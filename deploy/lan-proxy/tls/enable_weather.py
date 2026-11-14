#!/usr/bin/env python3
"""Scoped, reversible weather-only HTTPS proxy activation; run in native sudo TTY."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import sys

EXPECTED_OLD = '5130e38107542e73ec8ce1f89f35918634d155f2b7da312472583c8721007f45'
CODE = Path('/opt/pf1007l-tls/proxy.mjs')
CONFIG = Path('/etc/pf1007l-proxy-https/config.json')
STAGE = Path(__file__).resolve().parent
UNIT = 'pf1007l-proxy-https.service'

def run(args): return subprocess.check_output(args, stderr=subprocess.STDOUT, timeout=30)
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def baseline():
    return [digest(Path(p)) for p in ['/opt/pf1007l-proxy/pf1007l-lan-proxy.mjs','/etc/pf1007l-proxy/config.json']] + [run(['systemctl','show',u,'-p','MainPID','-p','ActiveState']) for u in ['pf1007l-proxy.service','jellyfin.service','tailscaled.service']]
def write(p,data,mode):
    t=p.with_name(p.name+'.weather-new');t.write_bytes(data);t.chmod(mode);t.replace(p)
def status(v):write(STAGE/'weather-state.json',json.dumps(v,indent=2).encode(),0o644)
def main():
    if os.geteuid()!=0 or not os.isatty(0):raise ValueError('Use native Terminal sudo authentication')
    os.umask(0o077)
    payload=STAGE/'weather-proxy.mjs'
    expected=(STAGE/'weather-proxy.sha256').read_text().strip()
    if payload.is_symlink() or digest(payload)!=expected or digest(CODE) not in [EXPECTED_OLD,expected]:raise ValueError('Unreviewed proxy source; refusing activation')
    cfg=json.loads(CONFIG.read_text())
    if cfg.get('demoOnly') is not True or cfg.get('tls',{}).get('hostname')!='beestr0.duckdns.org':raise ValueError('Unexpected existing HTTPS scope')
    before=baseline();oldcode=CODE.read_bytes();oldconfig=CONFIG.read_bytes()
    run(['/opt/pf1007l-proxy/node/bin/node','--check',str(payload)])
    backup=Path('/etc/pf1007l-tls')/('weather-backup-'+str(time.time_ns()));backup.mkdir(mode=0o700)
    write(backup/'proxy.mjs',oldcode,0o600);write(backup/'config.json',oldconfig,0o600)
    status({'phase':'activating','running':True})
    try:
        cfg['liveWeather']=True
        write(CODE,payload.read_bytes(),0o644);write(CONFIG,(json.dumps(cfg,indent=2)+'\n').encode(),0o644)
        run(['systemctl','restart',UNIT])
        healthy=False
        for _ in range(30):
            try:
                result=json.loads(run(['curl','--fail','--silent','--max-time','3','--resolve','beestr0.duckdns.org:8789:10.157.1.115','https://beestr0.duckdns.org:8789/__proxy_health']))
                healthy=True;break
            except Exception:time.sleep(.5)
        if not healthy or baseline()!=before:raise ValueError('Health or unrelated-service preservation check failed')
        status({'phase':'complete','success':True,'weatherOnly':True,'backup':str(backup),'unrelatedUnchanged':True})
        print('PF1007L_WEATHER_HTTPS_ENABLED; HTTP and unrelated services preserved.')
    except Exception:
        write(CODE,oldcode,0o644);write(CONFIG,oldconfig,0o644)
        run(['systemctl','restart',UNIT]);status({'phase':'rolled-back','success':False})
        raise
if __name__=='__main__':
    try:main()
    except Exception:
        # No raw exception/credential-bearing upstream response is printed.
        print('PF1007L_WEATHER_ACTIVATION_FAILED; previous proxy configuration retained.',file=sys.stderr)
        sys.exit(1)
