# File: dfs.py
# Purpose:
#   Python library that clients can invoke to interact with our DFS.

# PROVIDED APIs:
#   1. read a file
#   2. write data (also creates files)
#   3. delete a file
#   4. copy a file
#   5. rename (also moves) a file
#   6. check if a file exists

import requests
import urllib

##############################################################################
# Middleware IP Address & Port Number
MIDDLEWARE_IP_ADDRESS = "54.215.223.179"


##############################################################################
# Request Helper
def make_request(endpoint):
    return requests.get('http://'+MIDDLEWARE_IP_ADDRESS+':8002/'+endpoint)


def handle_failed_request(response, err_message: str):
    response_json = response.json()
    if not 'error' in response_json:
        raise Exception(err_message)
    raise Exception(err_message + '. Error: ' + response_json.get('error'))


##############################################################################
# Read the contents of a file
def read(path: str) -> str:
    response = make_request("read/"+urllib.parse.quote(path))
    if response.status_code == 200:
        return response.json().get("data")
    else:
        handle_failed_request(response, "Failed to read file '"+path+"'")


##############################################################################
# Write data to a file (creates a file if DNE)
def write(path: str, data: str):
    response = make_request("write/"+urllib.parse.quote(path)+"/"+urllib.parse.quote(data))
    if response.status_code != 200:
        handle_failed_request(response, "Failed to write to file '"+path+"'")


##############################################################################
# Delete a file
def delete(path: str):
    response = make_request("delete/"+urllib.parse.quote(path))
    if response.status_code != 200:
        handle_failed_request(response, "Failed to delete file '"+path+"'")


##############################################################################
# Copy a file
def copy(src_path: str, dest_path: str):
    response = make_request("copy/"+urllib.parse.quote(src_path)+"/"+urllib.parse.quote(dest_path))
    if response.status_code != 200:
        handle_failed_request(response, "Failed to copy file '"+src_path+"' to '"+dest_path+"'")


##############################################################################
# Rename a file (also moves files)
def rename(old_path: str, new_path: str):
    response = make_request("rename/"+urllib.parse.quote(old_path)+"/"+urllib.parse.quote(new_path))
    if response.status_code != 200:
        handle_failed_request(response, "Failed to rename file '"+old_path+"' to '"+new_path+"'")


##############################################################################
# Checks if a file exists
def exists(path: str) -> bool:
    response = make_request("exists/"+urllib.parse.quote(path))
    if response.status_code == 200:
        return response.json().get("exists")
    else:
        handle_failed_request(response, "Error checking if file '"+path+"' exists")
