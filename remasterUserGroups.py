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


userGroupNames = set()

# Read "User group" => "Host permissions" mapping into memory
with open("User_groups_Host_permissions_map.csv", 'rt') as f:
    User_groups_Host_permissions_map = list(csv.DictReader(f))  # Convert to a list for immediate use

# Read "User group" => "Template permissions" mapping into memory
with open("User_groups_Template_permissions_map.csv", 'rt') as f:
    User_groups_Template_permissions_map = list(csv.DictReader(f))


# 1.0 file structure validation
#   if file contains '\' symbol then exit program. highlight cell
#   if one of cells has trailing or leading space, then exist program, but highlight the cell
# allow characters per cell are'[a-zA-Z0-9]

# 2.0 create missing host/template groups if allowed by program
# 2.1 read line per templates_map csv
# validate if template group exist
#   if not exist
#     check flag to create template group
#     if flag=yes:
#       create new template group
#     else:
#       do nothina
# 2.1.1 backtrack if all nested groups has been made
#   read every group name and scan '/' symbol
#     if found then cut right portion away and search if such group exists
#     if not exists then create a blank group

# go through host group csv
for new_hg in User_groups_Host_permissions_map:
    # filter out unique names (this is not related to main cycle)
    userGroupNames.add(new_hg['User group'])
    # host group not recognized yet
    hg_exist = 0
    # go through existing
    for ins_hg in hostGroups:
        if new_hg['Host group'] == ins_hg['name']:
            # mask host group as found
            hg_exist = 1
            break

    # if host group was never found
    if not hg_exist:
        if hostGroupCreate:
            print('Creating host group \"'+new_hg['Host group']+'\" now..')
        else:
            print('Need to create \"'+new_hg['Host group']+'\" but no flag was given. Use -o to create missing host groups automatically')

print()

for new_tg in User_groups_Template_permissions_map:
    # filter out unique names (this is not related to main cycle)
    userGroupNames.add(new_tg['User group'])
    # template group not recognized yet
    tg_exist = 0
    # go through existing
    for ins_tg in templateGroups:
        if new_tg['Template group'] == ins_tg['name']:
            # mask template group as found
            tg_exist = 1
            break

    # if template group was never found
    if not tg_exist:
        if templateGroupCreate:
            print('Creating template group \"'+new_tg['Template group']+'\" now..')
        else:
            print('Need to create \"'+new_tg['Template group']+'\" but no flag was given. Use -t to create missing template groups automatically')
print()

print('unique user groups to work with: ')
userGroupNames = list(userGroupNames)
pprint(userGroupNames)
print()
# 2.2 read line per hosts_map csv
# validate if host group exists
#   if not exist then:
#     create new host group

# 2.2.1 backtrack if all nested groups has been made
#   read every group name and scan '/' symbol
#     if found then cut right portion away and search if such group exists
#     if not exists then create a blank group


# 3.0 rerun hostgroup.get and templategroup.get API call to ensure more groups exist
# if there was a flag given to recreate template groups automatically, then pick up all "Template groups" again
if templateGroupCreate:
    templateGroups = parse('$.result').find(json.loads(requests.request("POST", url, headers=headers, data=json.dumps(
        {"jsonrpc":"2.0","method":"templategroup.get","params":{"output":["groupid","name"]},"id":1}
        ), verify=False).text))[0].value

# if there was a flag given to recreate host groups automatically then pick up all "Host groups" again
if hostGroupCreate:
    hostGroups = parse('$.result').find(json.loads(requests.request("POST", url, headers=headers, data=json.dumps(
        {"jsonrpc":"2.0","method":"hostgroup.get","params":{"output":["groupid","name"]},"id":1}
        ), verify=False).text))[0].value



# read all unique user groups
for ug in userGroupNames:

    # if group name is listed in templates permissions file
    for hg in User_groups_Host_permissions_map:
        if ug == hg['User group']:
            print(hg['User group']+' exists in hosts permissions file')





    # if group name is listed in hosts permissions file
    for tg in User_groups_Template_permissions_map:
        if ug == tg['User group']:
            print(hg['User group']+' exists in templates permissions file')


# 4.0 read both "csv" lists and seek for a matching "user role"
#   prepare API update operation
#     reset array "hostgroup_rights"
#     reset array "templategroup_rights"
# 0 - access denied;
# 2 - read-only access;
# 3 - read-write access.










# 5.0 
# if template group and host group exists then
#   validate if user group with such name exist
#     if exist then:
#       read user group id
#       use "usergroup.update" API method to overwrite settings with new definition in csv
#     else:
#       use "usergroup.create" API method to create new group



