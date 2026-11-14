#!/usr/bin/env python3
"""Scoped resumable phase implementation, invoked by secure_session.py as root."""
import configparser
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request

ROOT=Path('/etc/pf1007l-tls')
PROJECT=Path('/opt/pf1007l-tls')
CONF=Path('/etc/pf1007l-proxy-https')
ACME=Path('/var/lib/pf1007l-acme')
HOST='beestr0.duckdns.org'
UNIT='pf1007l-proxy-https.service'
GUARD='pf1007l-proxy-https-firewall.service'
UNITS=[GUARD,UNIT,'pf1007l-cert-renew.service','pf1007l-cert-renew.timer','pf1007l-tls-monitor.service','pf1007l-tls-monitor.timer']


def run(args,check=True,env=None,timeout=120):
    result=subprocess.run(args,capture_output=True,text=True,env=env,timeout=timeout)
    if check and result.returncode:
        # These calls never contain credentials. Certbot output itself stays private.
        raise RuntimeError(repr(args)+' failed:\n'+result.stdout+'\n'+result.stderr)
    return result


def props(unit,*names):
    result=run(['systemctl','show',unit,*sum((['-p',name] for name in names),[])],check=False)
    return dict(l.split('=',1) for l in result.stdout.splitlines() if '=' in l)


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def unrelated():
    return {'services':{unit:props(unit,'MainPID','ActiveState') for unit in ['jellyfin','tailscaled','pf1007l-proxy']},
            'httpSource':digest('/opt/pf1007l-proxy/pf1007l-lan-proxy.mjs'),
            'httpConfig':digest('/etc/pf1007l-proxy/config.json'),
            'mount':run(['findmnt','-n','-o','TARGET,FSTYPE','--target','/mnt/media']).stdout,
            'iptables':run(['iptables','-S']).stdout,'ip6tables':run(['ip6tables','-S']).stdout}


def module(name):
    spec=importlib.util.spec_from_file_location('pf1007l_'+name,PROJECT/(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def write(path,data,mode=0o644):
    path=Path(path)
    if path.is_symlink():raise ValueError('Refusing symlink destination')
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.read_bytes()==data:return
    temporary=path.with_name(path.name+'.pf1007l-new')
    if temporary.exists():raise ValueError('Unexpected temporary artifact')
    temporary.write_bytes(data);temporary.chmod(mode);temporary.replace(path)


def install(stage):
    manifest_path=ROOT/'install-manifest.json'
    prior=json.loads(manifest_path.read_text()) if manifest_path.exists() else {'files':{}}
    before=prior.get('before') or unrelated()
    cfg=json.loads((ROOT/'profile.json').read_text())
    if cfg!={'hostname':HOST,'address':'10.157.1.115'}:raise ValueError('Unexpected private hostname/profile')
    if run(['ss','-H','-lnt','sport = :8789']).stdout.strip() and props(UNIT,'ActiveState').get('ActiveState')!='active':
        raise ValueError('Unknown listener occupies 8789')
    guard_changed=(CONF/'firewall.nft').exists() and (CONF/'firewall.nft').read_bytes()!=(stage/'firewall.nft.example').read_bytes()
    files={}
    for source in list(stage.glob('*.py')):
        if source.name not in ['secure_session.py','install_https.py']:
            files[PROJECT/source.name]=(source.read_bytes(),0o755)
    files[PROJECT/'proxy.mjs']=((stage/'proxy.mjs').read_bytes(),0o644)
    files[PROJECT/'requirements.txt']=((stage/'requirements.txt').read_bytes(),0o644)
    configuration=json.loads((stage/'config.json.example').read_text());configuration['tls']['hostname']=HOST
    files[CONF/'config.json']=(json.dumps(configuration,indent=2).encode(),0o644)
    files[CONF/'firewall.nft']=((stage/'firewall.nft.example').read_bytes(),0o644)
    files[ROOT/'frame-roots.pem']=((stage/'frame-roots.pem').read_bytes(),0o600)
    for unit in UNITS:files[Path('/etc/systemd/system')/unit]=((stage/unit).read_bytes(),0o644)
    PROJECT.mkdir(mode=0o755,parents=True,exist_ok=True);CONF.mkdir(mode=0o755,parents=True,exist_ok=True)
    PROJECT.chmod(0o755);CONF.chmod(0o755)
    for path,(data,mode) in files.items():
        if path.exists() and path.read_bytes()!=data and prior['files'].get(str(path))!=digest(path):
            raise ValueError('Unrecognized existing project file: '+str(path))
        write(path,data,mode)
        prior['files'][str(path)]=digest(path)
    prior['before']=before
    write(manifest_path,json.dumps(prior,indent=2).encode(),0o600)
    sys.path.insert(0,str(PROJECT))
    binary=PROJECT/'venv/bin/python'
    if not binary.exists():run(['python3','-m','venv','--without-pip',str(PROJECT/'venv')])
    requirements=(PROJECT/'requirements.txt').read_text()
    check='import importlib.metadata as m,json;print(json.dumps({k:m.version(k) for k in '+repr([l.split('==')[0] for l in requirements.splitlines() if l])+ '}))'
    installed=run([str(binary),'-c',check],check=False)
    exact=False
    if installed.returncode==0:
        versions=json.loads(installed.stdout);exact=all(versions[l.split('==')[0]]==l.split('==')[1] for l in requirements.splitlines() if l)
    if not exact:
        pip=next((stage/'wheels').glob('pip-*.whl'))
        env=dict(os.environ,PYTHONPATH=str(pip),PIP_DISABLE_PIP_VERSION_CHECK='1')
        result=run([str(binary),'-m','pip','install','--no-index','--find-links',str(stage/'wheels'),'-r',str(PROJECT/'requirements.txt')],check=False,env=env,timeout=240)
        write(ROOT/'dependency-install.log',(result.stdout+result.stderr).encode(),0o600)
        if result.returncode:raise ValueError('Offline isolated dependency installation failed')
    run(['/opt/pf1007l-proxy/node/bin/node','--check',str(PROJECT/'proxy.mjs')])
    run(['nft','--check','--file',str(CONF/'firewall.nft')])
    run(['systemctl','daemon-reload'])
    for unit in UNITS:
        properties=props(unit,'LoadState','FragmentPath','DropInPaths')
        if properties.get('LoadState')!='loaded' or properties.get('FragmentPath')!='/etc/systemd/system/'+unit or properties.get('DropInPaths'):
            raise ValueError('Unexpected unit registration/drop-ins: '+unit)
    run(['systemd-analyze','verify',*[str(Path('/etc/systemd/system')/u) for u in UNITS]])
    if guard_changed and props(GUARD,'ActiveState').get('ActiveState')=='active':
        run(['systemctl','stop',UNIT]);run(['systemctl','restart',GUARD])
    dns=module('dns_hook')
    original=prior.get('originalDNS')
    if original is None:
        original={'A':sorted(dns.dig(HOST,'A')),'AAAA':sorted(dns.dig(HOST,'AAAA'))}
        prior['originalDNS']=original;write(manifest_path,json.dumps(prior,indent=2).encode(),0o600)
    if dns.dig(HOST,'AAAA'):raise ValueError('Unexpected IPv6 record; refusing unreviewed removal')
    if dns.dig(HOST,'A')!={'10.157.1.115'}:
        from acme_common import private_read
        token=private_read(ROOT/'duckdns-token').strip()
        url='https://www.duckdns.org/update?'+urllib.parse.urlencode({'domains':'beestr0','token':token,'ip':'10.157.1.115'})
        try:
            with urllib.request.build_opener(dns.NoRedirect()).open(url,timeout=20) as response:
                if response.read(128).decode().strip()!='OK':raise ValueError('DNS update refused')
        except Exception:raise ValueError('DNS update failed; no credential details logged') from None
    acme=module('run_acme')
    deadline=time.monotonic()+120
    while time.monotonic()<deadline:
        if acme.published_lan_address(cfg):break
        time.sleep(2)
    else:raise ValueError('Published private hostname mapping not verified')
    recovery=stage/'recover-owned-challenge.json'
    if not recovery.exists() and (stage/'recovered-owned-challenge.json').exists():recovery=stage/'recovered-owned-challenge.json'
    if recovery.exists():
        owned=json.loads(recovery.read_text())
        ownership=ROOT/'challenge-ownership.json'
        known=json.loads(ownership.read_text()) if ownership.exists() else []
        if owned['sha256'] not in known:known.append(owned['sha256'])
        write(ownership,json.dumps(known).encode(),0o600)
        if recovery.name!='recovered-owned-challenge.json':recovery.rename(stage/'recovered-owned-challenge.json')
    lineage=ACME/'config/live/pf1007l-desk'
    if not (lineage/'fullchain.pem').exists():
        result=run(['python3',str(PROJECT/'run_acme.py'),'issue'],check=False,timeout=900)
        write(ROOT/'issue-operation.log',(result.stdout+result.stderr).encode(),0o600)
        if result.returncode:raise ValueError('ACME issuance/activation failed; details retained privately')
    else:
        env=dict(os.environ,RENEWED_LINEAGE=str(lineage))
        result=run(['python3',str(PROJECT/'activate_certificate.py')],check=False,env=env)
        if result.returncode:raise ValueError('Existing issued certificate activation failed; no reissuance performed')
    run(['python3',str(PROJECT/'run_acme.py'),'renew'],timeout=900)
    if unrelated()!=before:raise ValueError('Unrelated service/filter/fallback state changed')
    prior['installed']=True;write(manifest_path,json.dumps(prior,indent=2).encode(),0o600)
    monitor=module('monitor');public,health=monitor.endpoint(cfg)
    cert=run(['openssl','x509','-in',str(ROOT/'certificates/current/tls-chain'),'-noout','-subject','-issuer','-dates','-fingerprint','-sha256']).stdout
    return {'https':'https://'+HOST+':8789/','health':health,'certificate':cert,'unrelatedUnchanged':True,'originalDNS':original}


def execute(phase,stage):
    stage=Path(stage)
    if phase=='audit' and (stage/'dns-diagnose-request').exists():
        sys.path.insert(0,str(PROJECT));dns=module('dns_hook')
        values=dns.public_txt('_acme-challenge.'+HOST,'TXT','google')
        if len(values)!=1:raise ValueError('No single current task challenge found')
        cfg={'CERTBOT_IDENTIFIER':HOST,'CERTBOT_ALL_IDENTIFIERS':HOST,'CERTBOT_VALIDATION':next(iter(values))}
        old_args=sys.argv[:];old_env={key:os.environ.get(key) for key in cfg}
        try:
            os.environ.update(cfg);sys.argv=['dns_hook.py','auth'];code=dns.main()
        finally:
            sys.argv=old_args
            for key,value in old_env.items():
                if value is None:os.environ.pop(key,None)
                else:os.environ[key]=value
        (stage/'dns-diagnose-request').unlink()
        details=json.loads((ROOT/'dns-hook-status.json').read_text()) if code and (ROOT/'dns-hook-status.json').exists() else {}
        return {'dnsHookExit':code,'safeStatus':details}
    if phase=='audit'  and (stage/'diagnose-request').exists():
        import re
        secrets=[]
        if (ROOT/'duckdns-token').exists():secrets.append((ROOT/'duckdns-token').read_text().strip())
        if (ROOT/'acme.ini').exists():
            parsed=configparser.ConfigParser(interpolation=None);parsed.read_string('[acme]\n'+(ROOT/'acme.ini').read_text())
            secrets.extend(parsed['acme'].get(k,'') for k in ['email','eab-kid','eab-hmac-key'])
        paths=sorted(ROOT.glob('phase-*.log'),key=lambda p:p.stat().st_mtime)[-1:]
        if (ROOT/'dependency-install.log').exists():paths.append(ROOT/'dependency-install.log')
        if (ACME/'last-run.log').exists():paths.append(ACME/'last-run.log')
        if (ROOT/'dns-hook-status.json').exists():paths.append(ROOT/'dns-hook-status.json')
        output=[]
        for path in paths:
            text=path.read_text(errors='replace')
            for value in secrets:
                if value:text=text.replace(value,'[REDACTED]')
            text=re.sub(r'-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----','[PRIVATE KEY REDACTED]',text,flags=re.S)
            text=re.sub(r'https://[^\s]+[?][^\s]+','[CREDENTIAL-QUERY URL REDACTED]',text)
            output.append({'source':path.name,'sanitizedTail':text[-5000:]})
        (stage/'diagnose-request').unlink()
        return {'privateValuesRedacted':True,'diagnostics':output}
    if phase=='install':return install(stage)
    sys.path.insert(0,str(PROJECT))
    cfg=json.loads((ROOT/'profile.json').read_text());monitor=module('monitor')
    before=unrelated()
    if phase in ['crash','interruption']:
        initial=props(UNIT,'MainPID','NRestarts')
        if phase=='crash':run(['systemctl','kill','--kill-whom=main','--signal=SIGKILL',UNIT])
        else:
            run(['systemctl','stop',UNIT]);(stage/'https-stopped').write_text('stopped');time.sleep(8);run(['systemctl','start',UNIT])
        started=time.monotonic();health=None
        for _ in range(70):
            time.sleep(.5)
            try:_,health=monitor.endpoint(cfg);break
            except Exception:pass
        if health is None:raise ValueError('HTTPS recovery deadline exceeded')
        after=props(UNIT,'MainPID','NRestarts')
        if phase=='crash' and (initial['MainPID']==after['MainPID'] or int(after['NRestarts'])<=int(initial['NRestarts'])):raise ValueError('Automatic restart not proven')
        if phase=='interruption':(stage/'https-recovered').write_text('healthy')
        if unrelated()!=before:raise ValueError('Unrelated state changed')
        return {'before':initial,'after':after,'recoverySeconds':time.monotonic()-started,'health':health,'unrelatedUnchanged':True}
    if phase=='renew':
        initial=props(UNIT,'MainPID')
        env=dict(os.environ,RENEWED_LINEAGE=str(ACME/'config/live/pf1007l-desk'))
        run(['python3',str(PROJECT/'activate_certificate.py')],env=env)
        run(['python3',str(PROJECT/'run_acme.py'),'renew'],timeout=900)
        if initial!=props(UNIT,'MainPID'):raise ValueError('Hot reload unexpectedly restarted the process')
        _,health=monitor.endpoint(cfg)
        return {'hotReloadWithoutRestart':True,'renewalCheckPassed':True,'health':health}
    if phase=='enable':
        proof=json.loads((stage/'physical-proof.json').read_text())
        if proof.get('success') is not True:raise ValueError('Physical acceptance is required before boot activation')
        result=run(['python3',str(PROJECT/'monitor.py')])
        run(['systemctl','enable',UNIT,GUARD,'pf1007l-cert-renew.timer','pf1007l-tls-monitor.timer'])
        run(['systemctl','start','pf1007l-cert-renew.timer','pf1007l-tls-monitor.timer'])
        if unrelated()!=before:raise ValueError('Unrelated state changed')
        return {'enabled':True,'monitor':result.stdout.strip()}
    if phase=='monitor-test':
        healthy=monitor.evaluate(cfg)
        bad=dict(cfg,address='127.0.0.2')
        failed=monitor.evaluate(bad)
        if healthy['issues'] or 'https-health-or-certificate-failed' not in failed['issues']:raise ValueError('Monitor positive/negative test failed')
        run(['python3',str(PROJECT/'monitor.py')])
        return {'healthy':healthy,'controlledFailureDetected':True,'externalNotificationsEnabled':False}
    if phase=='audit':
        result=run(['python3',str(PROJECT/'monitor.py')],check=False)
        return {'monitorExit':result.returncode,'state':json.loads((ROOT/'monitor-status.json').read_text()),'unrelated':unrelated()}
    raise ValueError('Unknown project-specific phase')
