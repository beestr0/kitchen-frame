#!/usr/bin/env python3
"""Launch only the checksum-pinned, fixed-scope demo session in native Terminal."""
import hashlib
import os
from pathlib import Path
import shlex
import subprocess
import sys

BOOTSTRAP = r'''
import hashlib,os,pwd,stat,sys
from pathlib import Path
expected=sys.argv[1]
source='/home/hub/pf1007l-device-auth-review.yt5Otk/activation_session.py'
fd=os.open(source,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
try:
    info=os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_uid!=pwd.getpwnam('hub').pw_uid or info.st_size>131072:raise SystemExit('Unsafe staged controller')
    with os.fdopen(fd,'rb',closefd=False) as stream:data=stream.read(131073)
finally:os.close(fd)
if hashlib.sha256(data).hexdigest()!=expected:raise SystemExit('Controller checksum mismatch; nothing executed')
target=Path('/root/pf1007l-device-activation-'+expected[:12]+'.py')
if target.exists():
    info=target.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid!=0 or info.st_mode & 0o077 or target.read_bytes()!=data:raise SystemExit('Unexpected existing root controller')
else:
    output=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o700)
    with os.fdopen(output,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
print('Verified fixed-scope controller. Frozen artifacts and private backup will be checked before deployment.',flush=True)
program='/opt/pf1007l-reminders-demo/venv/bin/python'
os.execv(program,[program,'-I',str(target)]+sys.argv[2:])
'''


def command(mode=None):
    source=Path(__file__).with_name('activation_session.py')
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    remote=['sudo','-p','PF1007L device-auth activation sudo password (hidden): ',
            '/usr/bin/python3','-I','-c',BOOTSTRAP,digest]
    if mode:remote.append(mode)
    return ['ssh','-t','pf1007l-mint',shlex.join(remote)]


def main():
    if sys.argv[1:] not in ([],['--resume'],['--recover']):raise SystemExit('Only --resume or --recover is accepted')
    if not os.isatty(0):raise SystemExit('Run this launcher in a NEW native macOS Terminal, not a background cell')
    print('Use your Linux sudo password privately. Leave this scoped Terminal open during acceptance.',flush=True)
    raise SystemExit(subprocess.call(command(sys.argv[1] if sys.argv[1:] else None)))


if __name__=='__main__':main()
