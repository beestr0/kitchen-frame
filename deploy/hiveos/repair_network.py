#!/usr/bin/env python3
"""Fixed USB-verified frame-IP repair; only project guards and two project units."""
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import subprocess
import sys
import time
import uuid

OLD='10.157.1.76'
NEW='10.157.1.146'
PROXY=Path('/etc/pf1007l-proxy-https/config.json')
FIREWALL=Path('/etc/pf1007l-proxy-https/firewall.nft')
SETTINGS=Path('/etc/pf1007l-reminders-bridge/settings.json')
STAGE=Path('/home/hub/pf1007l-hiveos-review')
UNITS=['pf1007l-reminders-bridge.service','pf1007l-proxy-https.service']


def run(args,data=None):
 return subprocess.run(args,input=data,capture_output=True,text=True,check=True,timeout=20).stdout


def replacements(proxy,settings,firewall):
 if proxy.get('allowedClients')!=[OLD] or settings.get('frameIP')!=OLD or settings.get('authMode')!='device-v1':
  raise RuntimeError('Unexpected baseline; no automatic change')
 updated,count=re.subn(r'(?<![0-9.])'+re.escape(OLD)+r'(?![0-9.])',NEW,firewall)
 if count<1 or 'table inet pf1007l_proxy_tls' not in firewall:raise RuntimeError('Unexpected firewall')
 return {**proxy,'allowedClients':[NEW]},{**settings,'frameIP':NEW},updated


def atomic(path,data,mode):
 if path.is_symlink():raise RuntimeError('Unsafe destination')
 temporary=path.with_name('.'+path.name+'.'+uuid.uuid4().hex)
 try:
  with open(temporary,'xb') as stream:
   os.fchmod(stream.fileno(),mode);stream.write(data);stream.flush();os.fsync(stream.fileno())
  os.replace(temporary,path)
 finally:temporary.unlink(missing_ok=True)


def transaction(text):
 if not re.search(r'\b(?:delete|destroy)\s+table\s+inet\s+pf1007l_proxy_tls\b',text):
  return 'delete table inet pf1007l_proxy_tls\n'+text
 return text


def publish(phase,**fields):
 program="import sys,os;from pathlib import Path;p=Path('/home/hub/pf1007l-hiveos-review/status.json');t=p.with_name('.status-'+str(os.getpid()));t.write_text(sys.stdin.read());t.chmod(0o600);t.replace(p)"
 subprocess.run(['/usr/sbin/runuser','-u','hub','--','/usr/bin/python3','-I','-c',program],input=json.dumps({'phase':phase,'updatedUnix':time.time(),**fields}),text=True,check=True,timeout=5)


def health():
 for attempt in range(30):
  try:
   if any(run(['systemctl','is-active',u]).strip()!='active' for u in UNITS+['pf1007l-calendar.service','pf1007l-reminders-demo.service','jellyfin','tailscaled']):raise RuntimeError()
   run(['curl','--fail','--silent','--max-time','5','--resolve','beestr0.duckdns.org:8789:10.157.1.115','https://beestr0.duckdns.org:8789/__proxy_health'])
   return
  except Exception:
   if attempt==29:raise
   time.sleep(1)


def main():
 if os.geteuid()!=0 or not os.isatty(0):raise SystemExit('Private native sudo Terminal required')
 os.umask(0o077);health()
 originals={p:p.read_bytes() for p in (PROXY,SETTINGS,FIREWALL)}
 proxy,settings,firewall=replacements(json.loads(originals[PROXY]),json.loads(originals[SETTINGS]),originals[FIREWALL].decode())
 tx=transaction(firewall);run(['nft','--check','--file','-'],tx)
 parent=Path('/var/backups/pf1007l-network');parent.mkdir(mode=0o700,exist_ok=True)
 if parent.is_symlink() or parent.stat().st_mode&0o077:raise RuntimeError('Private backup directory required')
 backup=parent/('repair-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-'+uuid.uuid4().hex[:8]);backup.mkdir(mode=0o700)
 for path,data in originals.items():atomic(backup/(path.parent.name+'-'+path.name),data,0o600)
 rules=run(['nft','list','table','inet','pf1007l_proxy_tls']);atomic(backup/'live-firewall.nft',rules.encode(),0o600)
 # Read-only consistent task-state safety snapshot; never restored over new operation history.
 source=sqlite3.connect('file:/var/lib/pf1007l-reminders-bridge/tasks.sqlite?mode=ro',uri=True,timeout=10)
 target=sqlite3.connect(backup/'tasks.sqlite')
 try:
  source.backup(target)
  if target.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise RuntimeError('Invalid safety snapshot')
 finally:source.close();target.close()
 (backup/'tasks.sqlite').chmod(0o600)
 mutated=False
 try:
  mutated=True
  atomic(PROXY,json.dumps(proxy).encode(),stat.S_IMODE(PROXY.stat().st_mode))
  atomic(SETTINGS,json.dumps(settings).encode(),0o600)
  atomic(FIREWALL,firewall.encode(),stat.S_IMODE(FIREWALL.stat().st_mode))
  run(['nft','--file','-'],tx)
  for unit in UNITS:run(['systemctl','restart',unit])
  health()
  # Only the address changed; existing keys, enrollment, cookies/settings remain byte-equivalent values.
  after=json.loads(SETTINGS.read_text());before=json.loads(originals[SETTINGS])
  after.pop('frameIP');before.pop('frameIP')
  if after!=before:raise RuntimeError('Protected settings changed')
  publish('repaired',oldAddress=OLD,newAddress=NEW,backup=str(backup),existingAuthPreserved=True)
 except Exception:
  if mutated:
   for path,data in originals.items():atomic(path,data,0o600 if path==SETTINGS else 0o644)
   run(['nft','--file','-'],transaction(rules))
   for unit in UNITS:run(['systemctl','restart',unit])
   health()
  publish('stopped',backup=str(backup),workingBaselineRestored=True)
  return
 print('Exact frame IP repaired. Existing keys and private data preserved.',flush=True)


if __name__=='__main__':main()
