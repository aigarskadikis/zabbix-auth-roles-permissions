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

# pick up current LDAP settings
currentLDAPSettings = parse('$.result').find(json.loads(requests.request("POST", url, headers=headers, data=json.dumps(
    {"jsonrpc":"2.0","method":"userdirectory.get","params":{"output":"extend","selectProvisionMedia":"extend","selectProvisionGroups":"extend"},"id":1}
    ), verify=False).text))[0].value

userdirectory_mediaid = currentLDAPSettings[0]['provision_media'][0]['userdirectory_mediaid']
userdirectoryid = currentLDAPSettings[0]['userdirectoryid']
name = currentLDAPSettings[0]['name']

print('userdirectory_mediaid is: '+userdirectory_mediaid)
print('userdirectoryid is: '+userdirectoryid)
print('name is: '+name)

# listing all user role IDs
userRoles = parse('$.result').find(json.loads(requests.request("POST", url, headers=headers, data=json.dumps(
    {"jsonrpc":"2.0","method":"role.get","params":{"output":["roleid","name"]},"id":1}
    ), verify=False).text))[0].value

pprint(userRoles)


# listing all user group IDs
userGroups = parse('$.result').find(json.loads(requests.request("POST", url, headers=headers, data=json.dumps(
    {"jsonrpc":"2.0","method":"usergroup.get","params":{"output":["usrgrpid","name"]},"id":1}
    ), verify=False).text))[0].value
pprint(userGroups)

# prepare/define new object "provision_groups"
provision_groups = []

# importing CSV into memory
file = open("ldapmap.csv",'rt')
reader = csv.DictReader( file )

# check if user role and user group from CSV exist in Zabbix
for line in reader:
    roleid = 0
    usrgrpid = 0

    # validate existance of user role
    for role in userRoles:
        if role['name'] == line['User role']:
            roleid = role['roleid']
            break
    else:
        print('User role "'+line['User role']+'" not exist')

    # validate existance of user group
    for group in userGroups:
        if group['name'] == line['User groups']:
            usrgrpid = group['usrgrpid']
            break
    else:
        print('User group "'+line['User groups']+'" not exist')

    # if user role or user group does not exist, its a deal breaker
    if roleid == 0 or usrgrpid == 0:
        print('record not possible to create: '+line['LDAP group pattern']+', '+line['User groups']+', '+line['User role'])
    else:
        # add a new entry which will be used in a bulk API update
        provision_groups.append({"name":line['LDAP group pattern'],
            "roleid":roleid,
            "user_groups":[{"usrgrpid":usrgrpid}]})

# print new future mapping
pprint(provision_groups)


newMappingLDAP = parse('$.result').find(json.loads(requests.request("POST", url, headers=headers, data=json.dumps(
    {
    "jsonrpc": "2.0",
    "method": "userdirectory.update",
    "params": {
        "userdirectoryid": userdirectoryid,
        "provision_media": [
                {
                    "userdirectory_mediaid": userdirectory_mediaid
                }
            ],
            "provision_groups": provision_groups
    },
    "id": 1
}
    ), verify=False).text))[0].value

pprint(newMappingLDAP)
# go line by line of CSV:
#   if user role (case sensitive) or user group (case sensitive) does not exist:
#     print warning on screen and ignore the line
#   otherwise:
#     read LDAPgrouppatter, read ZabbixUserGroupID, read ZabbixUserRoleID
#     add new row into "provision_groups" array
#

# if lenght of "provision_groups" list is greater than 0:
#   execute ZabbixAPI userdirectory.update



#pprint(currentLDAPSettings)
