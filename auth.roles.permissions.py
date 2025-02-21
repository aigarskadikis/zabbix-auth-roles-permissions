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

import optparse
parser=optparse.OptionParser()
parser.add_option('-g','--group',help='group names')
parser.add_option('-l','--limit',help='limit the call',type=int)
(opts,args) = parser.parse_args()

if opts.limit:
    if not opts.group:
        limit=opts.limit
    else:
        limit=99999
else:
    limit=99999

print()
url = config.api_jsonrpc
token = config.api_token


# listing existing auth settings
headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer '+token}

currentLDAPSettings = parse('$.result').find(json.loads(requests.request("POST", url, headers=headers, data=json.dumps(
{"jsonrpc":"2.0","method":"authentication.get","params":{"output":"extend"},"id":1}
), verify=False).text))[0].value

print(currentLDAPSettings)

