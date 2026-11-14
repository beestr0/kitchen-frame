#!/usr/bin/env python3
"""Approved demo-only native-TTY session. Fixed actions; frozen, pinned artifacts.

Never run from a user-writable source as root without the launcher checksum check.
No arbitrary commands, paths, credentials or task mutations accepted from the queue.
"""
import base64
import fcntl
import hashlib
import http.client
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import sqlite3
import stat
import subprocess
import sys
import tarfile
import time
import traceback
import uuid

STAGE = Path('/home/hub/pf1007l-device-auth-review.yt5Otk')
MANIFEST = 'e1d119d6e96a548612e16751ee940a11e1951903873d6bca5b6956f788544f53'
BRIDGE = 'pf1007l-reminders-bridge.service'
PROXY = 'pf1007l-proxy-https.service'
SERVICES = ['pf1007l-reminders-demo.service', BRIDGE, 'pf1007l-proxy.service', PROXY, 'jellyfin', 'tailscaled']
FILE_MAP = {
 'task_bridge.py':'/opt/pf1007l-reminders-bridge/task_bridge.py',
 'device_auth.py':'/opt/pf1007l-reminders-bridge/device_auth.py',
 'device_registry.py':'/opt/pf1007l-reminders-bridge/device_registry.py',
 'pf1007l-reminders-bridge.service':'/etc/systemd/system/'+BRIDGE,
 'reminders-demo-proxy.mjs':'/opt/pf1007l-tls/reminders-demo-proxy.mjs',
 'settings.json':'/etc/pf1007l-reminders-bridge/settings.json',
 'device-registry.json':'/etc/pf1007l-reminders-bridge/device-registry.json',
 'device-auth.conf':'/etc/systemd/system/'+BRIDGE+'.d/device-auth.conf',
}
UI = '/opt/pf1007l-reminders-bridge/ui'
DATABASE = '/var/lib/pf1007l-reminders-bridge/tasks.sqlite'
ACCOUNT = '/etc/pf1007l-reminders-demo/demo-account.json'


def run(args):
    return subprocess.run(args,check=True,capture_output=True,text=True,timeout=30,
        env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C.UTF-8'}).stdout


def atomic(path, data, mode=0o600):
    if path.is_symlink(): raise RuntimeError('Refusing symlink destination')
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary = path.with_name('.'+path.name+'.'+uuid.uuid4().hex)
    try:
        with open(temporary,'xb') as stream:
            os.fchmod(stream.fileno(),mode); stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally: temporary.unlink(missing_ok=True)


def retain_failure(directory,name):
    path=directory/name
    if path.exists():shutil.copy2(path,directory/(path.stem+'-'+uuid.uuid4().hex+'.txt'))
    atomic(path,traceback.format_exc().encode())


def freeze(destination):
    owner = pwd.getpwnam('hub').pw_uid
    descriptor = os.open(STAGE,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    def read(name):
        fd = os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=descriptor)
        try:
            info=os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid!=owner or info.st_size>10*1024*1024:
                raise RuntimeError('Unsafe staged artifact')
            with os.fdopen(fd,'rb',closefd=False) as stream:return stream.read(10*1024*1024+1)
        finally:os.close(fd)
    try:
        manifest=read('manifest.json')
        if hashlib.sha256(manifest).hexdigest()!=MANIFEST:raise RuntimeError('Frozen manifest mismatch')
        entries=json.loads(manifest)['files']
        if not entries or any(not re.fullmatch(r'[A-Za-z0-9_.-]+',name) for name in entries):raise RuntimeError('Unsafe manifest path')
        destination.mkdir(mode=0o700)
        atomic(destination/'manifest.json',manifest)
        for name,digest in entries.items():
            data=read(name)
            if hashlib.sha256(data).hexdigest()!=digest:raise RuntimeError('Artifact checksum mismatch')
            atomic(destination/name,data)
    finally:os.close(descriptor)


class Activation:
    def __init__(self, frozen, backup, root=Path('/'), runner=run):
        self.frozen,self.backup,self.root,self.run=frozen,backup,root,runner
        self.mutated=False; self.proxy_touched=False; self.outage_until=None
        self.enrolled=None; self.compatible=False

    def p(self,path):return self.root/path.lstrip('/')
    def settings(self):return json.loads(self.p(FILE_MAP['settings.json']).read_text())

    def snapshot(self):
        settings=self.settings()
        connection=http.client.HTTPConnection('127.0.0.1',5240,timeout=12)
        try:
            connection.request('GET','/__reminders-demo/snapshot',headers={'X-Pilot-Key':settings['apiKey'],
                'X-Pilot-Client':settings['frameIP'],'Cookie':'pf1007l-demo='+settings['session']})
            response=connection.getresponse(); value=json.loads(response.read(2097152))
            if response.status!=200 or value.get('stale') or not isinstance(value.get('items'),list):raise RuntimeError('Demo snapshot gate failed')
            return value
        finally:connection.close()

    def health(self):
        if any(self.run(['systemctl','is-active',unit]).strip()!='active' for unit in SERVICES):raise RuntimeError('Service gate failed')
        data=json.loads(self.run(['curl','--fail','--silent','--max-time','8','--resolve',
            'beestr0.duckdns.org:8789:10.157.1.115','https://beestr0.duckdns.org:8789/__proxy_health']))
        if data['upstreamErrors']!=0:raise RuntimeError('HTTPS health gate failed')
        self.run(['curl','--fail','--silent','--max-time','5','http://127.0.0.1:8096/health'])
        serve=json.loads(self.run(['tailscale','serve','status','--json']))
        if serve.get('AllowFunnel') and any(serve['AllowFunnel'].values()):raise RuntimeError('Unexpected Funnel state')
        expected={'/':{'Proxy':'http://127.0.0.1:5238'}}
        if serve.get('Web',{}).get('hub-inspiron-5570.tailb76e1b.ts.net:443',{}).get('Handlers')!=expected:raise RuntimeError('Private Serve changed')

    def wait_healthy(self,timeout=30):
        # systemctl restart returns before Node necessarily binds its HTTPS socket.
        # Retry observation only; never restart again or weaken verification here.
        deadline=time.monotonic()+timeout
        while True:
            try:self.health();return
            except (subprocess.CalledProcessError,RuntimeError):
                if time.monotonic()>=deadline:raise
                time.sleep(1)

    def verify_restored(self):
        inventory=json.loads((self.backup/'inventory.json').read_text())
        for name,path in FILE_MAP.items():
            target=self.p(path)
            if inventory[name]:
                original=self.backup/name
                if target.is_symlink() or target.read_bytes()!=original.read_bytes() or stat.S_IMODE(target.stat().st_mode)!=stat.S_IMODE(original.stat().st_mode):
                    raise RuntimeError('Restored file gate failed')
            elif target.exists() or target.is_symlink():raise RuntimeError('Introduced file remains active')
        for original in (self.backup/'ui').rglob('*'):
            if original.is_file():
                target=self.p(UI)/original.relative_to(self.backup/'ui')
                if target.is_symlink() or target.read_bytes()!=original.read_bytes():raise RuntimeError('Restored UI gate failed')
        self.protected_ok();self.wait_healthy()
        return {'baselineFilesAndUIVerified':True,'protectedConfigurationUnchanged':True,'servicesHealthy':True,'databaseNotRewound':True}

    def make_backup(self):
        self.health()
        if self.settings().get('authMode','legacy-demo')!='legacy-demo':raise RuntimeError('Expected legacy baseline')
        self.baseline=self.snapshot()
        self.backup.mkdir(mode=0o700)
        inventory={}
        for name,path in FILE_MAP.items():
            source=self.p(path)
            if source.is_symlink():raise RuntimeError('Unexpected baseline symlink')
            inventory[name]=source.exists()
            if source.exists():shutil.copy2(source,self.backup/name)
        if inventory['device-auth.conf'] or inventory['device-registry.json']:raise RuntimeError('Unexpected prior enrollment; preserve it')
        shutil.copytree(self.p(UI),self.backup/'ui',symlinks=False)
        atomic(self.backup/'inventory.json',json.dumps(inventory).encode())
        atomic(self.backup/'baseline-snapshot.json',json.dumps(self.baseline).encode())
        source=sqlite3.connect('file:'+str(self.p(DATABASE))+'?mode=ro',uri=True,timeout=10)
        target=sqlite3.connect(self.backup/'tasks.sqlite')
        try:
            source.backup(target)
            if target.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise RuntimeError('SQLite backup gate failed')
        finally:target.close();source.close()
        (self.backup/'tasks.sqlite').chmod(0o600)
        # These must remain byte-identical throughout activation/rollback.
        self.protected={path:hashlib.sha256(self.p(path).read_bytes()).hexdigest() for path in
            [ACCOUNT,'/opt/pf1007l-tls/proxy.mjs','/etc/pf1007l-proxy-https/config.json','/etc/pf1007l-reminders-bridge/proxy-key']}
        atomic(self.backup/'protected-hashes.json',json.dumps(self.protected).encode())
        return {'backupCreated':True,'consistentSQLite':True,'backupPath':str(self.backup),'baselineItems':len(self.baseline['items'])}

    def protected_ok(self):
        if any(hashlib.sha256(self.p(path).read_bytes()).hexdigest()!=digest for path,digest in self.protected.items()):
            raise RuntimeError('Protected configuration changed')

    def install_ui(self, source):
        files=sorted(source.rglob('*'),key=lambda p:p.name=='index.html')
        for item in files:
            if item.is_symlink():raise RuntimeError('UI symlink denied')
            target=self.p(UI)/item.relative_to(source)
            if item.is_dir():target.mkdir(mode=0o755,parents=True,exist_ok=True)
            else:atomic(target,item.read_bytes(),0o644)

    def compat(self,proxy_approved):
        if proxy_approved is not True:raise RuntimeError('Dedicated HTTPS restart approval required')
        self.mutated=True
        for name in ('device_auth.py','device_registry.py','task_bridge.py','pf1007l-reminders-bridge.service','reminders-demo-proxy.mjs'):
            atomic(self.p(FILE_MAP[name]),(self.frozen/name).read_bytes(),0o644)
        extracted=self.frozen/'ui';extracted.mkdir(mode=0o700,exist_ok=True)
        with tarfile.open(self.frozen/'reminders-ui.tar.gz') as archive:
            for member in archive.getmembers():
                if member.issym() or member.islnk() or not member.isfile() or member.name.startswith('/') or '..' in Path(member.name).parts:
                    raise RuntimeError('Unsafe UI archive')
            archive.extractall(extracted,filter='data')
        self.install_ui(extracted)
        self.run(['systemd-analyze','verify',str(self.p(FILE_MAP['pf1007l-reminders-bridge.service']))])
        self.run(['systemctl','daemon-reload']);self.run(['systemctl','restart',BRIDGE])
        for attempt in range(20):
            try:current=self.snapshot();break
            except Exception:
                if attempt==19:raise
                time.sleep(1)
        def task_state(value):return sorted((item['id'],item['title'],item['due'],item['completed']) for item in value['items'])
        if task_state(current)!=task_state(self.baseline):raise RuntimeError('Compatibility task-state gate failed')
        self.proxy_touched=True;self.run(['systemctl','restart',PROXY])
        self.wait_healthy();self.protected_ok();self.compatible=True
        return {'compatibleBackend':True,'legacyAuthPreserved':True,'taskStatePreserved':True,'servicesHealthy':True}

    def enroll(self,value):
        if not self.compatible or self.enrolled:raise RuntimeError('Enrollment phase gate failed')
        from device_registry import change,save
        key=value.get('publicKey');identifier=value.get('fingerprint')
        if not isinstance(key,str) or len(key)>160 or not isinstance(identifier,str) or not re.fullmatch('[a-f0-9]{64}',identifier):raise RuntimeError('Invalid public enrollment')
        registry=change({'version':1,'devices':[]},'enroll',identifier,key)
        save(self.p(FILE_MAP['device-registry.json']),registry)
        self.enrolled=identifier
        atomic(self.backup/'enrolled-public.json',json.dumps(registry).encode())
        return {'publicKeyRegistered':True,'fingerprint':identifier,'authModeUnchanged':True}

    def activate(self):
        if not self.enrolled or self.settings().get('authMode','legacy-demo')!='legacy-demo':raise RuntimeError('Activation phase gate failed')
        settings=self.settings();settings['authMode']='device-v1'
        dropin=self.p(FILE_MAP['device-auth.conf']);dropin.parent.mkdir(mode=0o755,exist_ok=True)
        atomic(dropin,(self.frozen/'device-auth.conf').read_bytes(),0o644)
        atomic(self.p(FILE_MAP['settings.json']),json.dumps(settings).encode())
        self.run(['systemd-analyze','verify',str(self.p(FILE_MAP['pf1007l-reminders-bridge.service']))])
        self.run(['systemctl','daemon-reload']);self.run(['systemctl','restart',BRIDGE])
        self.wait_healthy();self.protected_ok()
        return {'deviceModeEnabled':True,'physicalEnableRequired':True}

    def registry_action(self,action):
        if not self.enrolled or self.settings().get('authMode')!='device-v1':raise RuntimeError('Device-mode gate failed')
        from device_registry import change,save
        path=self.p(FILE_MAP['device-registry.json'])
        save(path,change(json.loads(path.read_text()),action,self.enrolled))
        self.run(['systemctl','restart',BRIDGE]);self.wait_healthy();self.protected_ok()
        return {'registryAction':action,'bridgeReloaded':True}

    def status(self):
        db=sqlite3.connect('file:'+str(self.p(DATABASE))+'?mode=ro',uri=True,timeout=5)
        try:
            tables={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            try:bridge_state=self.run(['systemctl','is-active',BRIDGE]).strip()
            except subprocess.CalledProcessError as error:bridge_state=(error.stdout or '').strip()
            result={'mode':self.settings().get('authMode','legacy-demo'),'bridge':bridge_state}
            if 'device_sessions' in tables:
                count,latest,expiry=db.execute('SELECT COUNT(*),MAX(issued),MAX(expires) FROM device_sessions').fetchone()
                result.update(sessionCount=count,latestIssuedUnix=latest,latestExpiryUnix=expiry,
                    activeDevices=db.execute('SELECT COUNT(*) FROM device_keys WHERE active=1').fetchone()[0])
            return result
        finally:db.close()

    def rollback(self):
        if not self.mutated:return {'rollbackNeeded':False}
        self.run(['systemctl','stop',BRIDGE]);self.outage_until=None
        inventory=json.loads((self.backup/'inventory.json').read_text())
        for name,path in FILE_MAP.items():
            target=self.p(path)
            if inventory[name]:atomic(target,(self.backup/name).read_bytes(),0o600 if name in ('settings.json','device-registry.json') else 0o644)
            else:target.unlink(missing_ok=True)
        self.install_ui(self.backup/'ui')
        self.run(['systemctl','daemon-reload']);self.run(['systemctl','start',BRIDGE])
        if self.proxy_touched:self.run(['systemctl','restart',PROXY])
        self.wait_healthy();self.protected_ok();self.mutated=False
        return {'rollbackRestoredCurrentDemo':True,'databaseAndRadicaleNotRewound':True,'backupPath':str(self.backup)}


def publish(value):
    # Write as hub: a user-controlled status path must never be a root write primitive.
    value={'updatedUnix':time.time(),**value}
    program="import sys,json,os;from pathlib import Path;p=Path('/home/hub/pf1007l-device-auth-review.yt5Otk/device-auth-status.json');t=p.with_name('.device-status-'+str(os.getpid()));t.write_text(sys.stdin.read());t.chmod(0o600);t.replace(p)"
    subprocess.run(['/usr/sbin/runuser','-u','hub','--','/usr/bin/python3','-I','-c',program],
        input=json.dumps(value),text=True,check=True,timeout=5)


def read_action():
    directory=os.open(STAGE,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        try:fd=os.open('device-auth-action.json',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=directory)
        except FileNotFoundError:return None
        try:
            info=os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid!=pwd.getpwnam('hub').pw_uid or info.st_size>2048:raise RuntimeError('Invalid action file')
            with os.fdopen(fd,'rb',closefd=False) as stream:value=json.loads(stream.read(2049))
        finally:os.close(fd)
        if not isinstance(value,dict) or not re.fullmatch('[a-zA-Z0-9-]{8,80}',str(value.get('id',''))):raise RuntimeError('Invalid action')
        return value
    finally:os.close(directory)


def initial_seen():
    previous=read_action()
    return {previous['id']} if previous else set()


def diagnostic_summary(directory):
    result={}
    for name in ('failure.txt','rollback-failure.txt'):
        path=directory/name
        if not path.exists():continue
        last=path.read_text().strip().splitlines()[-1]
        kind=last.split(':',1)[0]
        value={'exceptionType':kind if re.fullmatch('[A-Za-z_.]+',kind) else 'private-diagnostic'}
        if "['curl'," in last:value['component']='HTTPS health curl'
        match=re.search(r'exit status ([0-9]+)',last)
        if match:value['exitStatus']=int(match[1])
        result[name]=value
    return result


def main():
    if os.geteuid()!=0 or not os.isatty(0):raise SystemExit('Native private sudo TTY required')
    os.umask(0o077)
    lock=open('/run/lock/pf1007l-device-activation.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    stamp=time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-'+uuid.uuid4().hex[:8]
    parent=Path('/var/backups/pf1007l-device-auth');parent.mkdir(mode=0o700,exist_ok=True)
    if parent.is_symlink() or parent.stat().st_uid!=0 or parent.stat().st_mode & 0o077:raise RuntimeError('Unsafe backup parent')
    recover=len(sys.argv)==2 and sys.argv[1]=='--recover'
    resume=len(sys.argv)==2 and sys.argv[1] in ('--resume','--recover')
    if len(sys.argv)>1 and not resume:raise RuntimeError('Only --resume or --recover is accepted')
    if resume:
        saved=json.loads((parent/'latest-session.json').read_text())
        frozen=Path(saved['frozen']);backup=Path(saved['backup'])
        if frozen.parent!=parent or backup.parent!=parent or frozen.is_symlink() or backup.is_symlink():raise RuntimeError('Unsafe saved session')
        state=json.loads((frozen/'session-state.json').read_text())
        session=Activation(frozen,backup)
        session.baseline=json.loads((backup/'baseline-snapshot.json').read_text())
        session.protected=json.loads((backup/'protected-hashes.json').read_text())
        for name in ('mutated','proxy_touched','enrolled','compatible'):setattr(session,name,state[name])
    else:
        frozen=parent/('artifacts-'+stamp);freeze(frozen)
        session=Activation(frozen,parent/('backup-'+stamp))
    sys.path.insert(0,str(frozen))
    seen=initial_seen()
    def checkpoint():
        atomic(frozen/'session-state.json',json.dumps({name:getattr(session,name) for name in ('mutated','proxy_touched','enrolled','compatible')}).encode())
        atomic(parent/'latest-session.json',json.dumps({'frozen':str(frozen),'backup':str(session.backup)}).encode())
    try:
        if not resume:
            import runpy
            runpy.run_path(str(frozen/'activation_preflight.py'))['main']()
            result=session.make_backup();checkpoint()
            publish({'phase':'backup-ready','result':result});print('Private backup and consistent SQLite snapshot verified. Awaiting scoped actions.',flush=True)
        elif recover:
            result=session.verify_restored()
            session.mutated=False;session.proxy_touched=False;session.compatible=False;session.enrolled=None
            checkpoint()
            publish({'phase':'recovery-verified','result':result,'priorDiagnostics':diagnostic_summary(frozen)})
            print('Restored baseline verified against original backup. No deployment performed; waiting for a new explicit action.',flush=True)
        else:
            session.protected_ok();session.wait_healthy()
            publish({'phase':'session-resumed','result':session.status()});print('Approved scoped session resumed; original backup preserved.',flush=True)
    except Exception:
        retain_failure(frozen,'recovery-failure.txt' if recover else 'failure.txt');publish({'phase':'preflight-or-backup-failed','error':'Root-private diagnostics retained; no deployment attempted'})
        raise SystemExit(1)
    deadline=time.monotonic()+7200
    try:
        while time.monotonic()<deadline:
            if session.outage_until and time.monotonic()>=session.outage_until:
                session.run(['systemctl','start',BRIDGE]);session.outage_until=None
                publish({'phase':'outage-ended','result':session.status()})
            task=read_action()
            if not task or task['id'] in seen:time.sleep(1);continue
            seen.add(task['id']);kind=task.get('action')
            publish({'phase':kind,'running':True,'id':task['id']})
            try:
                if kind=='compat':result=session.compat(task.get('proxyRestartApproved'))
                elif kind=='enroll':result=session.enroll(task)
                elif kind=='activate':result=session.activate()
                elif kind=='status':result=session.status()
                elif kind in ('revoke','rotate'):result=session.registry_action(kind)
                elif kind=='restart-bridge':session.run(['systemctl','restart',BRIDGE]);session.wait_healthy();result=session.status()
                elif kind=='outage-start':
                    if session.settings().get('authMode')!='device-v1' or session.outage_until:raise RuntimeError('Outage phase gate failed')
                    recovery='pf1007l-device-auth-recovery-'+uuid.uuid4().hex[:10]
                    session.run(['systemd-run','--unit='+recovery,'--on-active=960s','--collect','/usr/bin/systemctl','start',BRIDGE])
                    session.run(['systemctl','stop',BRIDGE]);session.outage_until=time.monotonic()+960
                    result={'bridgeOnlyOutageSeconds':960,'automaticRestartScheduled':True,'startedUnix':time.time()}
                elif kind=='rollback':result=session.rollback()
                elif kind=='finish':
                    if session.outage_until:raise RuntimeError('Wait for scheduled recovery before finishing')
                    publish({'phase':'finished','id':task['id'],'result':session.status()});return
                else:raise RuntimeError('Unknown scoped action')
                checkpoint();publish({'phase':kind,'success':True,'id':task['id'],'result':result})
                print('PF1007L approved phase complete: '+str(kind),flush=True)
            except Exception:
                retain_failure(frozen,'failure.txt')
                try:rollback=session.rollback()
                except Exception:
                    retain_failure(frozen,'rollback-failure.txt');rollback={'rollbackFailed':True,'manualRecoveryRequired':True}
                checkpoint();publish({'phase':'failed','id':task['id'],'error':'Verification stopped; root-private diagnostics retained','rollback':rollback})
                return
    finally:
        if session.outage_until:session.run(['systemctl','start',BRIDGE])


if __name__=='__main__':main()
