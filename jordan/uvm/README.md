# User Virtual Machines (UVMs)

UVMs are the main machines hosting user files in the DFS. Users send file commands to the central router, which then forwards the request to a UVM.

UVMs are linked in a ring, so as to be able to easily find new machines in the network. If more file resources are needed, a new UVM is spun up and added to the ring.

Each UVM has a series of Replacement Virtual Machines (RVMs) that are responsible for acting as a backup measure in the event of UVM failure. Every file command sent to a UVM is forwarded to its RVMs. If a UVM goes down, an RVM will be elected in order to become the new UVM, and a new RVM will be spun up in its place. UVMs are responsible for periodically polling their RVMs to ensure they haven't failed, and if they have, another RVM is spun up. See `rvm/README.md` for more details.