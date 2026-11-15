#!/usr/bin/env python3
"""Checksum-pinned native authorization for the approved exact-address repair."""
import hashlib
import os
from pathlib import Path
import shlex
import subprocess

BOOTSTRAP='''import os,pwd,stat,sys,hashlib
from pathlib import Path
source='/home/hub/pf1007l-hiveos-review/repair_network.py';expected=sys.argv[1]
fd=os.open(source,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
try:
 info=os.fstat(fd)
 if not stat.S_ISREG(info.st_mode) or info.st_uid!=pwd.getpwnam('hub').pw_uid or info.st_size>65536:raise SystemExit('Unsafe repair helper')
 with os.fdopen(fd,'rb',closefd=False) as stream:data=stream.read(65537)
finally:os.close(fd)
if hashlib.sha256(data).hexdigest()!=expected:raise SystemExit('Repair checksum mismatch')
target=Path('/root/pf1007l-network-repair-'+expected[:12]+'.py')
if target.exists():
 info=target.lstat()
 if not stat.S_ISREG(info.st_mode) or info.st_uid!=0 or info.st_mode&0o077 or target.read_bytes()!=data:raise SystemExit('Unexpected root helper')
else:
 fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o700)
 with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
os.execv('/usr/bin/python3',['/usr/bin/python3','-I',str(target)])
'''


def main():
 if not os.isatty(0):raise SystemExit('Run only in a private native Terminal')
 digest=hashlib.sha256(Path(__file__).with_name('repair_network.py').read_bytes()).hexdigest()
 remote=['sudo','-p','PF1007L exact-IP repair sudo password (hidden): ','/usr/bin/python3','-I','-c',BOOTSTRAP,digest]
 raise SystemExit(subprocess.call(['ssh','-t','pf1007l-mint',shlex.join(remote)]))


if __name__=='__main__':main()
