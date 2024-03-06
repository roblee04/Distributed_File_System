# User Virtual Machines (UVMs)

UVMs are the main machines hosting user files in the DFS. Users send file commands to the central router (middleware), which then forwards the request to a UVM.

UVMs are managed in a pool tracked by our middleware, so as to be able to easily find/add new UVMs in/to the network. If more file resources are needed, a new UVM is spun up and added to the pool.

Each UVM has a series of Replacement Virtual Machines (RVMs) that are responsible for acting as a backup measure in the event of UVM failure. Every file command sent to a UVM is forwarded to its RVMs. If a UVM goes down, an RVM will be elected in order to become the new UVM, and a new RVM will be spun up in its place. RVMs are also responsible for periodically polling each other to ensure they haven't failed, and if they have, other RVMs are spun up in their place. See `rvm/README.md` for more details.