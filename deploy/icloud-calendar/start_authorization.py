#!/usr/bin/env python3
"""Native Mac launcher for pinned private credential/discovery setup, after approval.

No secrets in arguments; no event fetch, service install or restart by this launcher.
"""
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess

ROOT=Path(__file__).resolve().parents[2]
BUNDLE=ROOT/'diagnostics/pf1007l/calendar-candidate-v3'
MANIFEST='b392c9f1babe4028ac7dd3a6ecca60693bc79a64f801d8f8dfc1b699b830c1ef'
REMOTE='/home/hub/pf1007l-calendar-candidate-v3-review'


def command():
    raw=(BUNDLE/'manifest.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=MANIFEST:raise ValueError('Reviewed candidate manifest mismatch')
    manifest=json.loads(raw)
    root='/root/pf1007l-calendar-authorization-'+MANIFEST[:12]
    commands=['sudo -p '+shlex.quote('PF1007L private Calendar setup sudo password (hidden): ')+' -v',
              shlex.join(['sudo','-n','install','-d','-o','root','-g','root','-m','700',root])]
    lines=[]
    for name in ('authorize.py','prepare_credentials.py','readonly_caldav.py'):
        path='deploy/icloud-calendar/'+name
        data=(BUNDLE/path).read_bytes();digest=hashlib.sha256(data).hexdigest()
        if digest!=manifest['files'][path]:raise ValueError('Reviewed setup file mismatch')
        commands.append(shlex.join(['sudo','-n','install','-o','root','-g','root','-m','700',REMOTE+'/'+path,root+'/'+name]))
        lines.append(digest+'  '+root+'/'+name+'\n')
    commands.append('printf %s '+shlex.quote(''.join(lines))+' | sudo -n sha256sum -c -')
    program='import sys,runpy;sys.path.insert(0,'+repr(root)+');runpy.run_path('+repr(root+'/authorize.py')+',run_name="__main__")'
    commands.append(shlex.join(['sudo','-n','/usr/bin/python3','-I','-c',program,'--approved-storage','--approved-discovery']))
    return ['ssh','-t','pf1007l-mint',' && '.join(commands)]


def main():
    if not os.isatty(0):raise SystemExit('Use a private native Terminal after owner account-scope approval')
    print('Approved private setup only. Enter credentials in this Terminal, never in chat.',flush=True)
    raise SystemExit(subprocess.call(command()))


if __name__=='__main__':main()
