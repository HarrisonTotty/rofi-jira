#!/usr/bin/env python3
'''
rofi-jira

Script to display JIRA tickets with rofi.
'''

import argparse
import getpass
import jira
import os
import subprocess
import sys
import yaml
import re

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

argparser = argparse.ArgumentParser(
    description = 'A python wrapper script around rofi to search through JIRA issues',
    epilog = '',
    usage = 'rofi-jira [--config FILE] [--search STR] [--username STR] [--password STR]',
    add_help = False,
    formatter_class = lambda prog: argparse.RawDescriptionHelpFormatter(prog, max_help_position=45, width=100)
)
argparser.add_argument(
    '-c',
    '--config',
    default = os.getenv('ROFI_JIRA_CONFIG', os.path.expanduser('rofi-jira.yaml')),
    dest = 'config',
    help = '[env: ROFI_JIRA_CONFIG] Specifies the configuration YAML file to grab search strings from. Defaults to "rofi-jira.yaml".',
    metavar = 'FILE'
)
argparser.add_argument(
    '-h',
    '--help',
    action = 'help',
    help = 'Displays help and usage information.'
)
argparser.add_argument(
    '-p',
    '--password',
    default = os.getenv('ROFI_JIRA_PASSWORD', ''),
    dest = 'password',
    help = '[env: ROFI_JIRA_PASSWORD] Specifies the password to use when connecting to JIRA.',
    metavar = 'STR'
)
argparser.add_argument(
    '-s',
    '--search',
    default = '',
    dest = 'search',
    help = 'Specifies a search string name to start with from the config file.',
    metavar = 'STR'
)
argparser.add_argument(
    '-S',
    '--server-url',
    default = os.getenv('ROFI_JIRA_SERVER_URL', 'https://127.0.0.1/jira'),
    dest = 'server_url',
    help = '[env: ROFI_JIRA_SERVER_URL] Specifies the URL of the JIRA server to connect to.',
    metavar = 'STR'
)
argparser.add_argument(
    '-u',
    '--username',
    default = os.getenv('ROFI_JIRA_USERNAME', getpass.getuser()),
    dest = 'username',
    help = '[env: ROFI_JIRA_USERNAME] Specifies the username to use when connecting to JIRA. Defaults to the current user.',
    metavar = 'STR'
)
args = argparser.parse_args()

with open(args.config, 'r') as f:
    config = yaml.safe_load(f.read())

def rofi(prompt):
    process = subprocess.Popen(
        "cat '/tmp/rofi-jira.out' | rofi -dmenu -i -no-custom -p '" + prompt + "'",
        stdout = subprocess.PIPE,
        stderr = subprocess.STDOUT,
        shell = True
    )
    output = process.communicate()[0].decode('ascii', 'ignore')
    exit_code = process.returncode
    return (output, exit_code)

search_descs = [config['searches'][s]['desc'] for s in config['searches']]

with open('/tmp/rofi-jira.out', 'w') as fo:
    for d in search_descs:
        fo.write(d + '\n')

if args.search:
    sel_search = config['searches'][args.search]['str']
else:
    (desc_out, desc_ec) = rofi('Search ... : ')
    if not desc_out:
        sys.exit(0)
    sel_search = ''
    for s in config['searches']:
        if config['searches'][s]['desc'].strip() == desc_out.strip():
            sel_search = config['searches'][s]['str']
            break
    if not sel_search:
        sys.exit(1)

j = jira.JIRA(
    server = args.server_url,
    options = {'verify': False},
    basic_auth = (args.username, args.password)
)

issues = j.search_issues(
    sel_search,
    maxResults = 2048,
    fields = ['summary', 'status'],
    json_result = True
)['issues']

with open('/tmp/rofi-jira.out', 'w') as fo:
    for i in issues:
        st_name = i['fields']['status']['name'].lower()
        if st_name == 'backlog':
            st = 'B'
        elif st_name == 'to do':
            st = '⚐'
        elif st_name == 'in progress':
            st = '⚑'
        elif st_name == 'waiting on task':
            st = '⚡'
        elif st_name == 'code review':
            st = ''
        elif st_name == 'awaiting verification':
            st = '✓'
        elif st_name == 'done':
            st = '✔'
        elif st_name == 'cancelled':
            st = '✘'
        else:
            st = '?'
        fo.write(
            '[{st}] {tid} : {desc}\n'.format(
                st = st,
                tid = i['key'],
                desc = i['fields']['summary']
            )
        )

(j_out, j_ec) = rofi('Search tickets : ')
if j_out:
    url = args.server_url + 'browse/' + j_out.split(']', 1)[1].split(':', 1)[0].strip()
    os.system("xdg-open '" + url + "'")
