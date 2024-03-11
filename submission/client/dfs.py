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
import time
import urllib

##############################################################################
# Middleware IP Address
MIDDLEWARE_IP_ADDRESS = "54.215.223.179"

# Middleware timeout to allocate a new resource
MIDDLEWARE_UVM_SPAWNING_TIMEOUT_SECONDS = 7


##############################################################################
# Request Helper
def make_request(endpoint):
    return requests.get('http://'+MIDDLEWARE_IP_ADDRESS+':8002/'+endpoint)


def handle_failed_request(response, err_message: str):
    exception_message = err_message
    try:
        exception_message = err_message + '. Error: ' + response.json().get('error')
    except Exception:
        exception_message = err_message + '. Error: ' + response.text
    raise Exception(exception_message)


##############################################################################
# Read the contents of a file
def read(path: str) -> str:
    url = "read/"+urllib.parse.quote(path)
    response = make_request(url)
    # Handle waiting for the router to have allocated a new resource
    if response.status_code == 425:
        url = url+'?token='+str(response.json().get('token'))
        while response.status_code == 425:
            time.sleep(MIDDLEWARE_UVM_SPAWNING_TIMEOUT_SECONDS)
            response = make_request(url)
    # Handle response once resource is allocated as needed
    if response.status_code == 200:
        return response.json().get("data")
    else:
        handle_failed_request(response, "Failed to read file '"+path+"'")


##############################################################################
# Write data to a file (creates a file if DNE)
def write(path: str, data: str):
    url = "write/"+urllib.parse.quote(path)+"/"+urllib.parse.quote(data)
    response = make_request(url)
    # Handle waiting for the router to have allocated a new resource
    if response.status_code == 425:
        url = url+'?token='+str(response.json().get('token'))
        while response.status_code == 425:
            time.sleep(MIDDLEWARE_UVM_SPAWNING_TIMEOUT_SECONDS)
            response = make_request(url)
    # Handle response once resource is allocated as needed
    if response.status_code != 200:
        handle_failed_request(response, "Failed to write to file '"+path+"'")


##############################################################################
# Delete a file
def delete(path: str):
    url = "delete/"+urllib.parse.quote(path)
    response = make_request(url)
    # Handle waiting for the router to have allocated a new resource
    if response.status_code == 425:
        url = url+'?token='+str(response.json().get('token'))
        while response.status_code == 425:
            time.sleep(MIDDLEWARE_UVM_SPAWNING_TIMEOUT_SECONDS)
            response = make_request(url)
    # Handle response once resource is allocated as needed
    if response.status_code != 200:
        handle_failed_request(response, "Failed to delete file '"+path+"'")


##############################################################################
# Copy a file
def copy(src_path: str, dest_path: str):
    url = "copy/"+urllib.parse.quote(src_path)+"/"+urllib.parse.quote(dest_path)
    response = make_request(url)
    # Handle waiting for the router to have allocated a new resource
    if response.status_code == 425:
        url = url+'?token='+str(response.json().get('token'))
        while response.status_code == 425:
            time.sleep(MIDDLEWARE_UVM_SPAWNING_TIMEOUT_SECONDS)
            response = make_request(url)
    # Handle response once resource is allocated as needed
    if response.status_code != 200:
        handle_failed_request(response, "Failed to copy file '"+src_path+"' to '"+dest_path+"'")


##############################################################################
# Rename a file (also moves files)
def rename(old_path: str, new_path: str):
    url = "rename/"+urllib.parse.quote(old_path)+"/"+urllib.parse.quote(new_path)
    response = make_request(url)
    # Handle waiting for the router to have allocated a new resource
    if response.status_code == 425:
        url = url+'?token='+str(response.json().get('token'))
        while response.status_code == 425:
            time.sleep(MIDDLEWARE_UVM_SPAWNING_TIMEOUT_SECONDS)
            response = make_request(url)
    # Handle response once resource is allocated as needed
    if response.status_code != 200:
        handle_failed_request(response, "Failed to rename file '"+old_path+"' to '"+new_path+"'")


##############################################################################
# Checks if a file exists
def exists(path: str) -> bool:
    url = "exists/"+urllib.parse.quote(path)
    response = make_request(url)
    # Handle waiting for the router to have allocated a new resource
    if response.status_code == 425:
        url = url+'?token='+str(response.json().get('token'))
        while response.status_code == 425:
            time.sleep(MIDDLEWARE_UVM_SPAWNING_TIMEOUT_SECONDS)
            response = make_request(url)
    # Handle response once resource is allocated as needed
    if response.status_code == 200:
        return response.json().get("exists")
    else:
        handle_failed_request(response, "Error checking if file '"+path+"' exists")
