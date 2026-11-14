#!/usr/bin/env python3
"""Reveal only the dedicated disposable DAV credential in a private native TTY."""
import json
import os
from pathlib import Path
import sys

if sys.platform != 'linux' or os.geteuid() != 0 or not os.isatty(0) or not os.isatty(1):
    raise SystemExit('Use a private native SSH sudo Terminal without redirection or recording.')
account = json.loads(Path('/etc/pf1007l-reminders-demo/demo-account.json').read_text())
if account.get('username') != 'pf1007l-demo':
    raise SystemExit('Unexpected account; no credential displayed.')
print('Dedicated disposable Radicale account, not an Apple Account.')
print('Do not paste this password into chat, screenshots or logs.')
print('Username:', account['username'])
print('Password:', account['password'])
print('Enter it only into the approved native Reminders CalDAV account setup.')
