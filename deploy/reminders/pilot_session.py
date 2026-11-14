#!/usr/bin/env python3
"""Private native sudo session for reviewed, hash-checked demo integration phases."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
import time

STAGE = Path(__file__).resolve().parent


def report(value):
    temp = STAGE / '.integration-status.new'
    temp.write_text(json.dumps(value, indent=2))
    temp.chmod(0o644)
    temp.replace(STAGE / 'integration-status.json')


def main():
    if os.geteuid() != 0 or not os.isatty(0):
        raise RuntimeError('Private native sudo TTY required')
    os.umask(0o077)
    lock = open('/run/lock/pf1007l-reminders-integration.lock', 'a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    report({'phase': 'integration-session-ready'})
    print('Private demo integration session ready. Leave this Terminal open.', flush=True)
    seen = set()
    deadline = time.monotonic() + 1800
    while time.monotonic() < deadline:
        action = STAGE / 'integration-action.json'
        if not action.exists():
            time.sleep(1); continue
        task = json.loads(action.read_text())
        identifier = task.get('id')
        if identifier in seen:
            time.sleep(1); continue
        seen.add(identifier)
        phase = task.get('phase')
        if phase == 'finish':
            report({'phase': 'integration-session-finished', 'id': identifier}); return
        files = {'inspect': 'inspect_phone.py', 'deploy': 'deploy_bridge.py', 'audit': 'audit_bridge.py'}
        script = STAGE / files.get(phase, 'invalid')
        if phase not in files or not script.is_file() or hashlib.sha256(script.read_bytes()).hexdigest() != task.get('sha256'):
            report({'phase': 'rejected', 'id': identifier, 'error': 'Unknown phase or checksum mismatch'}); continue
        try:
            report({'phase': phase, 'running': True, 'id': identifier})
            result = runpy.run_path(str(script))['execute'](STAGE)
            report({'phase': phase, 'success': True, 'id': identifier, 'result': result})
            print('PF1007L_DEMO_PHASE_COMPLETE: ' + phase, flush=True)
        except Exception:
            import traceback
            log = Path('/root/pf1007l-reminders-integration-failure.txt')
            log.write_text(traceback.format_exc()); log.chmod(0o600)
            report({'phase': phase, 'success': False, 'id': identifier, 'error': 'Root-private diagnostics retained'})
            print('Scoped phase failed; private diagnostics retained.', flush=True)
        deadline = time.monotonic() + 1800
    report({'phase': 'integration-session-expired'})


if __name__ == '__main__':
    main()
