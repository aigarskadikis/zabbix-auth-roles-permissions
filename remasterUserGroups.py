#!/usr/bin/env python3.10
import sys
sys.path.insert(0,'/var/lib/zabbix')
import config
import os
import requests
import json
from jsonpath_ng import jsonpath, parse
import csv
from pprint import pprint
import urllib3
urllib3.disable_warnings()

url = config.api_jsonrpc
token = config.api_token

# define token in header
headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer '+token}

# pick up all "User groups"
userGroups = parse('$.result').find(json.loads(requests.request("POST", url, headers=headers, data=json.dumps(
    {"jsonrpc":"2.0","method":"usergroup.get","params":{
        "output":["name","templategroup_rights","hostgroup_rights","usrgrpid"],
        "selectTemplateGroupRights":"query",
        "selectHostGroupRights":"query"},"id":1}
    ), verify=False).text))[0].value
print('User groups:');pprint(userGroups);print()

# pick up "Template groups"
templateGroups = parse('$.result').find(json.loads(requests.request("POST", url, headers=headers, data=json.dumps(
    {"jsonrpc":"2.0","method":"templategroup.get","params":{"output":["groupid","name"]},"id":1}
    ), verify=False).text))[0].value
print('Template groups:');pprint(templateGroups);print()

# pick up "Host groups"
hostGroups = parse('$.result').find(json.loads(requests.request("POST", url, headers=headers, data=json.dumps(
    {"jsonrpc":"2.0","method":"hostgroup.get","params":{"output":["groupid","name"]},"id":1}
    ), verify=False).text))[0].value
print('Host groups:');pprint(hostGroups);print()
# importing CSV into memory
#file = open("user_group_templates.csv",'rt')
#reader = csv.DictReader( file )

