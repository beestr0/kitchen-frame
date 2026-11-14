#!/usr/bin/env python3
"""Owner-approved native setup: hidden storage, metadata-only discovery, selection.

Never fetches events or starts a service. Run only after account-scope approval.
"""
import argparse
import getpass
import json
import os
from pathlib import Path
import secrets
import stat
import sys
import tempfile
from prepare_credentials import save,DIRECTORY
from readonly_caldav import ReadonlyCalDAV


def write_new(path,value):
    if os.path.lexists(path):raise ValueError('Existing calendar configuration preserved')
    fd,name=tempfile.mkstemp(prefix='.calendar-',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as stream:
            os.fchmod(stream.fileno(),0o600);stream.write(value);stream.flush();os.fsync(stream.fileno())
        os.link(name,path,follow_symlinks=False)
    finally:os.unlink(name)


def choose(calendars,answer):
    numbers=[int(x.strip())-1 for x in answer.split(',')]
    if not numbers or len(set(numbers))!=len(numbers) or any(n<0 or n>=len(calendars) for n in numbers):
        raise ValueError('Choose distinct listed calendars')
    return [{'id':'calendar-'+str(i+1),'href':calendars[n]['href'],
             'name':calendars[n]['name'],'color':calendars[n].get('color') or '#3478F6'} for i,n in enumerate(numbers)]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--approved-storage',action='store_true')
    parser.add_argument('--approved-discovery',action='store_true')
    args=parser.parse_args()
    if not (args.approved_storage and args.approved_discovery and sys.platform=='linux' and os.geteuid()==0 and os.isatty(0) and os.isatty(2)):
        raise ValueError('Explicit approval and private Linux root Terminal required')
    os.umask(0o077)
    if (DIRECTORY/'config.json').exists() or (DIRECTORY/'bridge-key').exists():
        raise ValueError('Existing calendar setup preserved; review before any change')
    path=DIRECTORY/'apple.json'
    if not path.exists():
        username=getpass.getpass('Apple reader account email (hidden): ').strip()
        password=getpass.getpass('PF1007L Calendar app-specific password (hidden): ').strip()
        save(DIRECTORY,username,password)
    info=path.lstat();directory=DIRECTORY.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid!=0 or stat.S_IMODE(info.st_mode)!=0o600 or not stat.S_ISDIR(directory.st_mode) or stat.S_IMODE(directory.st_mode)!=0o700:
        raise ValueError('Private credential permissions required')
    account=json.loads(path.read_text())
    calendars=ReadonlyCalDAV(account['username'],account['appPassword']).discover()
    print('Private calendar metadata below is for this Terminal only. No events fetched.')
    for i,c in enumerate(calendars):print(str(i+1)+'. '+''.join(ch if ch.isprintable() else ' ' for ch in c['name'])+'  '+(c.get('color') or 'default color'))
    selection=choose(calendars,input('Select calendar numbers separated by commas: '))
    print('Selected '+str(len(selection))+' calendars. The collector forbids all Apple writes.')
    if input('Type SELECT to save this scope (does not fetch events or start syncing): ')!='SELECT':
        raise ValueError('Selection not saved')
    config={'enabled':True,'readOnly':True,'allowCloudUpload':False,'syncMinutes':5,
            'timezone':'America/Indiana/Indianapolis','selectedCalendars':selection}
    write_new(DIRECTORY/'config.json',json.dumps(config))
    write_new(DIRECTORY/'bridge-key',secrets.token_hex(32))
    print('Selected scope saved privately. No events fetched; service remains stopped. First fetch/deployment requires approval.')


if __name__=='__main__':
    try:main()
    except (Exception,KeyboardInterrupt):
        print('Calendar setup stopped; no service started. Existing credentials/configuration preserved.',file=sys.stderr)
        sys.exit(1)
