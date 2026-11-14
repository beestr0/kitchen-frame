#!/usr/bin/env python3
"""Read-only, standard-library activation/status check. No tokens or task contents."""
import json
import os
from pathlib import Path
import sqlite3
import stat
import subprocess

BRIDGE = 'pf1007l-reminders-bridge.service'


def main():
    if os.geteuid() != 0 or not os.isatty(0):
        raise SystemExit('Use the reviewed helper in an interactive native sudo TTY')
    settings_path = Path('/etc/pf1007l-reminders-bridge/settings.json')
    checks = {}
    for name in ['/etc/pf1007l-reminders-bridge', str(settings_path), '/etc/pf1007l-reminders-demo/demo-account.json']:
        path = Path(name); info = path.lstat()
        allowed = 0o700 if stat.S_ISDIR(info.st_mode) else 0o600
        checks[name] = info.st_uid == 0 and stat.S_IMODE(info.st_mode) == allowed and not stat.S_ISLNK(info.st_mode)
    settings = json.loads(settings_path.read_text())
    report = {'readOnly':True, 'privatePermissions':checks, 'configuredAuthMode':settings.get('authMode','legacy-demo')}
    services = ['pf1007l-reminders-demo.service', BRIDGE, 'pf1007l-proxy-https.service', 'jellyfin', 'tailscaled']
    report['services'] = {unit:subprocess.run(['systemctl','is-active',unit],capture_output=True,text=True).stdout.strip() for unit in services}
    state = Path('/var/lib/pf1007l-reminders-bridge/tasks.sqlite')
    db = sqlite3.connect('file:'+str(state)+'?mode=ro',uri=True,timeout=5)
    try:
        report['databaseHealthy'] = db.execute('PRAGMA quick_check').fetchone()[0] == 'ok'
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        report['operations'] = dict(db.execute('SELECT result,COUNT(*) FROM operations GROUP BY result'))
        # Aggregate timestamps/counts only. Never print token hashes, CSRF, UIDs,
        # task titles, settings contents, public registry entries or passwords.
        if 'device_sessions' in tables:
            count,latest,expiry = db.execute('SELECT COUNT(*),MAX(issued),MAX(expires) FROM device_sessions').fetchone()
            report['sessions'] = {'count':count, 'latestIssuedUnix':latest, 'latestExpiryUnix':expiry}
            report['activeDeviceCount'] = db.execute('SELECT COUNT(*) FROM device_keys WHERE active=1').fetchone()[0]
    finally: db.close()
    print(json.dumps(report,indent=2))
    if not all(checks.values()) or not report['databaseHealthy'] or any(value!='active' for value in report['services'].values()):
        raise SystemExit('Preflight needs attention; no configuration changed')


if __name__ == '__main__': main()
