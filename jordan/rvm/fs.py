# Author: Jordan Randleman - fs.py
# Purpose:
#   Server functionality to operate on local files.
#   Called by an HTTP webserver process.



# ############################################################################
# @TODO: NEED TO ANCHOR ALL FILE OPERATIONS AT A SAFE ROOT (NOT JUST ANY PATH!)
# @TODO: CURRENTLY NOT IMPLEMENTING "DELETE N BYTES": ONLY "DELETE A FILE"
# ############################################################################



# SUPPORTED APIs:
#   1. read a file
#   2. write data (also creates files)
#   3. append data (also creates files)
#   4. delete a file
#   5. copy a file
#   6. rename (also moves) a file
#   7. check if a file exists

import os
import shutil

##############################################################################
# Custom Exceptions
# "File Not Found" Exception. Raised by every file except <exists>.
class DistributedFileNotFound(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__("dfs> "+self.message)

# Generic Error Class
class DistributedFileSystemError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__("dfs> "+self.message)


##############################################################################
# Constant Value(s)
READ_ENTIRE_PATH = -1 # used by <read>


##############################################################################
# Read N bytes from a path (read everything if N=-1)
# @return tuple: (new_position: int, read_data: str)
def read(path: str, position: int, n_bytes: int = READ_ENTIRE_PATH):
    if n_bytes != READ_ENTIRE_PATH and n_bytes < 0:
        raise DistributedFileSystemError(f"read: n_bytes {n_bytes} can't be negative!")
    try:
        with open(path, 'r') as file:
            contents = file.read()
            if n_bytes == READ_ENTIRE_PATH:
                return len(contents), contents
            return position+n_bytes, contents[position:position+n_bytes]
    except Exception:
        raise DistributedFileNotFound(f"read: Path {path} doesn't exist!")


##############################################################################
# Write a string to the path (creates a new file if <path> DNE)
def write(path: str, data: str):
    try:
        with open(path, 'w') as file:
            file.write(data)
    except Exception:
        raise DistributedFileSystemError(f"write: Path {path} can't be written!")


##############################################################################
# Append a string to the path (creates a new file if <path> DNE)
def append(path: str, data: str):
    try:
        with open(path, 'a') as file:
            file.write(data)
    except Exception:
        raise DistributedFileSystemError(f"append: Path {path} can't be appended!")


##############################################################################
# Delete <path>
def delete(path: str):
    try:
        os.remove(path)
    except Exception:
        raise DistributedFileNotFound(f"delete: Path {path} doesn't exist!")


##############################################################################
# Copy <src_path> to <dest_path>
def copy(src_path: str, dest_path: str):
    try:
        shutil.copyfile(src_path,dest_path)
    except Exception as e:
        raise DistributedFileNotFound(f"copy: Path {src_path} doesn't exist!")


##############################################################################
# Rename <old_path> as <new_path>
def rename(old_path: str, new_path: str):
    try:
        os.rename(old_path, new_path)
    except Exception as e:
        raise DistributedFileNotFound(f"rename: Path {old_path} doesn't exist!")


##############################################################################
# Check if <path> exists
def exists(path: str) -> bool:
    return os.path.exists(path)
