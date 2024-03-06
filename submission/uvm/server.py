# File: server.py
# Purpose:
#   UVM server functionality to listen to client file operation requests.





##############################################################################
# @TODO: REPLACE <get_new_rvm_ip> BODY WITH PROPER HTTP CALL TO CENTRAL ROUTER
##############################################################################






# SUPPORTED FILE APIs:
#   1. read a file
#   2. write data (also creates files)
#   3. delete a file
#   4. copy a file
#   5. rename (also moves) a file
#   6. check if a file exists

import os
import requests
import sys
import threading
import time
import urllib.parse
from flask import Flask, request, jsonify

import fs

##############################################################################
# App Creation + Invariants
app = Flask(__name__)

# How long we wait between checks as to whether every RVM has died
RVM_HEALTH_PING_TIMEOUT = 3

# How long we wait between attempts to send the new RVM IP address list to a seeded RVM
RVM_SEED_IP_ADDRESS_LIST_PING_TIMEOUT = 0.25


##############################################################################
# Get a new IP address for an EC2 RVM
def get_new_rvm_ip():
    return None


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


def get_forwarded_url(original_url, rvm_ip):
    return 'http://'+rvm_ip+':5000'+original_url[original_url.find(':5001')+5:]


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
        forward_command(request.url)
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
        src_path = urllib.parse.unquote(src_path)
        dest_path = urllib.parse.unquote(dest_path)
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
        old_path = urllib.parse.unquote(old_path)
        new_path = urllib.parse.unquote(new_path)
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
        path = urllib.parse.unquote(path)
        return jsonify({'exists': fs.exists(path)}), 200
    except Exception as err_msg:
        return jsonify({'error': str(err_msg)}), 400


##############################################################################
# UVM HEALTH MONITORING

##############################################################################
# Update ../ips/rvm.txt
@app.route('/uvm_update_rvm_ips/<ip_address_list>', methods=['GET'])
def uvm_update_rvm_ips(ip_address_list: str):
    try:
        ip_address_list = urllib.parse.unquote(ip_address_list)
        print('uvm> New RVM <ip_address_list>: '+ip_address_list.strip().replace('\n',', '))
        write_rvm_ips(ip_address_list)
        return jsonify({}), 200
    except Exception as err_msg:
        return jsonify({'error': str(err_msg)}), 400


##############################################################################
# Listen for an RVM leader ping
@app.route('/uvm_leader_ping', methods=['GET'])
def uvm_leader_ping():
    try:
        print('uvm> Pinged by leader!')
        return jsonify({}), 200
    except Exception as err_msg:
        return jsonify({'error': str(err_msg)}), 400


##############################################################################
# Listen to make sure there's at least one RVM available
# Ping an RVM IP address and return if got a valid response
def ping_rvm(ip_address, command):
    return get_request('http://'+ip_address+':5000/'+command) == 200


# Spawn and integrate a new RVM into the system
# => This RVM will automatically elect itself as the leader, then re-spawn all
#    of the other missing RVMs!
def spawn_seed_rvm():
    print('uvm> All RVMs are dead!')
    seed_ip = get_new_rvm_ip()
    if seed_ip == None:
        print("uvm> Can't allocate any more RVMs to recover the backup network!")
        return
    print('uvm> Spawning an RVM ('+seed_ip+') to seed the network!')
    rips = rvm_ips()
    ip_address_list = '\n'.join([seed_ip] + rips[1:])
    write_rvm_ips(ip_address_list)
    ip_address_list = urllib.parse.quote(ip_address_list)
    while not ping_rvm(seed_ip,'rvm_update_rvm_ips/'+ip_address_list):
        time.sleep(RVM_SEED_IP_ADDRESS_LIST_PING_TIMEOUT)


# Continuously verify that we have at least 1 RVM alive in the system
def keep_rvms_alive():
    while True:
        rips = rvm_ips()
        failed_count = 0
        for rip in rips:
            if not ping_rvm(rip,'rvm_uvm_ping'):
                print('uvm> Failed to reach RVM: '+rip)
                failed_count += 1
        if failed_count == len(rips):
            spawn_seed_rvm()
        time.sleep(RVM_HEALTH_PING_TIMEOUT)


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
    threading.Thread(target=keep_rvms_alive, daemon=True).start()
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)