# Jordan's Development Folder for COEN 317

--------------------------------------------------------------------
## Dependancies:

Create an EC2 instance using all the default settings, EXCEPT:
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
cd Distributed_File_System
pip install Flask
```

--------------------------------------------------------------------
## Directory Overview:

1. `client`:
   * `dfs.py`: Python skeleton code for users to interface with our DFS.
2. `uvm`:
   * `fs.py`: UVM local file manipulation logic to execute client requests.
   * `client_listener.py`: UVM HTTP server accepting client file requests.


--------------------------------------------------------------------
## Running the UVM Client-Listener Server:

```sh
python3 uvm/client_listener.py
```

To interact with the webserver, use: `http://<PUBLIC-IP-ADDRESS>:5000/<COMMAND>`
* ___Important: Flask prints out the WRONG http address!___
  - Find your VM's public IP on the AWS portal.
* The webserver will print out all available command paths on launch!
* Use `^C` (control-"C") to terminate the server.
