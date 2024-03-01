# Author: Jordan Randleman - server.py
# Purpose:
#   RVM server functionality to listen to uvm file operation requests.
#   Also monitors the other RVMs via a leadership election protocol.





##############################################################################
# @TODO: REPLACE <get_new_rvm_ip> BODY WITH PROPER HTTP CALL TO CENTRAL ROUTER
##############################################################################






# SUPPORTED FILE APIs:
#   1. read a file
#   2. write data (also creates files)
#   3. append data (also creates files)
#   4. delete a file
#   5. copy a file
#   6. rename (also moves) a file
#   7. check if a file exists

# SUPPORTED RVM-HEALTH APIs:
#   1. Listen for leader pings
#      * Elect a new leader if no ping in T time units
#   2. Listen for request to become the leader
#      * Start pinging nodes to test if alive after leadership
#   3. Change RVM IP address list

import os
import requests
import threading
import time
import urllib.parse
from flask import Flask, request, jsonify

import fs

##############################################################################
# App Creation + Invariables
app = Flask(__name__)

# How long a leader has to ping
LEADER_PING_TIMEOUT_SECONDS = 3

# How often we check for a leader ping
LEADER_PING_CHECK_TIMEOUT_SECONDS = 0.5

# How often we check for an RVM ping
RVM_PING_CHECK_TIMEOUT_SECONDS = 0.5


##############################################################################
# FILE OPERATIONS

##############################################################################
# Read N bytes from a path
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
        return jsonify({}), 200
    except Exception as err_msg:
        return jsonify({'error': str(err_msg)}), 400


##############################################################################
# Append a string to the path (creates a new file if <path> DNE)
@app.route('/append/<path>/<data>', methods=['GET'])
def append(path: str, data: str):
    try:
        fs.append(path, data)
        return jsonify({}), 200
    except Exception as err_msg:
        return jsonify({'error': str(err_msg)}), 400


##############################################################################
# Delete <path>
@app.route('/delete/<path>', methods=['GET'])
def delete(path: str):
    try:
        fs.delete(path)
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
        print('rvm> Error requesting url "'+url+'": '+str(err_msg))
        return 408


##############################################################################
# RVM Addresses Getter
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


##############################################################################
# Listen for a ping from the RVM leader: elect a new leader upon death.
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


# Ping an IP address and return if got a valid response
def ping_ip(ip_address, command):
    return get_request('http://'+ip_address+':5000/'+command) == 200


# Execute leader election protocol
def elect_leader():
    print('rvm> electing a leader!')
    rips = rvm_ips()
    leader_ips = [int(rip.replace('.','')) for rip in rips]
    leaders = leader_ips.copy() # sorted in descending order to ping leaders
    leaders.sort(reverse=True)
    for leader in leaders:
        leader_ip = rips[leader_ips.index(leader)]
        if ping_ip(leader_ip,'rvm_become_leader'):
            print('rvm> successfully pinged '+leader_ip+' to become the leader!')
            return
        print('rvm> failed pinging '+leader_ip+' to become the leader!')


# Verify received ping from leader within <LEADER_PING_TIMEOUT_SECONDS>
def elect_leader_if_missing_ping():
    while True:
        time_elapsed = time_since_last_leader_ping()
        if time_elapsed >= LEADER_PING_TIMEOUT_SECONDS:
            print('rvm> Time between pings '+str(time_elapsed)+'s passsed threshold '+str(LEADER_PING_TIMEOUT_SECONDS)+'s!')
            elect_leader()
            reset_last_leader_ping_time()
        time.sleep(LEADER_PING_CHECK_TIMEOUT_SECONDS)


# Listen for a leader ping
@app.route('/rvm_leader_ping', methods=['GET'])
def rvm_leader_ping():
    try:
        reset_last_leader_ping_time()
        print('rvm> pinged by leader!')
        return jsonify({}), 200
    except Exception as err_msg:
        return jsonify({'error': str(err_msg)}), 400


##############################################################################
# Listen for request to become the RVM leader
# Get a new IP address for an EC2 RVM
def get_new_rvm_ip():
    return None


# Get list of dead RVM IP addresses
def get_dead_rvm_ips(rips):
    dead_ips = []
    for rip in rips:
        if not ping_ip(rip,'rvm_leader_ping'):
            print('rvm> Leader failed to reach dead RVM (will replace it): '+rip)
            dead_ips.append(rip)
    return dead_ips


# Get list of replacement RVM IP addresses
def get_new_rvm_ips(total_new_rvms):
    return [x for x in [get_new_rvm_ip() for _ in range(total_new_rvms)] if x != None]


# Forward the new RVM IP address list to each RVM
def forward_new_rvm_ips(new_ips):
    print('rvm> Leader is forwarding new IP address list to RVMs ...')
    ip_address_list = urllib.parse.quote('\n'.join(new_ips))
    for ip in new_ips:
        if not ping_ip(ip,'rvm_update_rvm_ips/'+ip_address_list):
            print("rvm> Error trying to forward new IP address list to RVM "+ip)
    print('rvm> Leader finished forwarding the new IP address list!')


# Replace dead RVMs as needed
def replace_rvms_if_missing_ping():
    while True:
        rips = rvm_ips()
        dead_ips = get_dead_rvm_ips(rips)
        if len(dead_ips) != 0:
            print('rvm> Leader found dead RVM IPs: '+', '.join(dead_ips))
            live_ips = [ip for ip in rips if ip not in dead_ips]
            forward_new_rvm_ips(live_ips + get_new_rvm_ips(len(dead_ips)))
        else:
            print('rvm> Leader confirmed all RVM IPs are active!')
        time.sleep(RVM_PING_CHECK_TIMEOUT_SECONDS)


# Track RVM pinging status
leader_pinging_rvms_lock = threading.Lock()
leader_pinging_rvms = False


# Assume leadership and listen for RVM pings
@app.route('/rvm_become_leader', methods=['GET'])
def rvm_become_leader():
    print('rvm> Became the leader!')
    global leader_pinging_rvms
    try:
        with leader_pinging_rvms_lock:
            if leader_pinging_rvms:
                return jsonify({}), 200
            leader_pinging_rvms = True
        threading.Thread(target=replace_rvms_if_missing_ping, daemon=True).start()
        return jsonify({}), 200
    except Exception as err_msg:
        return jsonify({'error': str(err_msg)}), 400


##############################################################################
# Rename <old_path> as <new_path>
@app.route('/rvm_update_rvm_ips/<ip_address_list>', methods=['GET'])
def rvm_update_rvm_ips(ip_address_list: str):
    try:
        ip_address_list = urllib.parse.unquote(ip_address_list)
        print('rvm> NEW <ip_address_list>: '+ip_address_list)
        write_rvm_ips(ip_address_list)
        return jsonify({}), 200
    except Exception as err_msg:
        return jsonify({'error': str(err_msg)}), 400


##############################################################################
# Start the server
if __name__ == '__main__':
    # Don't even ask. Message always prints double otherwise lmao
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
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
    threading.Thread(target=elect_leader_if_missing_ping, daemon=True).start()
    app.run(host='0.0.0.0', debug=True, use_reloader=False)