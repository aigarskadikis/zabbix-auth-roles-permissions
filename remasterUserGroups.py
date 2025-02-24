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

import argparse

parser = argparse.ArgumentParser()
parser.add_argument(
    '-t', '--templateGroupCreate',
    help='flag to create template group if it does not exist, default: False',
    action='store_true'
)
parser.add_argument(
    '-o', '--hostGroupCreate',
    help='flag to create host group if it does not exist, default: False',
    action='store_true'
)

args = parser.parse_args()

templateGroupCreate = args.templateGroupCreate
hostGroupCreate = args.hostGroupCreate


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


# read "user group" => "host group" mapping into memory
hosts_map_csv = open("user_group_hosts.csv",'rt')
hosts_map = csv.DictReader( hosts_map_csv )

# read "user group" => "template group" mapping into memory
templates_map_csv = open("user_group_templates.csv",'rt')
templates_map = csv.DictReader( templates_map_csv )

# file validation
#  

# read line
# validate if template group exist
# validate if host group exists
#   if not exist then:
#     create new host group
# rerun hostgroup get API call to ensure more groups exist
# empty/reset array "hostgroup_rights"
# empty/reset array "templategroup_rights"
# if template group and host group exists then
#   validate if user group with such name exist
#     if exist then:
#       read user group id
#       use "usergroup.update" API method to overwrite settings with new definition in csv
#     else:
#       use "usergroup.create" API method to create new group

