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
##############################################################################
# App Creation
app = Flask(__name__)

##############################################################################
# ROUTING LOGIC

# need to add concurrency control
vm_pool = [] # add VMs manually
nodes = ["127.0.0.1:5000"] # temp, for testing

def init_server():
    # create first node, UVM will create replicas
    first_node = vm_pool.pop(0)
    nodes.append(first_node)

def request_replica():
    if len(vm_pool) >= 1:
        return vm_pool.pop(0)
    else:
        raise Exception('error: VM pool is empty')

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


# need locking?
# Global Election Counter
ELECTION_COUNTER = 0

##############################################################################
# Read N bytes from a path (read everything if N=-1)
@app.route('/read/<path>/<int:position>/<int:n_bytes>', methods=['GET'])
def read(path: str, position: int, n_bytes: int):
    try:
        # find route, and send request to node
        node_ip = route(path)
        url = f"{node_ip}/read/{path}/{position}/{n_bytes}"
        response = requests.get(url).json()

        # when the node responds back, forward reponse back to client
        if response.status_code == 200:
            new_position = response.get("position")
            data = response.get("data")
            return jsonify({'position': new_position, 'data': data}), 200
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
def getmachine():
    return request_replica()

##############################################################################
# Start the server
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8002, debug=True)