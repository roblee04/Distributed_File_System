# Author: Jordan Randleman - uvm_client_listener.py
# Purpose:
#   UVM server functionality to listen to client file operation requests.

# SUPPORTED APIs:
#   1. read N bytes (or all bytes if given READ_ENTIRE_PATH)
#   2. write N bytes (also creates files)
#   3. append N bytes (also creates files)
#   4. delete a file (static method)
#   5. copy a file  (static method)
#   6. rename (also moves) a file  (static method)
#   7. check if a file exists  (static method)

import os
import sys
from flask import Flask, request, jsonify

import uvm_fs

##############################################################################
# App Creation
app = Flask(__name__)


##############################################################################
# Read N bytes from a path (read everything if N=-1)
@app.route('/read/<path>/<int:position>/<int:n_bytes>', methods=['GET'])
def read(path: str, position: int, n_bytes: int):
    try:
        new_position, data = uvm_fs.read(path, position, n_bytes)
        return jsonify({'position': new_position, 'data': data, }), 200
    except uvm_fs.DistributedFileSystemError:
        return jsonify({'error': 'missing file'}), 404
    except Exception as err_msg:
        return jsonify({'error': err_msg}), 400


##############################################################################
# Write a string to the path (creates a new file if <path> DNE)
@app.route('/write/<path>/<data>', methods=['GET'])
def write(path: str, data: str):
    try:
        uvm_fs.write(path, data)
        return jsonify({}), 200
    except Exception as err_msg:
        return jsonify({'error': err_msg}), 400


##############################################################################
# Append a string to the path (creates a new file if <path> DNE)
@app.route('/append/<path>/<data>', methods=['GET'])
def append(path: str, data: str):
    try:
        uvm_fs.append(path, data)
        return jsonify({}), 200
    except Exception as err_msg:
        return jsonify({'error': err_msg}), 400


##############################################################################
# Delete <path>
@app.route('/delete/<path>', methods=['GET'])
def delete(path: str):
    try:
        uvm_fs.delete(path)
        return jsonify({}), 200
    except uvm_fs.DistributedFileSystemError:
        return jsonify({'error': 'missing file'}), 404
    except Exception as err_msg:
        return jsonify({'error': err_msg}), 400


##############################################################################
# Copy <src_path> to <dest_path>
@app.route('/copy/<src_path>/<dest_path>', methods=['GET'])
def copy(src_path: str, dest_path: str):
    try:
        uvm_fs.copy(src_path,dest_path)
        return jsonify({}), 200
    except uvm_fs.DistributedFileSystemError:
        return jsonify({'error': 'missing file'}), 404
    except Exception as err_msg:
        return jsonify({'error': err_msg}), 400


##############################################################################
# Rename <old_path> as <new_path>
@app.route('/rename/<old_path>/<new_path>', methods=['GET'])
def rename(old_path: str, new_path: str):
    try:
        uvm_fs.copy(old_path,new_path)
        return jsonify({}), 200
    except uvm_fs.DistributedFileSystemError:
        return jsonify({'error': 'missing file'}), 404
    except Exception as err_msg:
        return jsonify({'error': err_msg}), 400


##############################################################################
# Rename <old_path> as <new_path>
@app.route('/exists/<path>', methods=['GET'])
def exists(path: str):
    try:
        return jsonify({'exists': uvm_fs.exists(path)}), 200
    except Exception as err_msg:
        return jsonify({'error': err_msg}), 400


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
            /read/<path>/<int:position>/<int:n_bytes>
            /write/<path>/<data>
            /append/<path>/<data>
            /delete/<path>
            /copy/<src_path>/<dest_path>
            /rename/<old_path>/<new_path>
            /exists/<path>

        Happy coding! :)
        """
        )
    sys.stdout.flush()
    app.run(debug=True)