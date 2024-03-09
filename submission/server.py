# File: server.py
# Purpose:
#   Route requests from client to corresponding UVMs.

# SUPPORTED ROUTE APIs:
#   1. read a file
#   2. write data (also creates files)
#   3. delete a file
#   4. copy a file
#   5. rename (also moves) a file
#   6. check if a file exists

import os
from flask import Flask, request, jsonify
import requests
from threading import Lock
import urllib.parse


##############################################################################
# App Creation + Invariants
app = Flask(__name__)

# Resource Allocation: How long the router waits between checks for a new UVM
ROUTER_NEW_UVM_TIMEOUT = 0.25

# Maximum amount of time the router will wait for a new UVM to be created
# * Accounts for the extremely unlikely (but technically possible) event of
#   our entire subnetwork failing (even just 1 RVM could recover everything)
ROUTER_NEW_UVM_TERMINAL_FAILURE_TIMEOUT = 10


##############################################################################
# PREALLOCATED VM POOL DISTRIBUTION LOGIC
# add machine IPs from file
def machine_pool(file_name: str):
    pool = []
    with open(file_name, 'r') as file:
        for ip in file.readlines():
            pool.append(ip.strip())
    return pool


# thread safe global variables
IP_ROOT = "./ips/"
POOL_IPS_FILENAME = IP_ROOT+'pool-ips.txt'
vm_pool_lock = Lock()
vm_pool = machine_pool(POOL_IPS_FILENAME)


def init_uvms():
    uvm_ips = []
    subdirectories = [d for d in os.listdir(IP_ROOT) if os.path.isdir(os.path.join(IP_ROOT,d))]
    for subdir in subdirectories:
        uvm_file_path = os.path.join(IP_ROOT,subdir,'uvm.txt')
        if os.path.isfile(uvm_file_path):
            try:
                with open(uvm_file_path, 'r') as file:
                    contents = file.readlines()
                    uvm_ips.extend(contents)
            except IOError as e:
                print("router> Error opening or reading file "+uvm_file_path+": "+str(e))
    return uvm_ips


# thread safe global variables, nodes are UVMS!
node_lock = Lock()
nodes = init_uvms()


def request_replica():
    with vm_pool_lock:
        while True:
            if len(vm_pool) > 0:
                pip = vm_pool.pop(0)
                if ping_rvm(pip,'rvm_pool_confirm_waiting'):
                    print('router> Found an available pool VM: '+pip)
                    return pip
                else:
                    print('router> Pooled resource '+pip+' is unreachable!')
            else:
                print('router> No pool VMs left to allocate!')
                return None


##############################################################################
# UVM IP ADDRESS REPLACEMENT LOGIC
REPLACED_UVM_IPS = {} # {old: new, ...}
REPLACED_UVM_IPS_LOCK = Lock()

def replace_uvm(old_uvm: str, new_uvm: str):
    with REPLACED_UVM_IPS_LOCK:
        REPLACED_UVM_IPS[old_uvm] = new_uvm
    if old_uvm == new_uvm:
        return
    with node_lock:
        if old_uvm in nodes:
            print('router> Replacing UVM IP '+old_uvm+' with '+new_uvm)
            nodes[nodes.index(old_uvm)] = new_uvm
        else:
            raise Exception('router> Error: No UVM to be replaced')


##############################################################################
# UVM IP ADDRESS ALLOCATION LOGIC

##############################################################################
# ROUTING LOGIC
uvm_family_creation_lock = Lock()

def uvm_can_be_routed_to(ip_address: str, operation: str, path: str):
    try:
        return requests.get('http://'+ip_address+':5001/uvm_can_be_routed_with/'+operation+'/'+path)
    except Exception as err_msg:
        print('router> Error requesting url "'+url+'": '+str(err_msg))
        return None


def get_next_family_unit_id():
    max_subdir = 2
    subdirectories = [d for d in os.listdir(IP_ROOT) if os.path.isdir(os.path.join(IP_ROOT,d))]
    for subdir in subdirectories:
        if subdir.isdigit():
            n = int(subdir)
            if n > max_subdir:
                max_subdir = n
    return max_subdir+1


def get_number_of_RVMs_per_UVM():
    with open(IP_ROOT+'1/rvm.txt','r') as file:
        return len(file.read().strip().split("\n"))


def get_replicas_for_rvm_pool(number_RVMs_per_UVM: int):
    rvm_ips = [r for r in [request_replica() for _ in range(number_RVMs_per_UVM)] if r != None]
    if len(rvm_ips) == 0:
        return None, None
    return rvm_ips, rvm_ips[0]


def populate_rvm_txt(family_path: str, rvm_ips: list):
    with open(family_path+'/rvm.txt','w') as file:
        file.write('\n'.join(rvm_ips))


def populate_uvm_txt(family_path: str, uvm_dummy_ip: str):
    with open(family_path+'/uvm.txt','w') as file:
        file.write(uvm_dummy_ip)


def awaken_pooled_rvms(family: str, uvm: str, rvm_ips: list):
    family = urllib.parse.quote(family)
    uvm = urllib.parse.quote(uvm)
    rvms = urllib.parse.quote('\n'.join(rvm_ips))
    url = 'rvm_pool_awaken/'+family+'/'+uvm+'/'+rvms
    for rip in rvm_ips:
        if not ping_rvm(rip,url):
            print('router> UVM Allocation Warning: failed to awaken pooled RVM '+rip)


def get_uvm_ip_address(uvm_ip: str):
    start = time.time()
    while True:
        if time.time()-start >= ROUTER_NEW_UVM_TERMINAL_FAILURE_TIMEOUT:
            return None
        with REPLACED_UVM_IPS_LOCK:
            if uvm_ip in REPLACED_UVM_IPS:
                return REPLACED_UVM_IPS[uvm_ip]
        time.sleep(ROUTER_NEW_UVM_TIMEOUT)


# Also registers new UVM IP address to our <ips/> subdirectory!
def get_new_uvm_ip():
    with uvm_family_creation_lock:
        # 1. Determine which family number directory name we need to create
        family_id = str(get_next_family_unit_id())
        family_path = IP_ROOT+family_id
        # 2. Determine how many RVMs there are per UVM
        number_RVMs_per_UVM = get_number_of_RVMs_per_UVM()
        # 3. Request enough replicas for the RVMs
        rvm_ips, uvm_ip = get_replicas_for_rvm_pool(number_RVMs_per_UVM)
        if rvm_ips == None:
            return None
        # 4. Create the family's subdirectory in <ips> if needed
        os.makedirs(family_path)
        # 5. Populate the family number's <rvm.txt> on the local router machine
        populate_rvm_txt(family_path,rvm_ips)
        # 6. Put one of the RVM IPs in the <uvm.txt> on the local router machine
        #    * Guarenteed to fail, since the RVM's UVM server isn't up and running!
        populate_uvm_txt(uvm_ip)
        # 7. Forward the fact that the new family has been created to the pooled resources, awaking each resource
        #    * Have <rvm_pool_awaken/> create the directory and files if the family unit number is new
        awaken_pooled_rvms(family_id,uvm_ip,rvm_ips)
        # 8. Wait for UVM IP address to be confirmed generated by the leader, then return that UVM's IP address
        #    * Need to wait for the leader election _and_ UVM escelation procedures to complete in the subnetwork though!
        official_uvm_ip = get_uvm_ip_address(uvm_ip)
        if official_uvm_ip == None:
            return None
        # 9. Add new UVM IP to <nodes> with <node_lock>
        with node_lock:
            nodes.append(official_uvm_ip)


# Determine which UVM can execute <operation> on <path>
def route(operation: str, path: str):
    viable_uvms = []
    with node_lock:
        for ip in nodes:
            response = uvm_can_be_routed_to(ip,operation,path)
            if response != None and response.status_code == 200:
                print('router> Found viable UVM to route request to! Preferred status = '+str(response.json().get('preferred')))
                if response.json().get('preferred'):
                    return 'http://'+ip+':5001'
                else:
                    viable_uvms.append(ip)
    if len(viable_uvms) > 0:
        return 'http://'+viable_uvms[0]+":5001"
    new_uip = get_new_uvm_ip()
    if new_uip == None:
        print('router> Failed to route request "'+operation+'" with file "'+path+'" to a UVM!')
        return 'http://'+nodes[0]+":5001" # allow request to fail then trigger client-side exception
    print('router> Routing "'+operation+'" with file "'+path+'" to UVM "'+new_uip+'"!')
    return 'http://'+new_uip+":5001"
    

##############################################################################
# Read the contents of a path
@app.route('/read/<path>', methods=['GET'])
def read(path: str):
    try:
        # find route, and send request to node
        print('router> Pinged to write to '+urllib.parse.unquote(path))
        url_header = route('read',path)
        response = requests.get(url_header+"/read/"+path)
        # when the node responds back, forward response back to client
        if response.status_code == 200:
            return jsonify({'data': response.json().get("data")}), 200
        else:
            raise Exception("router> Read Error Code " + str(response.status_code))
    except Exception as err_msg:
        return jsonify({'error': err_msg.args[0]}), 400


##############################################################################
# Write a string to the path (creates a new file if <path> DNE)
@app.route('/write/<path>/<data>', methods=['GET'])
def write(path: str, data: str):
    try:
        print('router> Pinged to write to '+urllib.parse.unquote(path))
        # find route, and send request to node
        url_header = route('write',path)
        response = requests.get(url_header+"/write/"+path+"/"+data)
        # when the node responds back, forward reponse back to client
        if response.status_code == 200:
            return jsonify({}), 200
        else:
            raise Exception("router> Write Error Code " + str(response.status_code))

    except Exception as err_msg:
        return jsonify({'error': err_msg.args[0]}), 400


##############################################################################
# Delete <path>
@app.route('/delete/<path>', methods=['GET'])
def delete(path: str):
    try:
        print('router> Pinged to delete '+urllib.parse.unquote(path))
        url_header = route('delete',path)
        response = requests.get(url_header+"/delete/"+path)
        if response.status_code == 200:
            return jsonify({}), 200
        else:
            raise Exception("router> Delete Error Code " + str(response.status_code))

    except Exception as err_msg:
        return jsonify({'error': err_msg.args[0]}), 400


##############################################################################
# Copy <src_path> to <dest_path>
@app.route('/copy/<src_path>/<dest_path>', methods=['GET'])
def copy(src_path: str, dest_path: str):
    try:
        print('router> Pinged to copy '+urllib.parse.unquote(src_path)+' to '+urllib.parse.unquote(dest_path))
        url_header = route('copy',src_path)
        response = requests.get(url_header+"/copy/"+src_path+"/"+dest_path)
        if response.status_code == 200:
            return jsonify({}), 200
        else:
            raise Exception("router> Copy Error Code " + str(response.status_code))

    except Exception as err_msg:
        return jsonify({'error': err_msg.args[0]}), 400


##############################################################################
# Rename <old_path> as <new_path>
@app.route('/rename/<old_path>/<new_path>', methods=['GET'])
def rename(old_path: str, new_path: str):
    try:
        print('router> Pinged to rename '+urllib.parse.unquote(old_path)+' as '+urllib.parse.unquote(new_path))
        url_header = route('rename',old_path)
        response = requests.get(url_header+"/rename/"+old_path+"/"+new_path)
        if response.status_code == 200:
            return jsonify({}), 200
        else:
            raise Exception("router> Rename Error Code " + str(response.status_code))

    except Exception as err_msg:
        return jsonify({'error': err_msg.args[0]}), 400


##############################################################################
# Rename <old_path> as <new_path> # is this needed
@app.route('/exists/<path>', methods=['GET'])
def exists(path: str):
    try:
        print('router> Pinged whether '+urllib.parse.unquote(path)+' exists!')
        url_header = route('exists',path)
        response = requests.get(url_header+"/exists/"+path)
        if response.status_code == 200:
            return jsonify({'exists': response.json().get("exists")}), 200
        else:
            raise Exception("router> Exists? Error Code " + str(response.status_code))

    except Exception as err_msg:
        return jsonify({'error': err_msg.args[0]}), 400

##############################################################################
# gives machines to nodes that need it
@app.route('/getmachine', methods=['GET'])
def get_machine():
    print('router> Pinged to allocate a VM!')
    return jsonify({'replica': request_replica()}), 200


##############################################################################
# update global uvms / nodes variable
@app.route('/router_update_uvm_ip/<old>/<new>', methods=['GET'])
def update_uvm(old: str, new: str):
    replace_uvm(urllib.parse.unquote(old), urllib.parse.unquote(new))
    return jsonify({}), 200

    
##############################################################################
# Start the server
if __name__ == '__main__':
    print(
    """
    Welcome to Jordan, Rahul, and Robin's COEN 317 Project!
    Flask will communicate this server's "http" address!
    Communicate to our server by executing GET requests to the following routes:
        /read/<path>
        /write/<path>/<data>
        /delete/<path>
        /copy/<src_path>/<dest_path>
        /rename/<old_path>/<new_path>
        /exists/<path>

    Happy coding! :)
    """
    )
    app.run(host='0.0.0.0', port=8002, debug=True, use_reloader=False)