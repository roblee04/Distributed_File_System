# restore.sh - Restore the original IP addresses in "/ips/"

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

curl -L https://raw.githubusercontent.com/roblee04/Distributed_File_System/main/jordan/ips/1/rvm.txt > $SCRIPT_DIR/ips/1/rvm.txt
curl -L https://raw.githubusercontent.com/roblee04/Distributed_File_System/main/jordan/ips/1/uvm.txt > $SCRIPT_DIR/ips/1/uvm.txt
curl -L https://raw.githubusercontent.com/roblee04/Distributed_File_System/main/jordan/ips/2/rvm.txt > $SCRIPT_DIR/ips/2/rvm.txt
curl -L https://raw.githubusercontent.com/roblee04/Distributed_File_System/main/jordan/ips/2/uvm.txt > $SCRIPT_DIR/ips/2/uvm.txt