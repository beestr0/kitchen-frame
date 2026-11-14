#!/usr/bin/env python3
"""Fixed-scope calendar activation. Run only checksum-pinned in a native root TTY.

No secret/task/event payloads in status or logs. Apple operations occur only in the
approved read-only collector; this installer never holds the Apple password.
"""
import hashlib
import http.client
import json
import os
from pathlib import Path
import pwd
import shutil
import socket
import sqlite3
import stat
import subprocess
import sys
import time
import uuid

STAGE=Path('/home/hub/pf1007l-calendar-candidate-v3-review')
MANIFEST='b392c9f1babe4028ac7dd3a6ecca60693bc79a64f801d8f8dfc1b699b830c1ef'
RUNTIME=Path('/opt/pf1007l-calendar')
ETC=Path('/etc/pf1007l-calendar')
CAL='pf1007l-calendar.service'
BRIDGE='pf1007l-reminders-bridge.service'
PROXY='pf1007l-proxy-https.service'
UI=Path('/opt/pf1007l-reminders-bridge/ui')
DATABASE=Path('/var/lib/pf1007l-reminders-bridge/tasks.sqlite')
STATUS=STAGE/'calendar-status.json'
QUEUE=STAGE/'calendar-action.json'
FILE_MAP={
 'bridge.py':Path('/opt/pf1007l-reminders-bridge/task_bridge.py'),
 'proxy.mjs':Path('/opt/pf1007l-tls/reminders-demo-proxy.mjs'),
 'calendar.service':Path('/etc/systemd/system/'+CAL),
 'calendar.conf':Path('/etc/systemd/system/'+BRIDGE+'.d/calendar.conf')}
SERVICES=['pf1007l-reminders-demo.service',BRIDGE,'pf1007l-proxy.service',PROXY,'jellyfin','tailscaled']


def run(args):
 return subprocess.run(args,capture_output=True,text=True,check=True,timeout=30,
   env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C.UTF-8'}).stdout


def atomic(path,data,mode=0o644):
 if path.is_symlink():raise RuntimeError('Unsafe destination')
 path.parent.mkdir(parents=True,exist_ok=True)
 temp=path.with_name('.'+path.name+'.'+uuid.uuid4().hex)
 try:
  with open(temp,'xb') as stream:
   os.fchmod(stream.fileno(),mode);stream.write(data);stream.flush();os.fsync(stream.fileno())
  os.replace(temp,path)
 finally:temp.unlink(missing_ok=True)


def publish(phase,**safe):
 # Dropping UID before touching a hub-controlled status destination prevents a root write primitive.
 program="import sys,os;from pathlib import Path;p=Path("+repr(str(STATUS))+");t=p.with_name('.calendar-status-'+str(os.getpid()));t.write_text(sys.stdin.read());t.chmod(0o600);t.replace(p)"
 subprocess.run(['/usr/sbin/runuser','-u','hub','--','/usr/bin/python3','-I','-c',program],
   input=json.dumps({'phase':phase,'observedUnix':time.time(),**safe}),text=True,check=True,timeout=5)


def freeze(destination):
 owner=pwd.getpwnam('hub').pw_uid
 directory=os.open(STAGE,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
 def read(name):
  # Every path component must be a real directory; never follow staged symlinks as root.
  current=os.dup(directory)
  try:
   for part in Path(name).parts[:-1]:
    fd=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=current);os.close(current);current=fd
   fd=os.open(Path(name).name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=current)
   try:
    info=os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_uid!=owner or info.st_size>10*1024*1024:raise RuntimeError('Unsafe artifact')
    with os.fdopen(fd,'rb',closefd=False) as stream:return stream.read(10*1024*1024+1)
   finally:os.close(fd)
  finally:os.close(current)
 try:
  manifest=read('manifest.json')
  if hashlib.sha256(manifest).hexdigest()!=MANIFEST:raise RuntimeError('Manifest mismatch')
  files=json.loads(manifest)['files']
  if not files:raise RuntimeError('Empty manifest')
  for name,digest in files.items():
   path=Path(name)
   if path.is_absolute() or '..' in path.parts or not set(path.parts[0:1])<={'deploy','dashboard','scripts'}:raise RuntimeError('Unsafe artifact path')
   data=read(name)
   if hashlib.sha256(data).hexdigest()!=digest:raise RuntimeError('Artifact mismatch')
   atomic(destination/name,data,0o600)
  atomic(destination/'manifest.json',manifest,0o600)
 finally:os.close(directory)


def health():
 if any(run(['systemctl','is-active',unit]).strip()!='active' for unit in SERVICES):raise RuntimeError('Existing service unhealthy')
 data=json.loads(run(['curl','--fail','--silent','--max-time','8','--resolve',
   'beestr0.duckdns.org:8789:10.157.1.115','https://beestr0.duckdns.org:8789/__proxy_health']))
 if data['upstreamErrors']:raise RuntimeError('HTTPS upstream health')
 serve=json.loads(run(['tailscale','serve','status','--json']))
 if any(serve.get('AllowFunnel',{}).values()):raise RuntimeError('Unexpected public exposure')
 if serve.get('Web',{}).get('hub-inspiron-5570.tailb76e1b.ts.net:443',{}).get('Handlers')!={'/':{'Proxy':'http://127.0.0.1:5238'}}:raise RuntimeError('Private Serve changed')


def wait_healthy():
 for attempt in range(30):
  try:health();return
  except Exception:
   if attempt==29:raise
   time.sleep(1)


def calendar_snapshot():
 # Only the dedicated local collector key; Apple credentials are never read by this helper.
 key=(ETC/'bridge-key').read_text().strip()
 conn=http.client.HTTPConnection('127.0.0.1',5241,timeout=5)
 try:
  conn.request('GET','/snapshot',headers={'X-Calendar-Key':key})
  reply=conn.getresponse();data=reply.read(2097153)
  if reply.status!=200 or len(data)>2097152:raise RuntimeError('Collector unavailable')
  value=json.loads(data)
  if value.get('source')!='private-caldav':raise RuntimeError('Wrong collector source')
  return value
 finally:conn.close()


def private_permissions():
 directory=ETC.lstat()
 if not stat.S_ISDIR(directory.st_mode) or directory.st_uid!=0 or stat.S_IMODE(directory.st_mode)!=0o700:raise RuntimeError('Private calendar directory required')
 for name in ('apple.json','config.json','bridge-key'):
  info=(ETC/name).lstat()
  if not stat.S_ISREG(info.st_mode) or info.st_uid!=0 or stat.S_IMODE(info.st_mode)!=0o600:raise RuntimeError('Private credential files required')
 config=json.loads((ETC/'config.json').read_text())
 if config.get('enabled') is not True or config.get('readOnly') is not True or config.get('allowCloudUpload') is not False or not config.get('selectedCalendars'):raise RuntimeError('Approved selected scope required')
 return len(config['selectedCalendars'])


class Activation:
 def __init__(self,work):
  self.work=work;self.backup=work/'backup';self.frozen=work/'artifacts';self.mutated=False
  self.protected={};self.proxy_changed=False;self.bridge_changed=False
 def resume(self):
  health();private_permissions()
  raw=(self.frozen/'manifest.json').read_bytes()
  if hashlib.sha256(raw).hexdigest()!=MANIFEST:raise RuntimeError('Recovery manifest mismatch')
  self.protected=json.loads((self.backup/'protected-hashes.json').read_text());self.protected_ok()
  inventory=json.loads((self.backup/'inventory.json').read_text())
  for name,path in FILE_MAP.items():
   if inventory[name]:
    if path.is_symlink() or path.read_bytes()!=(self.backup/name).read_bytes():raise RuntimeError('Working baseline changed')
   elif path.exists() or path.is_symlink():raise RuntimeError('Prior rollback incomplete')
  for original in (self.backup/'ui').rglob('*'):
   if original.is_file() and (UI/original.relative_to(self.backup/'ui')).read_bytes()!=original.read_bytes():raise RuntimeError('Baseline UI changed')
  manifest=json.loads(raw)['files']
  for relative,digest in manifest.items():
   source=self.frozen/relative
   if source.is_symlink() or hashlib.sha256(source.read_bytes()).hexdigest()!=digest:raise RuntimeError('Recovery artifact changed')
   if relative.startswith(('deploy/icloud-calendar/','dashboard/worker/','dashboard/node_modules/ical.js/')) or relative=='dashboard/package.json':
    target=RUNTIME/relative
    if target.is_symlink() or not target.is_file() or target.read_bytes()!=source.read_bytes():raise RuntimeError('Installed candidate changed')
  if not RUNTIME.is_dir() or RUNTIME.is_symlink():raise RuntimeError('Unexpected runtime')
  publish('recovery-verified',backup=str(self.backup),installedFilesVerified=True,databaseNotRewound=True)
 def preflight(self):
  health();count=private_permissions()
  if RUNTIME.exists() or FILE_MAP['calendar.service'].exists() or FILE_MAP['calendar.conf'].exists():raise RuntimeError('Existing calendar runtime preserved')
  with socket.socket() as sock:sock.bind(('127.0.0.1',5241))
  if not Path('/opt/pf1007l-proxy/node/bin/node').is_file():raise RuntimeError('Existing Node runtime required')
  self.frozen.mkdir(mode=0o700);freeze(self.frozen)
  self.backup.mkdir(mode=0o700)
  inventory={}
  for name,path in FILE_MAP.items():
   if path.is_symlink():raise RuntimeError('Unsafe backup source')
   inventory[name]=path.exists()
   if path.exists():shutil.copy2(path,self.backup/name)
  atomic(self.backup/'inventory.json',json.dumps(inventory).encode(),0o600)
  shutil.copytree(UI,self.backup/'ui')
  db=sqlite3.connect('file:'+str(DATABASE)+'?mode=ro',uri=True,timeout=10)
  target=sqlite3.connect(self.backup/'tasks.sqlite')
  try:
   db.backup(target)
   if target.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise RuntimeError('SQLite backup invalid')
  finally:target.close();db.close()
  (self.backup/'tasks.sqlite').chmod(0o600)
  # Preserve all existing auth, DAV, TLS configuration byte-for-byte.
  for path in ['/etc/pf1007l-reminders-bridge/settings.json','/etc/pf1007l-reminders-bridge/device-registry.json',
    '/etc/pf1007l-reminders-demo/demo-account.json','/etc/pf1007l-proxy-https/config.json','/opt/pf1007l-tls/proxy.mjs']:
   self.protected[path]=hashlib.sha256(Path(path).read_bytes()).hexdigest()
  atomic(self.backup/'protected-hashes.json',json.dumps(self.protected).encode(),0o600)
  publish('backup-ready',selectedCalendarCount=count,backup=str(self.backup),consistentSQLite=True)
 def protected_ok(self):
  if any(hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h for p,h in self.protected.items()):raise RuntimeError('Protected configuration changed')
 def overlay(self,source,target):
  base=RUNTIME if target==RUNTIME or RUNTIME in target.parents else UI
  def directory(path):
   if base.is_symlink():raise RuntimeError('Unsafe public source directory')
   base.chmod(0o755)
   relative=path.relative_to(base);current=base
   for part in relative.parts:
    current=current/part
    if current.is_symlink():raise RuntimeError('Unsafe public source directory')
    current.mkdir(mode=0o755,exist_ok=True)
    current.chmod(0o755)
  directory(target)
  for p in sorted(source.rglob('*'),key=lambda p:p.name=='index.html'):
   if p.is_symlink():raise RuntimeError('Unsafe source file')
   if p.is_file():
    destination=target/p.relative_to(source);directory(destination.parent)
    data=p.read_bytes()
    if destination.is_file() and not destination.is_symlink() and destination.read_bytes()==data:
     destination.chmod(0o644)
    else:atomic(destination,data)
 def deploy(self):
  self.mutated=True
  RUNTIME.mkdir(mode=0o755,exist_ok=True)
  RUNTIME.chmod(0o755)
  for relative in ['deploy/icloud-calendar','dashboard/worker','dashboard/node_modules/ical.js']:
   self.overlay(self.frozen/relative,RUNTIME/relative)
  atomic(RUNTIME/'dashboard/package.json',(self.frozen/'dashboard/package.json').read_bytes())
  atomic(FILE_MAP['calendar.service'],(self.frozen/'deploy/icloud-calendar/pf1007l-calendar.service').read_bytes())
  run(['systemd-analyze','verify',str(FILE_MAP['calendar.service'])])
  run(['systemctl','daemon-reload']);run(['systemctl','reset-failed',CAL]);run(['systemctl','start',CAL])
  publish('first-read-pending',selectedCalendarCount=private_permissions())
  deadline=time.monotonic()+240
  while True:
   try:value=calendar_snapshot()
   except (OSError,RuntimeError):
    if time.monotonic()>=deadline:raise
    time.sleep(1);continue
   if value.get('updated') and value.get('stale') is False:break
   if value.get('error') or time.monotonic()>=deadline:raise RuntimeError('Initial selected calendar fetch failed')
   time.sleep(3)
  publish('first-read-verified',selectedCalendarCount=len(value['calendars']),eventCount=len(value['events']))
  atomic(FILE_MAP['bridge.py'],(self.frozen/'deploy/reminders/task_bridge.py').read_bytes())
  atomic(FILE_MAP['calendar.conf'],(self.frozen/'deploy/icloud-calendar/bridge-calendar.conf').read_bytes())
  run(['systemd-analyze','verify','/etc/systemd/system/'+BRIDGE]);run(['systemctl','daemon-reload'])
  self.bridge_changed=True;run(['systemctl','restart',BRIDGE]);wait_healthy();self.protected_ok()
  atomic(FILE_MAP['proxy.mjs'],(self.frozen/'scripts/reminders-demo-proxy.mjs').read_bytes())
  self.proxy_changed=True;run(['systemctl','restart',PROXY]);wait_healthy();self.protected_ok()
  self.overlay(self.frozen/'dashboard/dist-reminders-demo',UI)
  run(['systemctl','enable',CAL]);self.protected_ok();health()
  publish('deployed',backup=str(self.backup),selectedCalendarCount=len(value['calendars']),eventCount=len(value['events']),
    updated=value['updated'],stale=value['stale'],servicesHealthy=True,physicalAcceptancePending=True)
 def rollback(self):
  if not self.mutated:return
  if FILE_MAP['calendar.service'].exists():
   run(['systemctl','stop',CAL]);run(['systemctl','disable',CAL])
  inventory=json.loads((self.backup/'inventory.json').read_text())
  for name,path in FILE_MAP.items():
   if inventory[name]:atomic(path,(self.backup/name).read_bytes())
   else:path.unlink(missing_ok=True)
  self.overlay(self.backup/'ui',UI)
  run(['systemctl','daemon-reload'])
  if self.bridge_changed:run(['systemctl','restart',BRIDGE])
  if self.proxy_changed:run(['systemctl','restart',PROXY])
  wait_healthy();self.protected_ok();self.mutated=False
  publish('rolled-back',backup=str(self.backup),databaseNotRewound=True,servicesHealthy=True)


def main():
 if os.geteuid()!=0 or not os.isatty(0):raise SystemExit('Checksum-pinned native root Terminal required')
 os.umask(0o077)
 parent=Path('/var/backups/pf1007l-calendar');parent.mkdir(mode=0o700,exist_ok=True)
 info=parent.lstat()
 if not stat.S_ISDIR(info.st_mode) or info.st_uid!=0 or info.st_mode&0o077:raise RuntimeError('Unsafe backup parent')
 resume=sys.argv[1:]==['--resume']
 if sys.argv[1:] and not resume:raise RuntimeError('Only --resume accepted')
 if resume:
  choices=sorted(p for p in parent.glob('activation-*') if p.is_dir() and not p.is_symlink())
  if not choices:raise RuntimeError('No prior backup')
  work=choices[-1]
 else:
  work=parent/('activation-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-'+uuid.uuid4().hex[:8]);work.mkdir(mode=0o700)
 activation=Activation(work)
 try:
  if resume:activation.resume()
  else:activation.preflight()
  activation.deploy()
 except Exception as error:
  # Detailed errors remain root-private, never task/event/account payloads on stdout.
  atomic(work/'failure.txt',(type(error).__name__+'\n').encode(),0o600)
  try:activation.rollback()
  except Exception:
   publish('rollback-needs-attention',backup=str(activation.backup));return
  publish('stopped',backup=str(activation.backup),error='Verification stopped; private diagnostics retained',servicesRestored=not activation.mutated)
  return
 print('Calendar deployed. Keep Terminal open for the short acceptance session.',flush=True)
 # Bounded status/rollback/finish only. No arbitrary command, path, key or event writes.
 seen=None;deadline=time.monotonic()+3600
 while time.monotonic()<deadline:
  try:
   fd=os.open(QUEUE,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
   with os.fdopen(fd) as stream:
    info=os.fstat(stream.fileno())
    if not stat.S_ISREG(info.st_mode) or info.st_uid!=pwd.getpwnam('hub').pw_uid or info.st_size>1024:raise ValueError()
    action=json.loads(stream.read(1025))
  except FileNotFoundError:time.sleep(1);continue
  if not isinstance(action.get('id'),str) or action['id']==seen:time.sleep(1);continue
  seen=action['id']
  if action.get('action')=='finish':publish('finished',servicesHealthy=True);return
  if action.get('action')=='rollback':activation.rollback();return
  if action.get('action')=='status':
   health();value=calendar_snapshot()
   publish('status',id=seen,eventCount=len(value.get('events',[])),selectedCalendarCount=len(value.get('calendars',[])),updated=value.get('updated'),stale=value.get('stale'),servicesHealthy=True)


if __name__=='__main__':main()
