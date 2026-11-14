#!/usr/bin/env python3
"""Prepared only: secure Linux-local credential storage; never contacts Apple."""
import argparse
import getpass
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile

DIRECTORY = Path('/etc/pf1007l-calendar')

def save(directory, username, password):
    if not re.fullmatch(r'[^\s:@]+@[^\s:@]+', username) or not re.fullmatch(r'[a-z]{4}(?:-[a-z]{4}){3}', password):
        raise ValueError('Expected account email and Apple app-specific password')
    directory = Path(directory)
    directory.mkdir(mode=0o700, exist_ok=True)
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
        raise ValueError('Credential directory must be owner-private')
    destination = directory/'apple.json'
    # Never overwrite an existing credential, including dangling symlinks.
    if os.path.lexists(destination): raise ValueError('Existing credential preserved')
    fd, name = tempfile.mkstemp(prefix='.credential-', dir=directory)
    try:
        with os.fdopen(fd, 'w') as stream:
            os.fchmod(stream.fileno(), 0o600)
            json.dump({'username':username,'appPassword':password}, stream)
            stream.flush();os.fsync(stream.fileno())
        os.link(name, destination, follow_symlinks=False)
    finally:
        os.unlink(name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--approved-storage', action='store_true')
    args = parser.parse_args()
    if not args.approved_storage or sys.platform!='linux' or os.geteuid()!=0 or not os.isatty(0) or not os.isatty(2):
        raise ValueError('Approved Linux native Terminal sudo session required')
    os.umask(0o077)
    username = getpass.getpass('Apple Account email (hidden): ').strip()
    password = getpass.getpass('Dedicated app-specific password (hidden, never your main password): ').strip()
    save(DIRECTORY, username, password)
    print('Private calendar credential stored locally. No account access or syncing was performed.')

if __name__=='__main__':
    try:main()
    except (Exception, KeyboardInterrupt):
        print('Calendar credential entry not completed; existing credentials preserved.', file=sys.stderr)
        sys.exit(1)
