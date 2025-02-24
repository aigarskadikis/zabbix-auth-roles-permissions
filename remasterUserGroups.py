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

# Define the mapping
permission = {
    "Deny": 0,
    "Read": 2,
    "Write": 3,
    "deny": 0,
    "read": 2,
    "write": 3
}


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


# One time supply with group ID for host CSV inputs
for hg_csv in User_groups_Host_permissions_map:
    for hg_ins in hostGroups:
        if hg_csv['Host group'] == hg_ins['name']:
            hg_csv["id"] = hg_ins['groupid']
            hg_csv["permission"] = permission.get(hg_csv["Permission"],99)

# One time supply with group ID for templates CSV inputs
for tg_csv in User_groups_Template_permissions_map:
    for tg_ins in templateGroups:
        if tg_csv['Template group'] == tg_ins['name']:
            tg_csv["id"] = tg_ins['groupid']
            tg_csv["permission"] = permission.get(tg_csv["Permission"],99)

pprint(User_groups_Host_permissions_map)
pprint(User_groups_Template_permissions_map)

# read all unique user groups
for ug in userGroupNames:

    # reset array "hostgroup_rights"
    hostgroup_rights = []
    # reset array "templategroup_rights"
    templategroup_rights = []

    # if group name is listed in hosts permissions file, then read line (host group, permission level) and add to bulk update
    for hg in User_groups_Host_permissions_map:
        if ug == hg['User group']:
            print(hg['User group']+' exists in hosts permissions file')
            if 'id' in hg and 'permission' in hg:
                hostgroup_rights.append({
                    "id":hg['id'],
                    "permission":hg['permission']
                    })

    pprint(hostgroup_rights)


    # if group name is listed in templates permissions file, then read line (template group, permission level) and add to bulk update
    for tg in User_groups_Template_permissions_map:
        if ug == tg['User group']:
            print(tg['User group']+' exists in templates permissions file')
            if 'id' in tg and 'permission' in tg:
                templategroup_rights.append({
                    "id":tg['id'],
                    "permission":tg['permission']
                    })

    pprint(templategroup_rights)



    # check if this is fresh user group
    user_group_exist = 0
    for existing_ug in userGroups:
        if ug == existing_ug['name']:
            user_group_exist = 1
            break

    ug_to_update = 0
    if user_group_exist:
        print('User group already exist: '+ug)

        # read existing ID of user group
        for existing_ug in userGroups:
            if existing_ug['name'] == ug:
                ug_to_update = existing_ug['usrgrpid']

        print('user group to update: '+ug_to_update)

        pprint(json.dumps({"jsonrpc":"2.0","method":"usergroup.update","params":{"usrgrpid":ug_to_update,"hostgroup_rights":hostgroup_rights,"templategroup_rights":templategroup_rights},"id":1}))

        if len(hostgroup_rights)>0 and len(templategroup_rights)>0:
            print('match')
            updateOperation = parse('$.result').find(json.loads(requests.request("POST", url, headers=headers, data=json.dumps(
                {"jsonrpc":"2.0","method":"usergroup.update","params":{
                "usrgrpid":ug_to_update,
                "hostgroup_rights":hostgroup_rights,
                "templategroup_rights":templategroup_rights
                },"id":1}), verify=False).text))[0].value

            pprint(updateOperation)



    else:
        print('Need to create new User group: '+ug)


# 5.0
# read all unqieu user group names
#   if user group does not exist then
#     creta new user group. usergroup.create
#   else:
#     update existing. usergroup.update




