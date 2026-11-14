#!/usr/bin/env python3
"""Owner-invoked rollback only: keep Radicale, demo data and unrelated services."""
import json
import os
from pathlib import Path
import shutil
import subprocess

if os.geteuid() != 0 or not os.isatty(0):
    raise SystemExit('Use a private native sudo Terminal after choosing rollback.')
root = Path('/opt/pf1007l-reminders-bridge')
etc = Path('/etc/pf1007l-reminders-bridge')
config = Path('/etc/pf1007l-proxy-https/config.json')
current = json.loads(config.read_text())
baseline = json.loads((etc / 'baseline-config.json').read_text())
# Retain the physically verified current frame address and dedicated firewall rule.
baseline['allowedClients'] = current['allowedClients']
shutil.copyfile(root / 'baseline-proxy.mjs', '/opt/pf1007l-tls/proxy.mjs')
config.write_text(json.dumps(baseline, indent=2)); config.chmod(0o644)
Path('/etc/systemd/system/pf1007l-proxy-https.service.d/reminders-demo.conf').unlink(missing_ok=True)
subprocess.run(['systemctl', 'disable', '--now', 'pf1007l-reminders-bridge.service'], check=True)
subprocess.run(['systemctl', 'daemon-reload'], check=True)
subprocess.run(['systemctl', 'restart', 'pf1007l-proxy-https.service'], check=True)
print('Demo bridge disabled; Radicale tasks/credentials and private Serve preserved.')
print('Restore only the kiosk URL to https://beestr0.duckdns.org:8789/ from the Mac.')
