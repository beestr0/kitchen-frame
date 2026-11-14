#!/usr/bin/env python3
"""Native retry of explicitly mistyped entry; preserves runtime/selected calendars."""
import hashlib
import os
from pathlib import Path
import shlex
import subprocess

REMOTE='/home/hub/pf1007l-calendar-authorization-retry-review'


def command():
    source=Path(__file__).resolve().parent
    names=('authorize.py','prepare_credentials.py','readonly_caldav.py')
    hashes={name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in names}
    identity=hashlib.sha256(''.join(hashes.values()).encode()).hexdigest()[:12]
    root='/root/pf1007l-calendar-retry-'+identity
    commands=['sudo -p '+shlex.quote('PF1007L private Calendar retry sudo password (hidden): ')+' -v',
              shlex.join(['sudo','-n','install','-d','-o','root','-g','root','-m','700',root])]
    for name in names:commands.append(shlex.join(['sudo','-n','install','-o','root','-g','root','-m','700',REMOTE+'/'+name,root+'/'+name]))
    lines=''.join(digest+'  '+root+'/'+name+'\n' for name,digest in hashes.items())
    commands.append('printf %s '+shlex.quote(lines)+' | sudo -n sha256sum -c -')
    program='import sys,runpy;sys.path.insert(0,'+repr(root)+');runpy.run_path('+repr(root+'/authorize.py')+',run_name="__main__")'
    commands.append(shlex.join(['sudo','-n','/usr/bin/python3','-I','-c',program,'--approved-storage','--approved-discovery','--replace-mistyped-credential']))
    return ['ssh','-t','pf1007l-mint',' && '.join(commands)]


if __name__=='__main__':
    if not os.isatty(0):raise SystemExit('Use a private native Terminal for the explicitly requested entry correction')
    raise SystemExit(subprocess.call(command()))
