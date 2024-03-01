# Author: Jordan Randleman - server.py
# Purpose:
#   UVM server functionality to listen to client file operation requests.

# SUPPORTED FILE APIs:
#   1. read a file
#   2. write data (also creates files)
#   3. append data (also creates files)
#   4. delete a file
#   5. copy a file
#   6. rename (also moves) a file
#   7. check if a file exists

import os
import requests
import threading
import urllib.parse
from flask import Flask, request, jsonify

import fs

##############################################################################
# App Creation
app = Flask(__name__)


##############################################################################
# GET Request Helper (returns status code)
def get_request(url: str) -> int:
    try:
        return requests.get(url).status_code
    except Exception as err_msg:
        print('uvm> Error requesting url "'+url+'": '+str(err_msg))
        return 408


##############################################################################
# RVM File Command Forwarding URL Command Extractor
RVM_IPS_FILENAME = '../ips/rvm.txt'
rvm_ips_file_lock = threading.Lock()

def rvm_ips():
    with rvm_ips_file_lock:
        with open(RVM_IPS_FILENAME, 'r') as file:
            return [line for line in [line.strip() for line in file.read().split('\n')] if len(line) > 0]


def write_rvm_ips(rvm_ips_contents: str):
    with rvm_ips_file_lock:
        with open(RVM_IPS_FILENAME, 'w') as file:
            file.write(rvm_ips_contents)


def get_forwarded_url(original_url, rvm_ip):
    return 'http://'+rvm_ip+original_url[original_url.find(':5000'):]


def forward_command(original_url):
    rips = rvm_ips()
    for rip in rips:
        rurl = get_forwarded_url(original_url,rip)
        if get_request(rurl) != 200:
            print('uvm> UVM-to-RVM Forwarding Error: couldn\'t GET '+rurl)


##############################################################################
# FILE OPERATIONS

##############################################################################
# Read N bytes from a path
# >> NOTE: No need to forward to our RVMs here!
@app.route('/read/<path>', methods=['GET'])
def read(path: str):
    try:
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
        fs.write(path, data)
        forward_command(request.url)
        return jsonify({}), 200
    except Exception as err_msg:
        return jsonify({'error': str(err_msg)}), 400


##############################################################################
# Append a string to the path (creates a new file if <path> DNE)
@app.route('/append/<path>/<data>', methods=['GET'])
def append(path: str, data: str):
    try:
        fs.append(path, data)
        forward_command(request.url)
        return jsonify({}), 200
    except Exception as err_msg:
        return jsonify({'error': str(err_msg)}), 400


##############################################################################
# Delete <path>
@app.route('/delete/<path>', methods=['GET'])
def delete(path: str):
    try:
        fs.delete(path)
        forward_command(request.url)
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
        fs.copy(src_path,dest_path)
        forward_command(request.url)
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
        fs.copy(old_path,new_path)
        forward_command(request.url)
        return jsonify({}), 200
    except fs.DistributedFileSystemError:
        return jsonify({'error': 'missing file'}), 404
    except Exception as err_msg:
        return jsonify({'error': str(err_msg)}), 400


##############################################################################
# Rename <old_path> as <new_path>
# >> NOTE: No need to forward to our RVMs here!
@app.route('/exists/<path>', methods=['GET'])
def exists(path: str):
    try:
        return jsonify({'exists': fs.exists(path)}), 200
    except Exception as err_msg:
        return jsonify({'error': str(err_msg)}), 400


##############################################################################
# RVM HEALTH MONITORING

##############################################################################
# Update ../ips/rvm.txt
@app.route('/uvm_update_rvm_ips/<ip_address_list>', methods=['GET'])
def uvm_update_rvm_ips(ip_address_list: str):
    try:
        ip_address_list = urllib.parse.unquote(ip_address_list)
        print('uvm> New RVM <ip_address_list>: '+ip_address_list)
        write_rvm_ips(ip_address_list)
        return jsonify({}), 200
    except Exception as err_msg:
        return jsonify({'error': str(err_msg)}), 400


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
        /append/<path>/<data>
        /delete/<path>
        /copy/<src_path>/<dest_path>
        /rename/<old_path>/<new_path>
        /exists/<path>

    Happy coding! :)
    """
    )
    app.run(host='0.0.0.0', debug=True, use_reloader=False)