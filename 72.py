#!/usr/bin/env python3
import argparse
import json

from jsonpath_ng import parse
import requests
import urllib3
import yaml


def main():
    urllib3.disable_warnings()

    parser = argparse.ArgumentParser()
    parser.add_argument('--api_jsonrpc',help="'https://127.0.0.1:44372/api_jsonrpc.php'",type=str,required=True)
    parser.add_argument('--token',help="'7aad548037e06da49c5f29cfe990355b25ab0bb482565c79cbdb5ef7164fe565'",type=str,required=True)

    # LDAP settings
    parser.add_argument('--host',help="'dc'",type=str,required=True)
    parser.add_argument('--port',help="'389'",type=str,required=True)
    parser.add_argument('--base_dn',help="'OU=Domain users,DC=custom,DC=lan'",type=str,required=True)
    parser.add_argument('--bind_dn',help="'CN=zbxldap,OU=Service users,DC=custom,DC=lan'",type=str,required=True)
    parser.add_argument('--bind_password',help="'Abc12345'",type=str,required=True)
    parser.add_argument('--groups_file',help="'groups_test.yaml'",type=str,required=True)

    args = parser.parse_args()

    url = args.api_jsonrpc
    token = args.token

    # LDAP related
    host = args.host
    port = args.port
    base_dn = args.base_dn
    bind_dn = args.bind_dn
    bind_password = args.bind_password

    groups_file = args.groups_file

    # define token in header
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer '+token}

    # existing template groups
    templateGroups = parse('$.result').find(json.loads(requests.request("POST", url, headers=headers, data=json.dumps(
        {"jsonrpc":"2.0","method":"templategroup.get","params":{"output":["groupid","name"]},"id":1}
        ), verify=False).text))[0].value
    # print('Template groups:');pprint(templateGroups);print()

    # existing host groups
    hostGroups = parse('$.result').find(json.loads(requests.request("POST", url, headers=headers, data=json.dumps(
        {"jsonrpc":"2.0","method":"hostgroup.get","params":{"output":["groupid","name"]},"id":1}
        ), verify=False).text))[0].value
    # print('Host groups:');pprint(hostGroups);print()

    # existing user groups
    userGroups = parse('$.result').find(json.loads(requests.request("POST", url, headers=headers, data=json.dumps(
        {"jsonrpc":"2.0","method":"usergroup.get","params":{
            "output":["name","templategroup_rights","hostgroup_rights","usrgrpid"],
            "selectTemplateGroupRights":"query",
            "selectHostGroupRights":"query"},"id":1}
        ), verify=False).text))[0].value
    #print('User groups:');pprint(userGroups);print()

    # Load YAML file
    with open(groups_file, "r") as file:
        data = yaml.safe_load(file)

    # Iterate over YAML data
    for ldap, values in data.items():
        prefix = values["prefix"]  # Extract the prefix value

        # by default host group does not exist
        hg_exist = 0

        # check all existing host groups
        for hg in hostGroups:
            if hg['name'] == prefix:
                hg_exist = 1
                break

        # if host group was never found
        if not hg_exist:
            print('need to create host group: '+prefix)
            createNewHostGroup = parse('$.result').find(json.loads(requests.request("POST", url, headers=headers, data=json.dumps(
                {"jsonrpc":"2.0","method":"hostgroup.create","params":{"name":prefix},"id":1}
                ), verify=False).text))[0].value
        
        # by default template group does not exist
        tg_exist = 0
        for tg in templateGroups:
            if tg['name'] == 'templates/'+prefix:
                tg_exist = 1
                break

        if not tg_exist:
            print('need to create teamplate group: '+prefix)
            createNewTemplateGroup = parse('$.result').find(json.loads(requests.request("POST", url, headers=headers, data=json.dumps(
                {"jsonrpc":"2.0","method":"templategroup.create","params":{"name":'templates/'+prefix},"id":1}
                ), verify=False).text))[0].value
        #else:
         #   print('template group \"'+prefix+'\" already exist')



    # situation has been changed and need to fetch all host and template groups
    templateGroups = parse('$.result').find(json.loads(requests.request("POST", url, headers=headers, data=json.dumps(
        {"jsonrpc":"2.0","method":"templategroup.get","params":{"output":["groupid","name"]},"id":1}
        ), verify=False).text))[0].value
    hostGroups = parse('$.result').find(json.loads(requests.request("POST", url, headers=headers, data=json.dumps(
        {"jsonrpc":"2.0","method":"hostgroup.get","params":{"output":["groupid","name"]},"id":1}
        ), verify=False).text))[0].value

    # iterate through same yaml loop, but this time a user group will be made
    for ldap, values in data.items():
        prefix = values["prefix"]

        # reset array "hostgroup_rights"
        hostgroup_rights = []
        # reset array "templategroup_rights"
        templategroup_rights = []

        # by default we assume user group does not exist
        ug_exist = 0
        for ug in userGroups:
            if ug['name'] == prefix:
                ug_exist = 1
                break

        # next 2 blocks prepare ideal structure (just exact amount of permissions) of user and template groups

        # locate host group ID which it will need write access
        for hg in hostGroups:
            if hg['name'] == prefix:
                # a dd my own host group as writeable
                hostgroup_rights.append({"id":hg['groupid'],"permission":"3"})
            else:
                # check if the host group (already in Zabbix) exist in YAML
                for ldap_rescan, prefix_rescan in data.items():
                    if prefix_rescan['prefix'] == hg['name']:
                        hostgroup_rights.append({"id":hg['groupid'],"permission":"2"})


        # locate template group ID which it will need write access
        for tg in templateGroups:
            if tg['name'] == 'templates/'+prefix:
                # add my own template group as writable
                templategroup_rights.append({"id":tg['groupid'],"permission":"3"})
            else:
                # check if list of template groups in Zabbix exist in YAML
                for ldap_rescan, prefix_rescan in data.items():
                    if 'templates/'+prefix_rescan['prefix'] == tg['name']:
                        templategroup_rights.append({"id":tg['groupid'],"permission":"2"})

        # will create new or edit existing

        # if user group was not found
        if not ug_exist:

            # every user group should always have at least one host and template group
            if len(hostgroup_rights)>0 and len(templategroup_rights)>0:
                print('user group \"'+prefix+'\"is about to be made')
                print(json.dumps({"jsonrpc":"2.0","method":"usergroup.create","params":{"name":prefix,"hostgroup_rights":hostgroup_rights,"templategroup_rights":templategroup_rights},"id":1},indent=4, default=str))
                createNewUG = parse('$.result').find(json.loads(requests.request("POST", url, headers=headers, data=json.dumps(
                {"jsonrpc":"2.0","method":"usergroup.create","params":{
                    "name":prefix,"hostgroup_rights":hostgroup_rights,"templategroup_rights":templategroup_rights
                },"id":1}), verify=False).text))[0].value

        # if user group exist then need to validate how precise the structure is
        # extract all characteristics of existing user group
        for ug in userGroups:
            if prefix == ug['name']:
                existing_hostgroup_rights = ug['hostgroup_rights']
                existing_templategroup_rights = ug['templategroup_rights']
                if (sorted(existing_hostgroup_rights, key=lambda x: x['id']) == sorted(hostgroup_rights, key=lambda x: x['id'])) and (sorted(existing_templategroup_rights, key=lambda x: x['id']) == sorted(templategroup_rights, key=lambda x: x['id'])):
                    print('desired structure for user group \"'+prefix+'\" is OK')
                else:
                    print('something is off with user group \"'+prefix+'\", need to remaster it')
                    print(json.dumps({"jsonrpc":"2.0","method":"usergroup.update","params":{"usrgrpid":ug['usrgrpid'],"hostgroup_rights":hostgroup_rights,"templategroup_rights":templategroup_rights},"id":1},indent=4, default=str))
                    updateOperation = parse('$.result').find(json.loads(requests.request("POST", url, headers=headers, data=json.dumps(
                    {"jsonrpc":"2.0","method":"usergroup.update","params":{
                    "usrgrpid":ug['usrgrpid'],
                    "hostgroup_rights":hostgroup_rights,
                    "templategroup_rights":templategroup_rights
                    },"id":1}), verify=False).text))[0].value

    # remaster LDAP settings

    # listing all user role IDs
    userRoles = parse('$.result').find(json.loads(requests.request("POST", url, headers=headers, data=json.dumps(
        {"jsonrpc":"2.0","method":"role.get","params":{"output":["roleid","name"]},"id":1}
        ), verify=False).text))[0].value

    userGroups = parse('$.result').find(json.loads(requests.request("POST", url, headers=headers, data=json.dumps(
        {"jsonrpc":"2.0","method":"usergroup.get","params":{"output":["usrgrpid","name"]},"id":1}
        ), verify=False).text))[0].value

    # pick up current LDAP settings
    currentLDAPSettings = parse('$.result').find(json.loads(requests.request("POST", url, headers=headers, data=json.dumps(
        {"jsonrpc":"2.0","method":"userdirectory.get","params":{"output":"extend","selectProvisionMedia":"extend","selectProvisionGroups":"extend"},"id":1}
        ), verify=False).text))[0].value

    # detect any preexisting LDAP settings
    ldapSettingsFound = 0
    for ldap in currentLDAPSettings:
        if int(ldap['idp_type']) == int(1):
            ldapSettingsFound = 1
            provision_media = ldap['provision_media']
            userdirectoryid = ldap['userdirectoryid']
            name = ldap['name']

    # prepare/define new object "provision_groups"
    provision_groups = []

    # iterate through YAML (this is third reference to same file)
    for LDAP_group_pattern, group in data.items():
        prefix = group["prefix"]
        superAdmin = group.get("superAdmin", False)

        print(f"Prefix: {prefix}, Super: {superAdmin}")

        print(LDAP_group_pattern)

        # go through all user groups to find and pick up an existing user group ID
        for ug in userGroups:
            if ug['name'] == prefix:

                # if "superAdmin: yes" then promote user role to "Zabbix Super Admin" (host/template group relations will not matter)
                if superAdmin:
                    provision_groups.append({"name":LDAP_group_pattern,"roleid":"3","user_groups":[{"usrgrpid":ug['usrgrpid']}]})
                else:
                    provision_groups.append({"name":LDAP_group_pattern,"roleid":"2","user_groups":[{"usrgrpid":ug['usrgrpid']}]})
                break

    if ldapSettingsFound:

        # if preexisting settings was found, then update them
        payload = {"jsonrpc":"2.0","method":"userdirectory.update","params": {
            "userdirectoryid": userdirectoryid,
            "name": host,
            "provision_status": "1",
            "description": "",
            "group_name": "cn",
            "user_username": "givenName",
            "user_lastname": "sn",
            "host": host,
            "port": port,
            "base_dn": base_dn,
            "search_attribute": "sAMAccountName",
            "bind_dn": bind_dn,
            "bind_password": bind_password,
            "start_tls": "0",
            "search_filter": "",
            "group_basedn": "",
            "group_member": "",
            "group_filter": "",
            "group_membership": "memberOf",
            "user_ref_attr": "",
            "provision_media": provision_media,
            "provision_groups": provision_groups
            }
            ,"id":1}

        print(json.dumps(payload, indent=4, default=str))

        try:
            response = requests.request(
                "POST", url, headers=headers, data=json.dumps(payload), verify=False
            )

            raw_text = response.text
            print("Raw JSON response:", raw_text)  # Debugging output

            json_response = json.loads(raw_text)
            jsonReply = parse('$.result').find(json_response)[0].value

        except Exception as e:
            print("Error occurred:", str(e))

    else:
        # creat new LDAP mapping
        payload = {"jsonrpc":"2.0","method":"userdirectory.create","params": {
            "idp_type": "1",
            "name": host,
            "provision_status": "1",
            "description": "",
            "group_name": "cn",
            "user_username": "givenName",
            "user_lastname": "sn",
            "host": host,
            "port": port,
            "base_dn": base_dn,
            "search_attribute": "sAMAccountName",
            "bind_dn": bind_dn,
            "bind_password": bind_password,
            "start_tls": "0",
            "search_filter": "",
            "group_basedn": "",
            "group_member": "",
            "group_filter": "",
            "group_membership": "memberOf",
            "user_ref_attr": "",
            "provision_media": [{"mediatypeid":"4","name":"email","attribute":"mail","active":"0","severity":"63","period":"1-7,00:00-24:00"}],
            "provision_groups": provision_groups
            }
            ,"id":1}

        print(json.dumps(payload, indent=4, default=str))

        try:
            response = requests.request(
                "POST", url, headers=headers, data=json.dumps(payload), verify=False
            )

            raw_text = response.text
            print("Raw JSON response:", raw_text)  # Debugging output

            json_response = json.loads(raw_text)
            jsonReply = parse('$.result').find(json_response)[0].value

        except Exception as e:
            print("Error occurred:", str(e))


    # reset flags about authentification type
    # "disabled_usrgrpid": 9 is build in user group "Disabled"
    # https://www.zabbix.com/documentation/7.0/en/manual/api/reference/authentication/object
    resetFlags = parse('$.result').find(json.loads(requests.request("POST", url, headers=headers, data=json.dumps(
        {
        "jsonrpc": "2.0",
        "method": "authentication.update",
        "params": {
            "authentication_type": 1,
            "ldap_auth_enabled": 1,
            "ldap_case_sensitive": 0,
            "ldap_jit_status" : 1, 
            "disabled_usrgrpid": 9
        },
        "id": 1
    }), verify=False).text))[0].value

if __name__ == "__main__":
    main()

