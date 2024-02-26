# Replacement Virtual Machines (RVMs)

RVMs are the backup system for UVMs. See `uvm/README.md` for more details.

RVMs are responsible for periodically polling their UVM to ensure it hasn't failed, and if it has, another RVM is elected to become the new UVM. The RVM-to-UVM election protocol makes an alteration to the "ring leadership election protocol". 

1. All RVMs are linked in a ring.
2. When an RVM notices its UVM went down, it initiates the leader election protocol.
3. Each RVM will compare its IP address to its neighbors. The RVM that has the highest IP address wins.
4. When an RVM gets its own IP address back, that RVM knows it is the leader. 
5. The leader will ping the Central Router for the current Election Counter (EC).
6. The leader will forward the EC to each RVM in the ring, along with itself declared as the new leader.
7. If the leader gets a message confirming itself as the leader with the current election counter, it becomes the UVM and requests a replacement RVM.
8. If an RVM gets a leader declaration with a preexisting EC, it knows that the leader died before it could become a UVM. The leadership protocol is restarted.