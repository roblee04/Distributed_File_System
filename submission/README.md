# Final Submission Folder for our COEN 317 Group Project

## Team Members: Jordan Randleman, Rahul Yalavarthi, Robin Lee

--------------------------------------------------------------------
## Dependencies:

Create EC2 instances using all the default settings, EXCEPT:
* Enable: `Allow HTTPS traffic from the internet`
* Enable: `Allow HTTP traffic from the internet`

Click on your instance. Navigate from the "Details" tab to the "Security" tab.
Click on the security group. Click on "Edit inbound rules".
Add a rule for "All TCP" with a CIDR blocks value of "0.0.0.0/0". Click "Save rules".

SSH into your instance, then run the following commands:

```sh
curl -O https://bootstrap.pypa.io/get-pip.py
python3 get-pip.py --user
sudo yum update -y
sudo yum install git -y
git clone https://github.com/roblee04/Distributed_File_System/
pip install Flask
```

--------------------------------------------------------------------
## Directory Overview:

1. `client/`:
   * `dfs.py`: Python library code for users to interface with our DFS.
2. `uvm/`:
   * `fs.py`: UVM local file manipulation logic to execute client requests.
   * `server.py`: UVM HTTP server accepting client file requests.
     - Also forwards requests to all RVMs, and ensures at least 1 RVM exists.
3. `rvm/`:
   * `fs.py`: RVM local file manipulation logic to execute UVM requests.
   * `server.py`: RVM HTTP server accepting UVM file requests.
     - Also manages RVM/UVM server health, getting replacements as needed.
     - Also acts on standby if pooled to be allocated later as needed.
4. `server.py`: Middleware/router that clients ping to access our DFS.


--------------------------------------------------------------------
## Running the Middleware Routing Server:

Run `python3 server.py`.

To interact with the webserver, use: `http://<PUBLIC-IP-ADDRESS>:8002/<COMMAND>`
* ___Important: Flask prints out the WRONG IP address!___
  - Find your VM's public IP on the AWS portal.
* The server will print out all available command paths on launch!
* Use `^C` (control-"C") to terminate the server.


--------------------------------------------------------------------
## Running the UVM Client-Listener Server:

### Associating the UVM to RVMs:
Write your UVM's public IP address in `ips/<n>/uvm.txt`.
* `<n>` is the subfolder in `ips` that contains the UVM/RVM family ID
* Find the UVM's public IP on the AWS portal!
* This allows RVMs to detect UVM failures.

Write each RVM public IP address, one per line, in `ips/<n>/rvm.txt`.
* This allows UVMs to forward file requests to their RVMs.
* Also allows for RVMs to monitor each other's health.


### Running the UVM's File System Web Server:
On the UVM: `python3 uvm/server.py <n>`

On each active RVM: `python3 rvm/server.py <n>`

On each pooled RVM: `python3 rvm/server.py 0`
* `0` here denotes that the RVM should stand by for remote activation.

To interact with the UVM webserver, use: `http://<PUBLIC-IP-ADDRESS>:5001/<COMMAND>`
* ___Important: Flask prints out the WRONG IP address!___
  - Find your VM's public IP on the AWS portal.
* The UVM will print out all available command paths on launch!
  - UVMs also forward all file commands to their associated RVMs.
* Use `^C` (control-"C") to terminate the server.

If an RVM replaces the UVM, once that RVM exits, remember to lookup 
and `kill` the process that it spawned to become a UVM!
* Example:
  ```sh
  lsof -i :5001 # yields UVM process information, including the Process ID (PID)
  kill PID # insert PID from the printed info above to kill the spawned UVM
  ```


--------------------------------------------------------------------
## Example:

Suppose we have 2 UVMs with 3 RVMs per UVM, and 5 pooled RVMs for later allocation. 

Further assume we've already put the 1st UVM/RVM IP addresses in `ips/1/`, 
and the 2nd in `ips/2/`. We also need the middleware IP in `ips/middleware.txt` 
and `client/dfs.py`'s `MIDDLEWARE_IP_ADDRESS` global variable. Finally, we put 
all of our pool RVM IP addresses in `ips/pool-ips.txt`. All that having been 
done, we can launch our EC2s!

We can set our EC2s up to use `client/dfs.py` by doing the following:

1. SSH into the 1st UVM and its RVMs.
2. In the UVM: `cd Distributed_File_System/submission/uvm/ && python3 server.py 1`
3. In each RVM: `cd Distributed_File_System/submission/rvm/ && python3 server.py 1`
   * Note that all 3 RVMs must launch within 3sec of one another, otherwise a leader will be preemptively elected!
4. SSH into the 2nd UVM and its RVMs. Launch its UVM and RVMs exactly like the 1st UVM, but with `2` instead of `1`.
5. SSH into the pool RVMs, and run: `cd Distributed_File_System/submission/rvm/ && python3 server.py 0`
6. SSH into the router, and run: `cd Distributed_File_System/submission/ && python3 server.py`

Then, in another terminal, navigate into `client/`. Run `python3` at the command line to launch the REPL, then `import dfs` to be able to use `dfs.py`'s functions as methods on the `dfs` module object, thereby dynamically testing out our distributed file system! :)

