# Author: Robin Lee - central_server.py

# Purpose 
#   Route requests from client to corresponding UVMs


# ############################################################################
# @TODO: support dfs class http calls to server. route them to corresponding areas on uvm
# @TODO: Pool of VMs. In case of failure, allow UVMs to request for another VM (IP addr)
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

##############################################################################
# App Creation
app = Flask(__name__)

##############################################################################
# ROUTING LOGIC

vm_pool = [] # add VMs manually
nodes = []

def init_server():
    # create first node, UVM will create replicas
    first_node = vm_pool.pop(0)
    nodes.append(first_node)

def request_replica():
    if len(vm_pool) >= 1:
        return vm_pool.pop(0)
    else:
        raise Exception('error: VM pool is empty')
        
# Global Election Counter
ELECTION_COUNTER = 0

##############################################################################

# Communicate to our server by executing GET requests to the following routes:
#             /read/<path>/<int:position>/<int:n_bytes>
#             /write/<path>/<data>
#             /append/<path>/<data>
#             /delete/<path>
#             /copy/<src_path>/<dest_path>
#             /rename/<old_path>/<new_path>
#             /exists/<path>



##############################################################################
# Start the server
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)