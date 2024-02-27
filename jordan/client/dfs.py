# Author: Jordan Randleman - dfs.py
# Purpose:
#   Python library that clients can invoke to interact with our DFS.

# PROVIDED APIs:
#   1. read a file
#   2. write data (also creates files)
#   3. append data (also creates files)
#   4. delete a file
#   5. copy a file
#   6. rename (also moves) a file
#   7. check if a file exists

##############################################################################
# Read the contents of a file
def read(path: str) -> str:
    # ... delete file at <path> on the remote server ...
    raise Exception("unimplemented: read path")


##############################################################################
# Write data to a file (creates a file if DNE)
def write(path: str, data: str):
    # ... delete file at <path> on the remote server ...
    raise Exception("unimplemented: write data")


##############################################################################
# Append data to a file (creates a file if DNE)
def append(path: str, data: str):
    # ... delete file at <path> on the remote server ...
    raise Exception("unimplemented: append data")


##############################################################################
# Delete a file
def delete(path: str):
    # ... delete file at <path> on the remote server ...
    raise Exception("unimplemented: delete path")


##############################################################################
# Copy a file
def copy(src_path: str, dest_path: str):
    # ... copy file at <src_path> to <dest_path> on the remote server ...
    raise Exception("unimplemented: copy path")


##############################################################################
# Rename a file (also moves files)
def rename(old_path: str, new_path: str):
    # ... rename file at <old_path> as <new_path> on the remote server ...
    raise Exception("unimplemented: rename path")


##############################################################################
# Checks if a file exists
def exists(path: str) -> bool:
    # ... determine if file at <path> is on the remote server ...
    raise Exception("unimplemented: path exists?")
