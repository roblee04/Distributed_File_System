# File: server.py
# Purpose:
#   Route requests from client to corresponding UVMs.

# SUPPORTED ROUTES:
#   1. read N bytes (or all bytes if given READ_ENTIRE_PATH)
#   2. write N bytes (also creates files)
#   3. append N bytes (also creates files)
#   4. delete a file (static method)
#   5. copy a file  (static method)
#   6. rename (also moves) a file  (static method)
#   7. check if a file exists  (static method)

import os
from flask import Flask, request, jsonify
import requests
from threading import Lock
import urllib.parse


##############################################################################
# App Creation
app = Flask(__name__)


##############################################################################
# PREALLOCATED VM POOL DISTRIBUTION LOGIC
# add machine IPs from file
def machine_pool(file_name):
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


def init_uvms(root_dir):
    uvm_ips = []
    subdirectories = [d for d in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir,d))]
    for subdir in subdirectories:
        uvm_file_path = os.path.join(root_dir,subdir,'uvm.txt')
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
nodes = init_uvms(IP_ROOT)


def request_replica():
    with vm_pool_lock:
        if len(vm_pool) >= 1:
            return jsonify({'replica': vm_pool.pop(0)}), 200
        else:
            return jsonify({'replica': None}), 200


##############################################################################
# UVM IP ADDRESS REPLACEMENT LOGIC
def replace_uvm(old_uvm, new_uvm):
    if old_uvm in nodes:
        with node_lock:
            nodes[nodes.index(old_uvm)] = new_uvm
    else:
        raise Exception('router> Error: No UVM to be replaced')


##############################################################################
# ROUTING LOGIC
def get_request(url: str) -> int:
    try:
        return requests.get(url).status_code
    except Exception as err_msg:
        print('router> Error requesting url "'+url+'": '+str(err_msg))
        return 408


def ping_uvm(ip_address, command):
    return get_request('http://'+ip_address+':5001/'+command) == 200


# if file found, route to that node
def route(path: str):
    for ip in nodes:
        if ping_uvm(ip,'/exists/'+path):
            return 'http://'+ip+':5001'
    # if not found, return first node
    return 'http://'+nodes[0]+":5001"


##############################################################################
# Read N bytes from a path (read everything if N=-1)
@app.route('/read/<path>', methods=['GET'])
def read(path: str):
    try:
        # find route, and send request to node
        url_header = route(path)
        response = requests.get(url_header+"/read/"+path)
        # when the node responds back, forward response back to client
        if response.status_code == 200:
            return jsonify({'data': response.json().get("data")}), 200
        else:
            raise Exception("router> Read Error Code " + response.status_code)
    except Exception as err_msg:
        return jsonify({'error': err_msg.args[0]}), 400


##############################################################################
# Write a string to the path (creates a new file if <path> DNE)
@app.route('/write/<path>/<data>', methods=['GET'])
def write(path: str, data: str):
    try:
        path = urllib.parse.unquote(path)
        data = urllib.parse.unquote(data)
        # find route, and send request to node
        url_header = route(path)
        response = requests.get(url_header+"/write/"+path+"/"+data)
        # when the node responds back, forward reponse back to client
        if response.status_code == 200:
            return jsonify({}), 200
        else:
            raise Exception("router> Write Error Code " + response.status_code)

    except Exception as err_msg:
        return jsonify({'error': err_msg.args[0]}), 400


##############################################################################
# Delete <path>
@app.route('/delete/<path>', methods=['GET'])
def delete(path: str):
    try:
        path = urllib.parse.unquote(path)
        url_header = route(path)
        response = requests.get(url_header+"/delete/"+path)
        if response.status_code == 200:
            return jsonify({}), 200
        else:
            raise Exception("router> Delete Error Code " + response.status_code)

    except Exception as err_msg:
        return jsonify({'error': err_msg.args[0]}), 400


##############################################################################
# Copy <src_path> to <dest_path>
@app.route('/copy/<src_path>/<dest_path>', methods=['GET'])
def copy(src_path: str, dest_path: str):
    try:
        src_path = urllib.parse.unquote(src_path)
        dest_path = urllib.parse.unquote(dest_path)
        url_header = route(src_path)
        response = requests.get(url_header+"/copy/"+src_path+"/"+dest_path)
        if response.status_code == 200:
            return jsonify({}), 200
        else:
            raise Exception("router> Copy Error Code " + response.status_code)

    except Exception as err_msg:
        return jsonify({'error': err_msg.args[0]}), 400


##############################################################################
# Rename <old_path> as <new_path>
@app.route('/rename/<old_path>/<new_path>', methods=['GET'])
def rename(old_path: str, new_path: str):
    try:
        old_path = urllib.parse.unquote(old_path)
        new_path = urllib.parse.unquote(new_path)
        url_header = route(old_path)
        response = requests.get(url_header+"/rename/"+old_path+"/"+new_path)
        if response.status_code == 200:
            return jsonify({}), 200
        else:
            raise Exception("router> Rename Error Code " + response.status_code)

    except Exception as err_msg:
        return jsonify({'error': err_msg.args[0]}), 400


##############################################################################
# Rename <old_path> as <new_path> # is this needed
@app.route('/exists/<path>', methods=['GET'])
def exists(path: str):
    try:
        path = urllib.parse.unquote(path)
        url_header = route(path)
        response = requests.get(url_header+"/exists/"+path)
        if response.status_code == 200:
            return jsonify({'exists': response.json().get("exists")}), 200
        else:
            raise Exception("router> Exists? Error Code " + response.status_code)

    except Exception as err_msg:
        return jsonify({'error': err_msg.args[0]}), 400

##############################################################################
# gives machines to nodes that need it
@app.route('/getmachine', methods=['GET'])
def get_machine():
    return request_replica()


##############################################################################
# update global uvms / nodes variable
@app.route('/router_update_uvm_ip/<old>/<new>', methods=['GET'])
def update_uvm(old, new):
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