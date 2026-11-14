#!/usr/bin/env python3
"""One native Terminal root session; private prompts, resumable scoped phases."""
import hashlib
import fcntl
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import time
import traceback

STAGE = Path(__file__).resolve().parent
STATE = STAGE / 'session-state.json'
ROOT = Path('/etc/pf1007l-tls')


def public_state(value):
    temp=STATE.with_suffix('.new');temp.write_text(json.dumps(value,indent=2));temp.chmod(0o644);temp.replace(STATE)


def main():
    if os.geteuid()!=0 or not os.isatty(0):
        raise SystemExit('Use secure native Terminal sudo authentication.')
    os.umask(0o077)
    if '--wait-for' in sys.argv:
        previous=int(sys.argv[sys.argv.index('--wait-for')+1])
        print('Waiting for the previous bounded helper to exit; no concurrent installation.',flush=True)
        while True:
            try:os.kill(previous,0)
            except ProcessLookupError:break
            time.sleep(1)
    lock=(STAGE/'session.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    public_state({'phase':'secure-entry','ready':False})
    if not (ROOT/'acme.ini').exists() or '--correct-eab' in sys.argv:
        command=['python3',str(STAGE/'prepare_secrets.py'),'--hostname','beestr0.duckdns.org']
        if '--correct-eab' in sys.argv:command.append('--correct-eab')
        try:result=subprocess.run(command)
        except KeyboardInterrupt:
            public_state({'phase':'credential-entry-interrupted','ready':False});return 130
        if result.returncode:
            public_state({'phase':'credential-entry-incomplete','ready':False,'exit':result.returncode});return result.returncode
    else:
        print('Existing private ACME configuration preserved.',flush=True)
    public_state({'phase':'credentials-ready','ready':True})
    print('PF1007L_PRIVATE_CONFIGURATION_READY',flush=True)
    consumed=set();deadline=time.monotonic()+3600
    while time.monotonic()<deadline:
        request=STAGE/'action.json'
        if not request.exists():time.sleep(1);continue
        action=json.loads(request.read_text());identifier=action.get('id')
        if identifier in consumed:time.sleep(1);continue
        consumed.add(identifier)
        deadline=time.monotonic()+3600  # idle limit; active phases retain their authorized session
        phase=action.get('phase')
        if phase=='finish':
            public_state({'phase':'finished','success':True,'id':identifier});return
        if phase not in ('install','crash','interruption','renew','enable','monitor-test','audit'):
            public_state({'phase':phase,'success':False,'error':'Unknown scoped phase','id':identifier});continue
        script=STAGE/'install_https.py'
        if hashlib.sha256(script.read_bytes()).hexdigest()!=action.get('sha256'):
            public_state({'phase':phase,'success':False,'error':'Deployment checksum mismatch','id':identifier});continue
        public_state({'phase':phase,'running':True,'id':identifier})
        try:
            module=runpy.run_path(str(script))
            result=module['execute'](phase,STAGE)
            public_state({'phase':phase,'success':True,'result':result,'id':identifier})
            deadline=time.monotonic()+3600
            print('PF1007L_PHASE_COMPLETE: '+phase,flush=True)
        except Exception:
            log=ROOT/('phase-'+str(int(time.time()))+'.log')
            log.write_text(traceback.format_exc());log.chmod(0o600)
            public_state({'phase':phase,'success':False,'error':'Scoped phase failed; details retained privately on server','id':identifier})
            print('PF1007L_PHASE_FAILED: '+phase+'; private diagnostics retained.',flush=True)
    public_state({'phase':'session-expired','success':False})


if __name__=='__main__':
    raise SystemExit(main())
