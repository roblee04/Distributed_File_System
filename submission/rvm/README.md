# Replacement Virtual Machines (RVMs)

RVMs are the backup system for UVMs. See `uvm/README.md` for more details.

Each RVM has a file containing all IP addresses for the other RVMs associated to the given UVM.
This file is used to elect an RVM leader (more on that in a bit!) responsible for both replacing
missing UVMs and RVMs.

If the leader detects that the UVM is missing, it spawns a new RVM to take its place, and converts itself into a UVM.

The leader pings every RVM every `T` time units confirming it is alive, expecting a response confirming the RVM is alive.
1. If an RVM doesn't recieve leader notice in `T` time units, it starts the leader election protocol.
   * The RVM will find the max IP address in its RVM IP address list file, then ping that RVM to tell it that it is the leader, expecting a response.
   * If that leader does not respond, it is assumed dead, and the next highest RVM is pinged as the leader, etc.
2. If the leader doesn't recieve confirmation in time from an RVM, that RVM is presumed dead.
   * The RVM is replaced by the leader with another RVM
   * That RVM's replacement of the old RVM is propagated across RVMs for them to update their IP address files.