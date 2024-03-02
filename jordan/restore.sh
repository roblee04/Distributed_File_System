# restore.sh - Restore the original IP addresses in "/ips/"

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

curl -L https://raw.githubusercontent.com/roblee04/Distributed_File_System/main/jordan/ips/rvm.txt > $SCRIPT_DIR/ips/rvm.txt
curl -L https://raw.githubusercontent.com/roblee04/Distributed_File_System/main/jordan/ips/uvm.txt > $SCRIPT_DIR/ips/uvm.txt