# File: fs.py
# Purpose:
#   Server functionality to operate on local files.
#   Called by an HTTP webserver process.

# SUPPORTED APIs:
#   1. read a file
#   2. write data (also creates files)
#   3. delete a file
#   4. copy a file
#   5. rename (also moves) a file
#   6. check if a file exists

import os
import shutil

##############################################################################
# Anchoring our FS operations to a certain directory
ROOT_DIRECTORY = os.path.dirname(__file__)+'/../rootdir/'


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
        with open(ROOT_DIRECTORY+path, 'r') as file:
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
        with open(ROOT_DIRECTORY+path, 'w') as file:
            file.write(data)
    except Exception:
        raise DistributedFileSystemError(f"write: Path {path} can't be written!")


##############################################################################
# Delete <path>
def delete(path: str):
    try:
        os.remove(ROOT_DIRECTORY+path)
    except Exception:
        raise DistributedFileNotFound(f"delete: Path {path} doesn't exist!")


##############################################################################
# Copy <src_path> to <dest_path>
def copy(src_path: str, dest_path: str):
    try:
        shutil.copyfile(ROOT_DIRECTORY+src_path,ROOT_DIRECTORY+dest_path)
    except Exception as e:
        raise DistributedFileNotFound(f"copy: Path {src_path} doesn't exist!")


##############################################################################
# Rename <old_path> as <new_path>
def rename(old_path: str, new_path: str):
    try:
        os.rename(ROOT_DIRECTORY+old_path,ROOT_DIRECTORY+new_path)
    except Exception as e:
        raise DistributedFileNotFound(f"rename: Path {old_path} doesn't exist!")


##############################################################################
# Check if <path> exists
def exists(path: str) -> bool:
    return os.path.exists(ROOT_DIRECTORY+path)
