#!/usr/bin/env python3
"""Prepare a private, credential-free activation bundle locally. Never deploy/install."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/'diagnostics/pf1007l/device-auth-activation'
SOURCES={
 'task_bridge.py':'deploy/reminders/task_bridge.py',
 'device_auth.py':'deploy/reminders/device_auth.py',
 'device_registry.py':'deploy/reminders/device_registry.py',
 'activation_preflight.py':'deploy/reminders/activation_preflight.py',
 'pf1007l-reminders-bridge.service':'deploy/reminders/pf1007l-reminders-bridge.service',
 'reminders-demo-proxy.mjs':'scripts/reminders-demo-proxy.mjs',
 'frame-auth-candidate.apk':'kiosk/build-auth-candidate/frame-auth-candidate.apk',
 'frame-auth-rollback.apk':'kiosk/build-auth-rollback/frame-auth-rollback.apk',
}


def main():
    os.umask(0o077)
    if OUTPUT.exists(): raise SystemExit('Bundle already exists; preserve it and choose a new reviewed output before rebuilding')
    ui=ROOT/'dashboard/dist-reminders-demo'
    if not (ui/'index.html').is_file():raise SystemExit('Build the isolated demo UI first')
    for source in SOURCES.values():
        if not (ROOT/source).is_file():raise SystemExit('Required reviewed artifact missing: '+source)
    OUTPUT.mkdir(parents=True,mode=0o700)
    for name,source in SOURCES.items():shutil.copyfile(ROOT/source,OUTPUT/name)
    with tarfile.open(OUTPUT/'reminders-ui.tar.gz','w:gz') as archive:
        for path in sorted(ui.rglob('*')):
            if path.is_symlink():raise SystemExit('UI symlink rejected')
            if path.is_file():archive.add(path,arcname=str(path.relative_to(ui)),recursive=False)
    (OUTPUT/'device-auth.conf').write_text('[Service]\nLoadCredential=device-registry:/etc/pf1007l-reminders-bridge/device-registry.json\n')
    manifest={'sourceCommit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'purpose':'PREPARED ONLY; explicit owner approval required before installation/enrollment',
        'files':{path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(OUTPUT.iterdir())}}
    (OUTPUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    for path in OUTPUT.iterdir():path.chmod(0o600)
    print('Prepared credential-free bundle:',OUTPUT)
    print('Manifest SHA256:',hashlib.sha256((OUTPUT/'manifest.json').read_bytes()).hexdigest())
    print('No server/app changes, credentials, registry enrollment or activation performed.')


if __name__=='__main__':main()
