# Author: Robin Lee - central_server.py

# Purpose 
#   Route requests from client to corresponding UVMs


# ############################################################################
# @TODO: Who initializes the ring? the server or nodes?
# @TODO: Pool of VMs. In case of failure, allow UVMs to request for another VM (IP addr)
#        May or may not need concurrency control.
# ############################################################################

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
##############################################################################
# App Creation
app = Flask(__name__)

##############################################################################
# ROUTING LOGIC

# add machine IPs from file
def machine_pool(file_name):
    pool = []
    with open(file_name, 'r') as file:
        for ip in file.readlines():
            pool.append(ip.strip())
    return pool

# thread safe global variables
POOL_IPS_FILENAME = 'pool-ips.txt'
vm_pool_lock = Lock()
vm_pool = machine_pool(POOL_IPS_FILENAME)


UVM_IPS_FILENAME = 'uvm-ips.txt'
node_lock = Lock()
nodes = machine_pool(UVM_IPS_FILENAME)

print(vm_pool, nodes)

def request_replica():
    with vm_pool_lock:
        if len(vm_pool) >= 1:
            return vm_pool.pop(0)
        else:
            raise Exception('error: VM pool is empty')

def replace_uvm(old_uvm, new_uvm):
    print(nodes)
    if old_uvm in nodes:
        with node_lock:
            idx = nodes.index(old_uvm)
            del nodes[idx]
            nodes.insert(idx, new_uvm)
            return nodes
    else:
        raise Exception('error: No UVM to be replaced')



# if file found, route to that node
def route(path: str):
    # INPUT, path
    try:
        for ip in nodes:
            #check existence of file on node
            url = ip +  '/exists/' + path
            response = requests.get(url)
            if response.status_code == 200:
                return ip

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
        url = f"{node_ip}/read/{path}"
        response = requests.get(url).json()

        # when the node responds back, forward reponse back to client
        if response.status_code == 200:
            data = response.get("data")
            return jsonify({'data': data}), 200
        else:
            raise Exception("Error Code " + response.status_code)

    except Exception as err_msg:
        return jsonify({'error': err_msg.args[0]}), 400


##############################################################################
# Write a string to the path (creates a new file if <path> DNE)
@app.route('/write/<path>/<data>', methods=['GET'])
def write(path: str, data: str):
    try:
        print("hit")
        # find route, and send request to node
        node_ip = route(path)
        url = f"{node_ip}/write/{path}/{data}"
        response = requests.get(url)
        # when the node responds back, forward reponse back to client
        if response.status_code == 200:
            return jsonify({}), 200
        else:
            raise Exception("Error Code " + response.status_code)

    except Exception as err_msg:
        return jsonify({'error': err_msg.args[0]}), 400


##############################################################################
# Append a string to the path (creates a new file if <path> DNE)
@app.route('/append/<path>/<data>', methods=['GET'])
def append(path: str, data: str):
    try:
        # find route, and send request to node
        node_ip = route(path)
        url = f"{node_ip}/append/{path}/{data}"
        response = requests.get(url)
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
        node_ip = route(path)
        url = f"{node_ip}/delete/{path}"
        response = requests.get(url)
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
        node_ip = route(src_path)
        url = f"{node_ip}/copy/{src_path}/{dest_path}"
        response = requests.get(url)
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
        node_ip = route(old_path)
        url = f"{node_ip}/rename/{old_path}/{new_path}"
        response = requests.get(url)
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
        node_ip = route(path)
        url = f"{node_ip}/exists/{path}"
        response = requests.get(url)
        if response.status_code == 200:
            return jsonify({}), 200
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
# find a new leader and replace current
@app.route('/elect/<old_uvm_ip>/<new_uvm_ip>', methods=['GET'])
def elect(old_uvm_ip: str, new_uvm_ip: str):
    return replace_uvm(old_uvm_ip, new_uvm_ip)

##############################################################################
# Start the server
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8002, debug=True)