import json
from pssh.clients import ParallelSSHClient
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--start", action="store_true", help="start jupyter servers")
parser.add_argument("--stop", action="store_true", help="stop all jupyter servers")
parser.add_argument("--list", action="store_true", help="List jupyter server information.")
parser.add_argument("--test", action="store_true", help="List jupyter server information.")
args = parser.parse_args()


file_path = "ip_logs"
ips = []
with open(file_path, "r") as fp:
    data = json.load(fp)
    num_ips = len(data)
    for i, machine in enumerate(data):
        ip = machine["ipAddress"]
        ips.append(ip)

print(ips)
print(len(ips))

# Write the IP address somewhere
to_write = "ips.txt"
with open(to_write, "w") as tw:
    for ip in ips:
        tw.write(ip + "\n")

client = ParallelSSHClient(ips, user="mc2", pkey="/home/hao/.ssh/mc2-key")

start_cmd = """
jupyter notebook stop 8888
jupyter notebook stop 8889
sudo su
cd /home/mc2/risecamp/mc2/tutorial
whoami
jupyter notebook stop 8888
jupyter notebook stop 8889
jupyter notebook --ip 0.0.0.0 --port 8888 --allow-root --no-browser & 
jupyter notebook --ip 0.0.0.0 --port 8889 --allow-root --no-browser & 
"""

stop_cmd = """
jupyter notebook stop 8888
jupyter notebook stop 8889
sudo su
jupyter notebook stop 8888
jupyter notebook stop 8889
"""

list_cmd = """
sudo su
jupyter notebook list
"""

test_cmd = """
sudo su
whoami
"""

if args.start:
    cmd = start_cmd
if args.stop:
    cmd = stop_cmd
if args.list:
    cmd = list_cmd
if args.test:
    cmd = test_cmd

shells = client.open_shell()
client.run_shell_commands(shells, cmd)
client.join_shells(shells)
for shell in shells:
    for line in shell.stdout:
        print(line)
    print(">>>>>>>>>>")
