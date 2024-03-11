# File: server.py
# Purpose:
#   UVM server functionality to listen to client file operation requests.

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
from datetime import datetime
from flask import Flask, request, jsonify

import fs

##############################################################################
# App Creation + Invariants
app = Flask(__name__)

# How many files we want to allow to be allocated per UVM (beyond README.md)
UVM_MAXIMUM_NUMBER_OF_FILES = 3

# How long we wait between checks as to whether every RVM has died
RVM_HEALTH_PING_TIMEOUT = 3


##############################################################################
# Logging Helper(s)
def current_timestamp():
    return datetime.now().strftime("%Hh %Mm %Ss %f")[:-3]+"ms"


def log(msg: str):
    print('uvm ['+current_timestamp()+']> '+msg)


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


##############################################################################
# UVM/RVM File Command Forwarding URL Command Extractor
UVM_IPS_FILENAME = '../ips/'+sys.argv[1]+'/uvm.txt'
RVM_IPS_FILENAME = '../ips/'+sys.argv[1]+'/rvm.txt'
rvm_ips_file_lock = threading.Lock()

def uvm_ip():
    with open(UVM_IPS_FILENAME, 'r') as file:
        return file.read().strip()


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
            log('UVM-to-RVM Forwarding Error: couldn\'t GET '+rurl)


##############################################################################
# Store all actions to be able to forward them to newly allocated servers
_command_history = []
_command_history_lock = threading.Lock()

def register_command(url: str):
    with _command_history_lock:
        _command_history.append(url[url.find(':5001')+6:])


def forward_commands(rvm_ip: str):
    with _command_history_lock:
        for command in _command_history:
            if not ping_rvm(rvm_ip,command):
                log('Failed to forward action "'+command+'" to VM '+rvm_ip)


##############################################################################
# Get a new IP address for an EC2 RVM
MIDDLEWARE_IP_FILENAME = '../ips/middleware.txt'

def middleware_ip():
    with open(MIDDLEWARE_IP_FILENAME, 'r') as file:
        return file.read().strip()


def ping_middleware_for_new_rvm_ip():
    try:
        response = requests.get('http://'+middleware_ip()+':8002/getmachine')
        if response.status_code != 200:
            log('VM allocation error: Middleware is out of VMs to distribute!')
            return None
        return response.json().get("replica")
    except Exception as err_msg:
        log('VM allocation error: Middleware is out of VMs to distribute!')
        return None


# Also registers the IP in the UVM's <rvm.txt> file!
def get_new_rvm_ip():
    rip = ping_middleware_for_new_rvm_ip()
    if rip == None:
        return None
    family = urllib.parse.quote(sys.argv[1])
    uvm = urllib.parse.quote(uvm_ip())
    rips = rvm_ips()
    if len(rips) == 0:
        rips.append(rip)
    else:
        rips[0] = rip
    rvm_txt = '\n'.join(rips)
    rvms = urllib.parse.quote(rvm_txt)
    if ping_rvm(rip,'rvm_pool_register_and_awaken/'+family+'/'+uvm+'/'+rvms):
        write_rvm_ips(rvm_txt)
        forward_commands(rip)
        return rip
    return None


##############################################################################
# FILE OPERATIONS

##############################################################################
# Read the contents of a path
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
        fs.write(path,data)
        register_command(request.url)
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
        register_command(request.url)
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
        register_command(request.url)
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
        fs.rename(old_path,new_path)
        register_command(request.url)
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
        log('New RVM <ip_address_list>: '+ip_address_list.strip().replace('\n',', '))
        write_rvm_ips(ip_address_list)
        return jsonify({}), 200
    except Exception as err_msg:
        return jsonify({'error': str(err_msg)}), 400


##############################################################################
# Listen for an RVM leader ping
@app.route('/uvm_leader_ping', methods=['GET'])
def uvm_leader_ping():
    try:
        log('Pinged by leader!')
        return jsonify({}), 200
    except Exception as err_msg:
        return jsonify({'error': str(err_msg)}), 400


##############################################################################
# Listen to make sure there's at least one RVM available
# Spawn and integrate a new RVM into the system
# => This RVM will automatically elect itself as the leader, then re-spawn all
#    of the other missing RVMs!
def spawn_seed_rvm():
    log('All RVMs are dead!')
    seed_ip = get_new_rvm_ip()
    if seed_ip == None:
        log("Can't allocate any more RVMs to recover the backup network!")
    else:
        log('Spawned an RVM ('+seed_ip+') to seed the network!')


# Continuously verify that we have at least 1 RVM alive in the system
def keep_rvms_alive():
    while True:
        rips = rvm_ips()
        failed_count = 0
        for rip in rips:
            if not ping_rvm(rip,'rvm_uvm_ping'):
                log('Failed to reach RVM: '+rip)
                failed_count += 1
        if failed_count == len(rips):
            spawn_seed_rvm()
        time.sleep(RVM_HEALTH_PING_TIMEOUT)


##############################################################################
# ROUTER UVM SELECTION
FILES_ROOT_DIRECTORY = os.path.dirname(__file__)+'/../rootdir/'

def number_of_files_in_uvm():
    count = 0
    for entry in os.listdir(FILES_ROOT_DIRECTORY):
        if entry != 'README.md' and os.path.isfile(os.path.join(FILES_ROOT_DIRECTORY,entry)):
            count += 1
    return count


def can_add_files_to_this_machine():
    return number_of_files_in_uvm() < UVM_MAXIMUM_NUMBER_OF_FILES


@app.route('/uvm_can_be_routed_with/<operation>/<path>', methods=['GET'])
def uvm_can_be_routed_with(operation, path):
    try:
        operation = urllib.parse.unquote(operation)
        path = urllib.parse.unquote(path)
        log('Pinged whether can support operation "'+operation+'" on file "'+path+'"!')
        if fs.exists(path):
            if operation == 'copy' and not can_add_files_to_this_machine():
                return jsonify({'error': 'UVM can\'t support operation "'+operation+'" for file "'+path+'"'}), 403
            return jsonify({ 'preferred': True }), 200
        if operation == 'exists':
            return jsonify({ 'preferred': False }), 200 # use this UVM iff no others have the file
        if(operation == 'write' and can_add_files_to_this_machine()):
            return jsonify({ 'preferred': False }), 200 # use this UVM iff no others have the file
        return jsonify({'error': 'UVM can\'t support operation "'+operation+'" for file "'+path+'"'}), 403
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
        /delete/<path>
        /copy/<src_path>/<dest_path>
        /rename/<old_path>/<new_path>
        /exists/<path>

    Happy coding! :)
    """
    )
    threading.Thread(target=keep_rvms_alive, daemon=True).start()
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)