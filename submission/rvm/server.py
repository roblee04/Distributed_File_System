# File: server.py
# Purpose:
#   RVM server functionality to listen to uvm file operation requests.
#   Also monitors the other RVMs via a leadership election protocol.

# SUPPORTED FILE APIs:
#   1. read a file
#   2. write data (also creates files)
#   3. delete a file
#   4. copy a file
#   5. rename (also moves) a file
#   6. check if a file exists

# SUPPORTED UVM/RVM-HEALTH APIs:
#   1. Ping UVM to verify alive, and replace as needed
#   2. Listen for leader pings
#      * Elect a new leader if no ping in T time units
#   3. Listen for request to become the leader
#      * Start pinging nodes to test if alive after leadership
#   4. Change RVM IP address list

import os
import requests
import sys
import threading
import time
import urllib.parse
from datetime import datetime
from flask import Flask, request, jsonify

import fs

##############################################################################
# App Creation + Invariants
app = Flask(__name__)

# How long a leader has to ping - @important INCREASE THIS IF YOU NEED MORE TIME TO BOOT RVM SERVERS UP!
LEADER_PING_TIMEOUT_SECONDS = 3

# How often pooled resources check to see if they've been activated
RVM_POOLED_RESOURCE_AWAKEN_PING_TIMEOUT = 0.25

# How long a pooled RVM waits to start (gives other RVMs time to integrate this RVM)
RVM_POOLED_RESOURCE_INTEGRATION_BUFFER_TIME = 2

# How often we ping the UVM
UVM_PING_TIMEOUT_SECONDS = 0.5

# How often we check for a leader ping
LEADER_PING_CHECK_TIMEOUT_SECONDS = 0.5

# How often we check for an RVM ping
RVM_PING_CHECK_TIMEOUT_SECONDS = 0.5

# How often the leader checks for its public IP upon the AWS site's failure
RVM_PUBLIC_IP_GETTER_TIMEOUT = 0.25

# How long we want to wait for <os.system> to exe prior killing this RVM
LAUNCH_UVM_SYSTEM_TIMEOUT = 0.25


##############################################################################
# Logging Helper(s)
def current_timestamp():
    return datetime.now().strftime("%Hh %Mm %Ss %f")[:-3]+"ms"


def log_pool(msg: str):
    print('pool-rvm ['+current_timestamp()+']> '+msg)


def log_leader(msg: str):
    print('lead-rvm ['+current_timestamp()+']> '+msg)


def log(msg: str):
    print('rvm ['+current_timestamp()+']> '+msg)


##############################################################################
# Store all actions to be able to forward them to newly allocated servers
_command_history = []
_command_history_lock = threading.Lock()

def register_command(url: str):
    with _command_history_lock:
        _command_history.append(url[url.find(':5000')+6:])


def forward_commands(rvm_ip: str):
    with _command_history_lock:
        for command in _command_history:
            if not ping_rvm(rvm_ip,command):
                log_leader('Failed to forward action "'+command+'" to VM '+rvm_ip)


##############################################################################
# FILE OPERATIONS

##############################################################################
# Read the contents of a path
@app.route('/read/<path>', methods=['GET'])
def read(path: str):
    try:
        path = urllib.parse.unquote(path)
        _, data = fs.read(path, 0, fs.READ_ENTIRE_PATH)
        return jsonify({'data': data, }), 200
    except fs.DistributedFileSystemError:
        return jsonify({'error': 'missing file'}), 404
    except Exception as err_msg:
        return jsonify({'error': str(err_msg)}), 400


##############################################################################
# Write a string to the path (creates a new file if <path> DNE)
@app.route('/write/<path>/<data>', methods=['GET'])
def write(path: str, data: str):
    try:
        path = urllib.parse.unquote(path)
        data = urllib.parse.unquote(data)
        fs.write(path, data)
        register_command(request.url)
        return jsonify({}), 200
    except Exception as err_msg:
        return jsonify({'error': str(err_msg)}), 400


##############################################################################
# Delete <path>
@app.route('/delete/<path>', methods=['GET'])
def delete(path: str):
    try:
        path = urllib.parse.unquote(path)
        fs.delete(path)
        register_command(request.url)
        return jsonify({}), 200
    except fs.DistributedFileSystemError:
        return jsonify({'error': 'missing file'}), 404
    except Exception as err_msg:
        return jsonify({'error': str(err_msg)}), 400


##############################################################################
# Copy <src_path> to <dest_path>
@app.route('/copy/<src_path>/<dest_path>', methods=['GET'])
def copy(src_path: str, dest_path: str):
    try:
        src_path = urllib.parse.unquote(src_path)
        dest_path = urllib.parse.unquote(dest_path)
        fs.copy(src_path,dest_path)
        register_command(request.url)
        return jsonify({}), 200
    except fs.DistributedFileSystemError:
        return jsonify({'error': 'missing file'}), 404
    except Exception as err_msg:
        return jsonify({'error': str(err_msg)}), 400


##############################################################################
# Rename <old_path> as <new_path>
@app.route('/rename/<old_path>/<new_path>', methods=['GET'])
def rename(old_path: str, new_path: str):
    try:
        old_path = urllib.parse.unquote(old_path)
        new_path = urllib.parse.unquote(new_path)
        fs.rename(old_path,new_path)
        register_command(request.url)
        return jsonify({}), 200
    except fs.DistributedFileSystemError:
        return jsonify({'error': 'missing file'}), 404
    except Exception as err_msg:
        return jsonify({'error': str(err_msg)}), 400


##############################################################################
# Rename <old_path> as <new_path>
@app.route('/exists/<path>', methods=['GET'])
def exists(path: str):
    try:
        path = urllib.parse.unquote(path)
        return jsonify({'exists': fs.exists(path)}), 200
    except Exception as err_msg:
        return jsonify({'error': str(err_msg)}), 400


##############################################################################
# RVM HEALTH MONITORING

##############################################################################
# GET Request Helper (returns status code)
def get_request(url: str) -> int:
    try:
        return requests.get(url).status_code
    except Exception as err_msg:
        log('Error requesting url "'+url+'": '+str(err_msg))
        return 408


# Ping an RVM IP address and return if got a valid response
def ping_rvm(ip_address, command):
    return get_request('http://'+ip_address+':5000/'+command) == 200


# Ping a UVM IP address and return if got a valid response
def ping_uvm(ip_address, command):
    return get_request('http://'+ip_address+':5001/'+command) == 200


# Ping a Router IP address and return if got a valid response
def ping_router(ip_address, command):
    return get_request('http://'+ip_address+':8002/'+command) == 200


##############################################################################
# RVM Addresses Getter
RVM_IPS_FILENAME = '../ips/'+sys.argv[1]+'/rvm.txt'
rvm_ips_file_lock = threading.Lock()


def rvm_ips():
    with rvm_ips_file_lock:
        with open(RVM_IPS_FILENAME, 'r') as file:
            return [line for line in [line.strip() for line in file.read().split('\n')] if len(line) > 0]


def write_rvm_ips(rvm_ips_contents: str):
    with rvm_ips_file_lock:
        with open(RVM_IPS_FILENAME, 'w') as file:
            file.write(rvm_ips_contents)


##############################################################################
# UVM Address Getter
UVM_IPS_FILENAME = '../ips/'+sys.argv[1]+'/uvm.txt'
uvm_ips_file_lock = threading.Lock()


def uvm_ip():
    with uvm_ips_file_lock:
        with open(UVM_IPS_FILENAME, 'r') as file:
            return file.read().strip()


def write_uvm_ip(uvm_ip_contents: str):
    with uvm_ips_file_lock:
        with open(UVM_IPS_FILENAME, 'w') as file:
            file.write(uvm_ip_contents)


##############################################################################
# Get a new IP address for an EC2 RVM
MIDDLEWARE_IP_FILENAME = '../ips/middleware.txt'

def middleware_ip():
    with open(MIDDLEWARE_IP_FILENAME, 'r') as file:
        return file.read().strip()


def get_new_rvm_ip():
    try:
        response = requests.get('http://'+middleware_ip()+':8002/getmachine')
        if response.status_code != 200:
            log_leader('VM allocation error: Middleware is out of VMs to distribute!')
            return None
        return response.json().get("replica")
    except Exception as err_msg:
        log_leader('VM allocation error: Middleware is out of VMs to distribute!')
        return None


@app.route('/rvm_pool_confirm_waiting', methods=['GET'])
def rvm_pool_confirm_waiting():
    try:
        log('Pinged by a remote allocator to verify alive!')
        return jsonify({}), 200
    except Exception as err_msg:
        return jsonify({'error': str(err_msg)}), 400


##############################################################################
# Listen for a ping from the RVM leader: elect a new leader upon death.
# Track whether should continue RVM daemons (stops when becoming a UVM)
EXECUTING_RVM_DAEMONS = True


# Track last time pinged by leader
last_leader_ping_time_lock = threading.Lock()
last_leader_ping_time = time.time()


def reset_last_leader_ping_time():
    global last_leader_ping_time
    with last_leader_ping_time_lock:
        last_leader_ping_time = time.time()


def time_since_last_leader_ping():
    with last_leader_ping_time_lock:
        return time.time() - last_leader_ping_time


# Execute leader election protocol
def elect_leader():
    log('Electing a leader!')
    rips = rvm_ips()
    leader_ips = [int(rip.replace('.','')) for rip in rips]
    leaders = leader_ips.copy() # sorted in descending order to ping leaders
    leaders.sort(reverse=True)
    for leader in leaders:
        leader_ip = rips[leader_ips.index(leader)]
        if ping_rvm(leader_ip,'rvm_become_leader'):
            log('Successfully pinged '+leader_ip+' to become the leader!')
            return
        log('Failed pinging '+leader_ip+' to become the leader!')


# Verify received ping from leader within <LEADER_PING_TIMEOUT_SECONDS>
def elect_leader_if_missing_ping():
    log('Leader detection and election protocol initiated!')
    while EXECUTING_RVM_DAEMONS:
        time_elapsed = time_since_last_leader_ping()
        if time_elapsed >= LEADER_PING_TIMEOUT_SECONDS:
            log('Time between leader pings '+str(time_elapsed)+'s exceeded '+str(LEADER_PING_TIMEOUT_SECONDS)+'s!')
            elect_leader()
            reset_last_leader_ping_time()
        time.sleep(LEADER_PING_CHECK_TIMEOUT_SECONDS)


# Listen for a leader ping
@app.route('/rvm_leader_ping', methods=['GET'])
def rvm_leader_ping():
    try:
        reset_last_leader_ping_time()
        log('Pinged by leader!')
        return jsonify({}), 200
    except Exception as err_msg:
        return jsonify({'error': str(err_msg)}), 400


##############################################################################
# Leader pings for UVM health: become the new UVM upon death.
# Get our public IP address from <http://checkip.amazonaws.com>
def get_public_ip():
    while True:
        try:
            response = requests.get('http://checkip.amazonaws.com')
            response.raise_for_status()
            public_ip = response.text.strip()
            log_leader('Leader got its own public IP: '+public_ip)
            return public_ip
        except Exception as err_msg:
            log_leader("Error fetching leader's public IP address: "+str(err_msg))
        time.sleep(RVM_PUBLIC_IP_GETTER_TIMEOUT)


# Trigger pooled RVM(s) to execute as proper RVM(s)
def awaken_pooled_rvm(pooled_rvm_ip, rvm_txt): 
    family = urllib.parse.quote(sys.argv[1])
    uvm = urllib.parse.quote(uvm_ip())
    rvms = urllib.parse.quote(rvm_txt)
    if isinstance(pooled_rvm_ip,list):
        registration_url = 'rvm_pool_register/'+family+'/'+uvm+'/'+rvms
        for ip in pooled_rvm_ip:
            ping_rvm(ip,registration_url)
        for ip in pooled_rvm_ip:
            ping_rvm(ip,'rvm_pool_awaken')
        for ip in pooled_rvm_ip:
            forward_commands(ip)
    else:
        ping_rvm(pooled_rvm_ip,'rvm_pool_register_and_awaken/'+family+'/'+uvm+'/'+rvms)
        forward_commands(pooled_rvm_ip)


# Remove own IP from ../ips/rvm.txt, and forward the new list to all other RVMs
def replace_self_in_rvm_ip_list(public_ip, new_rvm_ip):
    rips = rvm_ips()
    new_rvm_ips = [ip for ip in rips if ip != public_ip]
    if new_rvm_ip != None:
        new_rvm_ips.append(new_rvm_ip)
    rvm_txt = '\n'.join(new_rvm_ips)
    write_rvm_ips(rvm_txt)
    if new_rvm_ip != None:
        awaken_pooled_rvm(new_rvm_ip,rvm_txt)
    forward_new_rvm_ips_to_rvms(new_rvm_ips,urllib.parse.quote(rvm_txt))


# Update all RVMs with own IP as the new UVM IP
def forward_new_uvm_ip_to_rvms(public_ip):
    rips = rvm_ips()
    for rip in rips:
        if not ping_rvm(rip,'rvm_update_uvm_ip/'+public_ip):
            log_leader("Error trying to forward new UVM IP address to RVM "+rip)


def forward_new_uvm_ip_to_router(old_uvm_ip, public_ip):
    mip = middleware_ip()
    if not ping_router(mip,'router_update_uvm_ip/'+old_uvm_ip+'/'+public_ip):
        log_leader("Error trying to forward new UVM IP address to central router "+mip)


def forward_new_uvm_ip_to_rvms_and_router(public_ip):
    old_uvm_ip = urllib.parse.quote(uvm_ip())
    write_uvm_ip(public_ip)
    public_ip = urllib.parse.quote(public_ip)
    forward_new_uvm_ip_to_rvms(public_ip)
    forward_new_uvm_ip_to_router(old_uvm_ip,public_ip)


# Launch the UVM Server
def spawn_uvm_server_process(command: str):
    os.system(command)


def launch_uvm_server(command):
    # <sleep> waits for the <system> call in the thread below to trigger
    threading.Thread(target=spawn_uvm_server_process, args=(command,), daemon=True).start()
    time.sleep(LAUNCH_UVM_SYSTEM_TIMEOUT)


# Replace self with a new RVM, elect a new leader, and become the new UVM
def become_uvm():
    # 0. Spawn a new RVM to take the current RVM's place
    public_ip = get_public_ip()
    EXECUTING_RVM_DAEMONS = False
    # 1. Spawn UVM server to run on this machine
    command = "python3 "+os.getcwd()+"/../uvm/server.py "+sys.argv[1]+" &> logs.txt"
    log_leader('Becoming a UVM!')
    log_leader('Starting the UVM process: see output in "./logs.txt"')
    log_leader('Starting command: '+command)
    launch_uvm_server(command)
    # 2. Replace self with the new RVM's IP in the IP address list
    log_leader('Leader (new UVM) is forwarding new RVM IP address list ...')
    new_rvm_ip = get_new_rvm_ip()
    replace_self_in_rvm_ip_list(public_ip,new_rvm_ip)
    # 3. Forward own IP address to all RVMs to confirm UVM status
    log_leader('Leader (new UVM) is forwarding itself as the UVM IP address ...')
    forward_new_uvm_ip_to_rvms_and_router(public_ip)
    # 4. Elect a new leader among the RVMs
    log_leader('Leader (new UVM) is electing a leader amoung the remaining RVMs ...')
    elect_leader()
    # 5. Terminate the current RVM
    log_leader('Leader (new UVM) is terminating: became a UVM! :)')
    print('          >> Make sure to eventually lookup and kill the PID of the spawned UVM!')
    print('             $ lsof -i :5001')
    print('             $ kill <pid>')
    os._exit(0) # required to properly end the flask server (smh)


# Verify received ping from UVM within <LEADER_PING_TIMEOUT_SECONDS>
def become_uvm_if_missing_ping():
    while True:
        uip = uvm_ip()
        if not ping_uvm(uip,'/uvm_leader_ping'):
            log_leader('Failed to reach UVM (will replace with self): '+uip)
            become_uvm()
        else:
            log_leader('Confirmed UVM is alive!')
        time.sleep(UVM_PING_TIMEOUT_SECONDS)


##############################################################################
# Listen for request to become the RVM leader
# Get list of dead RVM IP addresses
def get_dead_rvm_ips(rips):
    dead_ips = []
    for rip in rips:
        if not ping_rvm(rip,'rvm_leader_ping'):
            log_leader('Failed to reach dead RVM (will replace it): '+rip)
            dead_ips.append(rip)
    return dead_ips


# Get list of replacement RVM IP addresses
def get_new_rvm_ips(total_new_rvms):
    return [x for x in [get_new_rvm_ip() for _ in range(total_new_rvms)] if x != None]


# Forward the new RVM IP address list to the UVM and each RVM
def forward_new_rvm_ips_to_rvms(new_rvm_ips, ip_address_list):
    for rip in new_rvm_ips:
        if not ping_rvm(rip,'rvm_update_rvm_ips/'+ip_address_list):
            log_leader("Error trying to forward new RVM IP address list to RVM "+rip)


def forward_new_rvm_ips_to_uvm(uvm_ip, ip_address_list):
    if not ping_uvm(uvm_ip,'uvm_update_rvm_ips/'+ip_address_list):
        log_leader("Error trying to forward new RVM IP address list to UVM "+uvm_ip)


def forward_new_rvm_ips(live_ips, pooled_rvm_ips):
    log_leader('Forwarding new RVM IP addresses list ...')
    rvm_txt = '\n'.join(live_ips + pooled_rvm_ips) 
    ip_address_list = urllib.parse.quote(rvm_txt)
    write_rvm_ips(rvm_txt)
    awaken_pooled_rvm(pooled_rvm_ips,rvm_txt)
    forward_new_rvm_ips_to_rvms(live_ips,ip_address_list)
    forward_new_rvm_ips_to_uvm(uvm_ip(),ip_address_list)
    log_leader('Finished forwarding the new RVM IP addresses list!')


# Replace dead RVMs as needed
def replace_rvms_if_missing_ping():
    while EXECUTING_RVM_DAEMONS:
        rips = rvm_ips()
        dead_ips = get_dead_rvm_ips(rips)
        if len(dead_ips) != 0:
            log_leader('Found dead RVM IPs: '+', '.join(dead_ips))
            live_ips = [ip for ip in rips if ip not in dead_ips]
            forward_new_rvm_ips(live_ips,get_new_rvm_ips(len(dead_ips)))
        else:
            log_leader('Confirmed all RVM IPs are active!')
        time.sleep(RVM_PING_CHECK_TIMEOUT_SECONDS)


# Track RVM pinging status
leader_pinging_rvms_lock = threading.Lock()
leader_pinging_rvms = False


# Assume leadership and listen for RVM pings
@app.route('/rvm_become_leader', methods=['GET'])
def rvm_become_leader():
    log_leader('Became the leader!')
    global leader_pinging_rvms
    try:
        with leader_pinging_rvms_lock:
            if leader_pinging_rvms:
                return jsonify({}), 200
            leader_pinging_rvms = True
        threading.Thread(target=become_uvm_if_missing_ping, daemon=True).start()
        threading.Thread(target=replace_rvms_if_missing_ping, daemon=True).start()
        return jsonify({}), 200
    except Exception as err_msg:
        return jsonify({'error': str(err_msg)}), 400


##############################################################################
# Update ../ips/rvm.txt
@app.route('/rvm_update_rvm_ips/<ip_address_list>', methods=['GET'])
def rvm_update_rvm_ips(ip_address_list: str):
    try:
        ip_address_list = urllib.parse.unquote(ip_address_list)
        log('New RVM <ip_address_list>: '+ip_address_list.strip().replace('\n',', '))
        write_rvm_ips(ip_address_list)
        return jsonify({}), 200
    except Exception as err_msg:
        return jsonify({'error': str(err_msg)}), 400


##############################################################################
# Update ../ips/uvm.txt
@app.route('/rvm_update_uvm_ip/<ip>', methods=['GET'])
def rvm_update_uvm_ip(ip: str):
    try:
        ip = urllib.parse.unquote(ip)
        log('New UVM <ip>: '+ip.strip())
        write_uvm_ip(ip)
        return jsonify({}), 200
    except Exception as err_msg:
        return jsonify({'error': str(err_msg)}), 400


##############################################################################
# Confirm to UVM whether alive
@app.route('/rvm_uvm_ping', methods=['GET'])
def rvm_uvm_ping():
    try:
        log('Pinged by UVM!')
        return jsonify({}), 200
    except Exception as err_msg:
        return jsonify({'error': str(err_msg)}), 400


##############################################################################
# Pooled RVM Waiter: wait until awoken with system parameters
AWOKEN = False
awoken_lock = threading.Lock()

def register_family(family_id, current_uvm, current_rvms):
    global RVM_IPS_FILENAME
    global UVM_IPS_FILENAME
    sys.argv[1] = urllib.parse.unquote(family_id)
    family_path = '../ips/'+sys.argv[1]+'/'
    with rvm_ips_file_lock:
        RVM_IPS_FILENAME = family_path+'rvm.txt'
    with uvm_ips_file_lock:
        UVM_IPS_FILENAME = family_path+'uvm.txt'
    if not os.path.isdir(family_path):
        os.makedirs(family_path)
    write_uvm_ip(urllib.parse.unquote(current_uvm))
    write_rvm_ips(urllib.parse.unquote(current_rvms))
    log_pool('Pooled resource given family '+family_id+' information!')


def awaken_pooled_resource():
    global AWOKEN
    with awoken_lock:
        AWOKEN = True
    log_pool('Pooled resource awoken!')


@app.route('/rvm_pool_register/<family_id>/<current_uvm>/<current_rvms>', methods=['GET'])
def rvm_pool_register(family_id, current_uvm, current_rvms):
    try:
        register_family(family_id,current_uvm,current_rvms)
        return jsonify({}), 200
    except Exception as err_msg:
        return jsonify({'error': str(err_msg)}), 400


@app.route('/rvm_pool_awaken/', methods=['GET'])
def rvm_pool_awaken():
    try:
        awaken_pooled_resource()
        return jsonify({}), 200
    except Exception as err_msg:
        return jsonify({'error': str(err_msg)}), 400


@app.route('/rvm_pool_register_and_awaken/<family_id>/<current_uvm>/<current_rvms>', methods=['GET'])
def rvm_pool_register_and_awaken(family_id, current_uvm, current_rvms):
    try:
        register_family(family_id,current_uvm,current_rvms)
        awaken_pooled_resource()
        return jsonify({}), 200
    except Exception as err_msg:
        return jsonify({'error': str(err_msg)}), 400


def initiate_pool_protocol():
    if sys.argv[1] == '0':
        log_pool('Pooled RVM resource is awaiting allocation\n!')
        while True:
            with awoken_lock:
                if AWOKEN:
                    log('Pooled resource is awaking!')
                    break
            time.sleep(RVM_POOLED_RESOURCE_AWAKEN_PING_TIMEOUT)
        log_pool('Awoken pooled RVM waiting for '+str(RVM_POOLED_RESOURCE_INTEGRATION_BUFFER_TIME)+'s for system integration!')
        time.sleep(RVM_POOLED_RESOURCE_INTEGRATION_BUFFER_TIME)
    threading.Thread(target=elect_leader_if_missing_ping, daemon=True).start()


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
    threading.Thread(target=initiate_pool_protocol, daemon=True).start()
    app.run(host='0.0.0.0', debug=True, use_reloader=False)