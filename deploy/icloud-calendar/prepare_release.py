#!/usr/bin/env python3
"""Freeze a credential-free Calendar candidate; never deploy or contact Apple."""
import argparse
import re
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[2]


def main():
    os.umask(0o077)
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',default='calendar-candidate')
    args=parser.parse_args()
    if not re.fullmatch(r'calendar-candidate(?:-[A-Za-z0-9]+)?',args.label):raise SystemExit('Invalid candidate label')
    output=ROOT/'diagnostics/pf1007l'/args.label
    if output.exists():raise SystemExit('Existing candidate preserved; choose a new reviewed output before rebuilding')
    sources=[
        'deploy/icloud-calendar/collector.py','deploy/icloud-calendar/service.py',
        'deploy/icloud-calendar/readonly_caldav.py','deploy/icloud-calendar/normalize.mjs',
        'deploy/icloud-calendar/authorize.py','deploy/icloud-calendar/prepare_credentials.py',
        'deploy/icloud-calendar/pf1007l-calendar.service','deploy/icloud-calendar/bridge-calendar.conf',
        'deploy/reminders/task_bridge.py','scripts/reminders-demo-proxy.mjs',
        'dashboard/worker/calendar.js','dashboard/package.json',
        'dashboard/node_modules/ical.js/package.json','dashboard/node_modules/ical.js/dist/ical.js']
    ui=ROOT/'dashboard/dist-reminders-demo'
    if not (ui/'index.html').is_file():raise SystemExit('Build the isolated UI first')
    sources += [str(p.relative_to(ROOT)) for p in ui.rglob('*') if p.is_file()]
    for source in sources:
        p=ROOT/source
        if not p.is_file() or p.is_symlink():raise SystemExit('Missing/unsafe candidate source')
    output.mkdir(mode=0o700,parents=True)
    for source in sources:
        target=output/source;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/source,target);target.chmod(0o600)
    manifest={'purpose':'PREPARED ONLY; account/selection authorization before deployment',
        'sourceBase':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'files':{s:hashlib.sha256((output/s).read_bytes()).hexdigest() for s in sorted(sources)}}
    path=output/'manifest.json';path.write_text(json.dumps(manifest,indent=2)+'\n');path.chmod(0o600)
    print('Credential-free candidate:',output)
    print('Manifest SHA256:',hashlib.sha256(path.read_bytes()).hexdigest())
    print('No account, credential, calendar data, runtime database or service changes included.')


if __name__=='__main__':main()
