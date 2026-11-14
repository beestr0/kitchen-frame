#!/usr/bin/env python3
"""Native launcher pins the fixed read-only Calendar deployment controller."""
import hashlib
import os
from pathlib import Path
import shlex
import subprocess
import sys

REMOTE='/home/hub/pf1007l-calendar-candidate-v3-review/activation.py'
BOOTSTRAP='''import hashlib,os,pwd,stat,sys
from pathlib import Path
source=sys.argv[1];expected=sys.argv[2]
fd=os.open(source,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
try:
 info=os.fstat(fd)
 if not stat.S_ISREG(info.st_mode) or info.st_uid!=pwd.getpwnam('hub').pw_uid or info.st_size>131072:raise SystemExit('Unsafe controller')
 with os.fdopen(fd,'rb',closefd=False) as stream:data=stream.read(131073)
finally:os.close(fd)
if hashlib.sha256(data).hexdigest()!=expected:raise SystemExit('Controller mismatch')
target=Path('/root/pf1007l-calendar-activation-'+expected[:12]+'.py')
if target.exists():
 info=target.lstat()
 if not stat.S_ISREG(info.st_mode) or info.st_uid!=0 or info.st_mode&0o077 or target.read_bytes()!=data:raise SystemExit('Unsafe root controller')
else:
 fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o700)
 with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
os.execv('/usr/bin/python3',['/usr/bin/python3','-I',str(target)]+sys.argv[3:])
'''


def command(resume=False):
 digest=hashlib.sha256(Path(__file__).with_name('activation.py').read_bytes()).hexdigest()
 remote=['sudo','-p','PF1007L read-only Calendar deployment sudo password (hidden): ',
         '/usr/bin/python3','-I','-c',BOOTSTRAP,REMOTE,digest]
 if resume:remote.append('--resume')
 return ['ssh','-t','pf1007l-mint',shlex.join(remote)]


def main():
 if not os.isatty(0):raise SystemExit('Use a private native Terminal for this approved scoped deployment')
 if sys.argv[1:] not in ([],['--resume']):raise SystemExit('Only --resume is accepted')
 print('Deploying selected read-only calendars only; no Apple writes or unrelated restarts.',flush=True)
 raise SystemExit(subprocess.call(command(sys.argv[1:]==['--resume'])))


if __name__=='__main__':main()
