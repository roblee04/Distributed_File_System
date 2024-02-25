# Author: Jordan Randleman - dfs.py
# Purpose:
#   Python library that clients can invoke to interact with our DFS.



# ############################################################################
# @TODO: IMPLEMENT THE PROPER HTTP CALLS TO OUR DFS FROM CLASS METHODS!
# @TODO: CURRENTLY NOT IMPLEMENTING "DELETE N BYTES": ONLY "DELETE A FILE"
# ############################################################################



# PROVIDED APIs:
#   1. read N bytes (or all bytes if given -1)
#   2. write N bytes (also creates files)
#   3. append N bytes (also creates files)
#   4. delete a file (static method)
#   5. copy a file  (static method)
#   6. rename (also moves) a file  (static method)
#   7. check if a file exists  (static method)

##############################################################################
# Constant Value(s)
READ_ENTIRE_PATH = -1 # used by <read>


##############################################################################
# Distributed File Object Class
class DistributedFile:
    ##########################################################################
    # Constructor accepts the distributed file's path name
    def __init__(self, path: str):
        # ... LOGIC TO ESTABLISH A CONNECTION TO THE SERVER ...
        self.path = path  # string location of the file in question
        self.position = 0 # byte position to operate on the file from

    ##########################################################################
    # Instance APIs
    def read(self, n_bytes: int = READ_ENTIRE_PATH):
        # ... read N bytes (or all bytes if N=-1) from the file located on the remote server ...
        raise Exception("unimplemented: read n bytes")

    def write(self, data: str):
        # ... write <data> to the file located on the remote server (create if DNE) ...
        raise Exception("unimplemented: write data")

    def append(self, data: str):
        # ... append <data> to the file located on the remote server (create if DNE) ...
        raise Exception("unimplemented: append data")

    ##########################################################################
    # Static APIs
    def delete(path: str):
        # ... delete file at <path> on the remote server ...
        raise Exception("unimplemented: delete path")

    def copy(src_path: str, dest_path: str):
        # ... copy file at <src_path> to <dest_path> on the remote server ...
        raise Exception("unimplemented: copy path")

    def rename(old_path: str, new_path: str):
        # ... rename file at <old_path> as <new_path> on the remote server ...
        raise Exception("unimplemented: rename path")

    def exists(path: str) -> bool:
        # ... determine if file at <path> is on the remote server ...
        raise Exception("unimplemented: path exists?")
