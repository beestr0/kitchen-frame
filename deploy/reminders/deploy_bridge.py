"""Scoped demo bridge deployment; original root route/assets and providers remain intact."""
import hashlib
import http.client
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tarfile
import time


def run(args):
    return subprocess.run(args, check=True, text=True, capture_output=True).stdout


def execute(stage):
    root = Path('/opt/pf1007l-reminders-bridge')
    etc = Path('/etc/pf1007l-reminders-bridge')
    proxy = Path('/opt/pf1007l-tls/proxy.mjs')
    proxy_config = Path('/etc/pf1007l-proxy-https/config.json')
    manifest = json.loads((stage / 'bridge-manifest.json').read_text())
    # Review exact staged sources before root installs them.
    for name, digest in manifest['files'].items():
        if hashlib.sha256((stage / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError('Staged artifact checksum mismatch')
    if manifest.get('uiOnly') is True:
        ui = root / 'ui'
        if not ui.is_dir():
            raise RuntimeError('Existing demo UI required for asset-only update')
        with tarfile.open(stage / 'reminders-ui.tar.gz') as archive:
            for member in archive.getmembers():
                if member.issym() or member.islnk() or member.name.startswith('/') or '..' in Path(member.name).parts:
                    raise RuntimeError('Unsafe UI artifact member')
            archive.extractall(ui, filter='data')
        for item in ui.rglob('*'):
            item.chmod(0o755 if item.is_dir() else 0o644)
        return {'demoUIUpdated': True, 'servicesRestarted': False, 'credentialsAndTasksPreserved': True}
    if not (root / 'baseline-proxy.mjs').exists() and hashlib.sha256(proxy.read_bytes()).hexdigest() != manifest['baselineProxy']:
        raise RuntimeError('Running proxy differs from reviewed baseline; preserve it')
    root.mkdir(mode=0o755, exist_ok=True); root.chmod(0o755)
    etc.mkdir(mode=0o700, exist_ok=True); etc.chmod(0o700)
    if not (root / 'baseline-proxy.mjs').exists():
        shutil.copy2(proxy, root / 'baseline-proxy.mjs')
        shutil.copy2(proxy_config, etc / 'baseline-config.json')
        (etc / 'baseline-config.json').chmod(0o600)
    settings_file = etc / 'settings.json'
    if settings_file.exists():
        settings = json.loads(settings_file.read_text())
    else:
        clients = json.loads(proxy_config.read_text())['allowedClients']
        if len(clients) != 1:
            raise RuntimeError('Review the existing single-frame allowlist before provisioning')
        settings = {'apiKey': secrets.token_hex(32), 'session': secrets.token_hex(32), 'csrf': secrets.token_hex(32), 'frameIP': clients[0]}
        settings_file.write_text(json.dumps(settings)); settings_file.chmod(0o600)
    (etc / 'proxy-key').write_text(settings['apiKey']); (etc / 'proxy-key').chmod(0o600)
    shutil.copyfile(stage / 'task_bridge.py', root / 'task_bridge.py'); (root / 'task_bridge.py').chmod(0o644)
    ui = root / 'ui'; ui.mkdir(mode=0o755, exist_ok=True); ui.chmod(0o755)
    with tarfile.open(stage / 'reminders-ui.tar.gz') as archive:
        for member in archive.getmembers():
            if member.issym() or member.islnk() or member.name.startswith('/') or '..' in Path(member.name).parts:
                raise RuntimeError('Unsafe UI artifact member')
        archive.extractall(ui, filter='data')
    # Do not inherit root's private umask for files read by DynamicUser.
    for item in ui.rglob('*'):
        item.chmod(0o755 if item.is_dir() else 0o644)
    unit = Path('/etc/systemd/system/pf1007l-reminders-bridge.service')
    unit.write_bytes((stage / unit.name).read_bytes()); unit.chmod(0o644)
    run(['systemd-analyze', 'verify', str(unit)])
    run(['systemctl', 'daemon-reload'])
    run(['systemctl', 'enable', '--now', unit.name])
    for _ in range(25):
        try:
            connection = http.client.HTTPConnection('127.0.0.1', 5240, timeout=2)
            connection.request('GET', '/__reminders-demo/snapshot', headers={'X-Pilot-Key': settings['apiKey'], 'X-Pilot-Client': settings['frameIP'], 'Cookie': 'pf1007l-demo=' + settings['session']})
            response = connection.getresponse(); data = json.loads(response.read()); connection.close()
            if response.status == 200 and not data.get('stale'):
                break
        except (OSError, ValueError):
            pass
        time.sleep(1)
    else:
        raise RuntimeError('Demo task bridge not ready; HTTPS baseline untouched')
    # Only after the adapter is healthy add its isolated local route to HTTPS.
    shutil.copyfile(stage / 'reminders-demo-proxy.mjs', proxy.parent / 'reminders-demo-proxy.mjs')
    (proxy.parent / 'reminders-demo-proxy.mjs').chmod(0o644)
    shutil.copyfile(stage / 'proxy.mjs', proxy); proxy.chmod(0o644)
    cfg = json.loads(proxy_config.read_text())
    cfg['remindersDemo'] = {'enabled': True, 'uiDirectory': str(ui)}
    proxy_config.write_text(json.dumps(cfg, indent=2)); proxy_config.chmod(0o644)
    dropin = Path('/etc/systemd/system/pf1007l-proxy-https.service.d')
    dropin.mkdir(mode=0o755, exist_ok=True)
    (dropin / 'reminders-demo.conf').write_text('[Service]\nLoadCredential=reminders-demo-key:/etc/pf1007l-reminders-bridge/proxy-key\n')
    (dropin / 'reminders-demo.conf').chmod(0o644)
    try:
        run(['systemctl', 'daemon-reload'])
        run(['systemctl', 'restart', 'pf1007l-proxy-https.service'])
        run(['curl', '--fail', '--silent', '--retry', '5', '--retry-connrefused', '--resolve', 'beestr0.duckdns.org:8789:10.157.1.115', 'https://beestr0.duckdns.org:8789/__proxy_health'])
    except Exception:
        # Restore the known-working HTTPS implementation/config; retain task data.
        shutil.copyfile(root / 'baseline-proxy.mjs', proxy)
        shutil.copyfile(etc / 'baseline-config.json', proxy_config)
        proxy_config.chmod(0o644)
        (dropin / 'reminders-demo.conf').unlink(missing_ok=True)
        run(['systemctl', 'daemon-reload']); run(['systemctl', 'restart', 'pf1007l-proxy-https.service'])
        raise
    matches = [{'title': x['title'], 'due': x['due'], 'completed': x['completed']} for x in data['items'] if 'edited on iPhone' in x['title']]
    return {'demoBridgeReady': True, 'items': len(data['items']), 'phoneTask': matches,
            'url': 'https://beestr0.duckdns.org:8789/__reminders-demo/',
            'normalDashboardURLPreserved': True, 'state': 'demo-only'}
