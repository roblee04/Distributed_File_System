# Jordan's Development Folder for COEN 317

--------------------------------------------------------------------
## Dependancies:

```sh
pip install Flask
```

--------------------------------------------------------------------
## File Overview:

1. `client/dfs.py`: Python skeleton code for users to interface with our DFS.
2. `uvm/fs.py`: UVM local file manipulation logic to execute client requests.
3. `uvm/client_listener.py`: UVM HTTP server accepting client file requests.


--------------------------------------------------------------------
## Running the Server:

```sh
python3 uvm/client_listener.py
```

The program will print out directions for you to test the server!
Use `^C` (control-"C") to terminate the server.
