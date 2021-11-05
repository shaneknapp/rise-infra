
### Install Azure CLI

```python
# MacOS
brew update && brew install azure-cli
```

```python
# Ubuntu
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

### Start a VM Scale Set via Azure GUI
Use the Azure **Custom Deployment** to deploy a scale set. Use the ARM template under [arm/template.json](arm/template.json). 
Remember to specify the number and type of instances you need. For MC^2 tutorial of RISECamp 2021, the number is 100.

The template has several places that is customizable, such as the image you want each instance to start from, instance types, etc.
You can read the json file and try to understand it, or send me a message (hao@cs.berkeley.edu) to ask.


### Setup Azure CLI

```
# Need username and password
az login 

# replace [scale-set-name] with the VM scale set name created in Azure.
az vmss list-instance-public-ips --resource-group hao-test-group --name [scale-set-name] > ip_logs
```
The above command will pull some meta information about all the instances in the scale set. We next use a Python script to parse the meta information to get all the IPs, and then start Jupyter notebooks in each IP.

```python
# install some deps
pip install parallel-ssh

# start jupyter notebooks
python parse_public_ips.py --start

# stop all jupyter notebooks
python parse_public_ips.py --stop

# list all active notebooks
python parse_public_ips.py --list
```

