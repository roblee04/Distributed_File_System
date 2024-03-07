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


IP_ROOT = "./ips/"
UVM_PORT = "5001"


# thread safe global variables
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
                print("Error opening or reading file "+uvm_file_path+": "+str(e))
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
            idx = nodes.index(old_uvm)
            del nodes[idx]
            nodes.insert(idx, new_uvm)
            return nodes
    else:
        raise Exception('error: No UVM to be replaced')


##############################################################################
# ROUTING LOGIC
# if file found, route to that node
def route(path: str):
    # INPUT, path
    try:
        for ip in nodes:
            #check existence of file on node
            response = requests.get(ip+'/exists/'+path)
            if response.status_code == 200:
                return ip + ":" + UVM_PORT
        # if not found, return first node
        return nodes[0] + ":" + UVM_PORT

    # OUTPUT, corresponding node ip
    except Exception as err:
        return err.args[0]


##############################################################################
# Read N bytes from a path (read everything if N=-1)
@app.route('/read/<path>', methods=['GET'])
def read(path: str):
    try:
        # find route, and send request to node
        node_ip = route(path)
        response = requests.get(node_ip+"/read/"+path)
        # when the node responds back, forward response back to client
        if response.status_code == 200:
            return jsonify({'data': response.json().get("data")}), 200
        else:
            raise Exception("Error Code " + response.status_code)
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
        node_ip = route(path)
        response = requests.get(node_ip+"/write/"+path+"/"+data)
        # when the node responds back, forward reponse back to client
        if response.status_code == 200:
            return jsonify({}), 200
        else:
            raise Exception("Error Code " + response.status_code)

    except Exception as err_msg:
        return jsonify({'error': err_msg.args[0]}), 400


##############################################################################
# Delete <path>
@app.route('/delete/<path>', methods=['GET'])
def delete(path: str):
    try:
        path = urllib.parse.unquote(path)
        node_ip = route(path)
        response = requests.get(node_ip+"/delete/"+path)
        if response.status_code == 200:
            return jsonify({}), 200
        else:
            raise Exception("Error Code " + response.status_code)

    except Exception as err_msg:
        return jsonify({'error': err_msg.args[0]}), 400


##############################################################################
# Copy <src_path> to <dest_path>
@app.route('/copy/<src_path>/<dest_path>', methods=['GET'])
def copy(src_path: str, dest_path: str):
    try:
        src_path = urllib.parse.unquote(src_path)
        dest_path = urllib.parse.unquote(dest_path)
        node_ip = route(src_path)
        response = requests.get(node_ip+"/copy/"+src_path+"/"+dest_path)
        if response.status_code == 200:
            return jsonify({}), 200
        else:
            raise Exception("Error Code " + response.status_code)

    except Exception as err_msg:
        return jsonify({'error': err_msg.args[0]}), 400


##############################################################################
# Rename <old_path> as <new_path>
@app.route('/rename/<old_path>/<new_path>', methods=['GET'])
def rename(old_path: str, new_path: str):
    try:
        old_path = urllib.parse.unquote(old_path)
        new_path = urllib.parse.unquote(new_path)
        node_ip = route(old_path)
        response = requests.get(node_ip+"/rename/"+old_path+"/"+new_path)
        if response.status_code == 200:
            return jsonify({}), 200
        else:
            raise Exception("Error Code " + response.status_code)

    except Exception as err_msg:
        return jsonify({'error': err_msg.args[0]}), 400


##############################################################################
# Rename <old_path> as <new_path> # is this needed
@app.route('/exists/<path>', methods=['GET'])
def exists(path: str):
    try:
        path = urllib.parse.unquote(path)
        node_ip = route(path)
        response = requests.get(node_ip+"/exists/"+path)
        if response.status_code == 200:
            return jsonify({'exists': response.json().get("exists")}), 200
        else:
            raise Exception("Error Code " + response.status_code)

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
    old = urllib.parse.unquote(old)
    new = urllib.parse.unquote(new) 
    nodes = replace_uvm(old, new)
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