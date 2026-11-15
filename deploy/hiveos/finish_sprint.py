#!/usr/bin/env python3
"""Bounded approved metadata deployment; no credentials or event/task contents printed.

Run from a root-owned frozen copy of the source-only release. Current task databases,
Apple credential, device registry, network guards and unrelated services are untouched.
"""
import hashlib
import http.client
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
CONFIG = Path('/etc/pf1007l-calendar/config.json')
CAL = Path('/opt/pf1007l-calendar/deploy/icloud-calendar')
BRIDGE = Path('/opt/pf1007l-reminders-bridge/task_bridge.py')
UI = Path('/opt/pf1007l-reminders-bridge/ui')


def command(*args):
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL)


def calendar_snapshot():
    key = Path('/etc/pf1007l-calendar/bridge-key').read_text().strip()
    connection = http.client.HTTPConnection('127.0.0.1', 5241, timeout=5)
    try:
        connection.request('GET', '/snapshot', headers={'X-Calendar-Key': key})
        response = connection.getresponse()
        if response.status != 200:
            raise RuntimeError('Calendar health failed')
        return json.loads(response.read(2097153))
    finally:
        connection.close()


def main():
    if os.geteuid() != 0 or ROOT.stat().st_uid != 0:
        raise RuntimeError('Use the root-owned frozen release')
    os.umask(0o077)
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    for name, digest in manifest.items():
        path = ROOT / name
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise RuntimeError('Release verification failed')
    for service in ('pf1007l-calendar', 'pf1007l-reminders-bridge', 'pf1007l-proxy-https'):
        command('systemctl', 'is-active', '--quiet', service)
    before = calendar_snapshot()
    if before.get('stale'):
        raise RuntimeError('Existing Calendar is stale; deployment not started')
    # Load only existing server-side credentials. Metadata discovery has no event reads.
    sys.path.insert(0, str(ROOT))
    from readonly_caldav import ReadonlyCalDAV
    from collector import selected
    account = json.loads(Path('/etc/pf1007l-calendar/apple.json').read_text())
    config = json.loads(CONFIG.read_text())
    original = selected(config)
    client = ReadonlyCalDAV(account['username'], account['appPassword'])
    discovered = client.discover()
    chosen = [dict(c) for c in original]
    for name in ('General', 'Appointments'):
        matches = [c for c in discovered if c['name'] == name]
        if len(matches) != 1:
            raise RuntimeError('Requested calendar identity is missing or ambiguous')
        found = matches[0]
        if any(c['href'] == found['href'] for c in chosen):
            continue
        identifier = 'calendar-' + hashlib.sha256(found['href'].encode()).hexdigest()[:16]
        chosen.append(dict(found, id=identifier, color=found.get('color') or '#3478F6'))
    by_href = {c['href']: c for c in discovered}
    for c in chosen:
        if c['href'] not in by_href:
            raise RuntimeError('Existing selected identity unavailable')
        metadata = by_href[c['href']]
        c['name'] = metadata['name']
        c['color'] = metadata.get('color') or c['color']
    if len(chosen) != 4 or not {'School', 'General', 'Appointments'} <= {c['name'] for c in chosen}:
        raise RuntimeError('Expected four-calendar selection not verified')
    config['selectedCalendars'] = chosen
    selected(config)
    # Verify the fixed task collection through read-only calls using an isolated DB.
    sys.path.insert(0, '/opt/pf1007l-reminders-bridge')
    import importlib.util
    spec = importlib.util.spec_from_file_location('candidate_bridge', ROOT / 'task_bridge.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    settings = json.loads(Path('/etc/pf1007l-reminders-bridge/settings.json').read_text())
    demo = json.loads(Path('/etc/pf1007l-reminders-demo/demo-account.json').read_text())
    registry_path = Path('/etc/pf1007l-reminders-bridge/device-registry.json')
    registry = json.loads(registry_path.read_text()) if settings.get('authMode') == 'device-v1' else None
    probe = module.Bridge(demo, settings, ':memory:', device_registry=registry)
    tasks_before = probe.snapshot(force=True)
    if tasks_before.get('stale') or tasks_before.get('list') != 'Do It':
        raise RuntimeError('Existing task collection name/sync not verified')
    backup = Path('/var/backups/pf1007l-sprint') / time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    backup.mkdir(parents=True, mode=0o700)
    files = [(CAL / 'collector.py', 'collector.py'), (CAL / 'readonly_caldav.py', 'readonly_caldav.py'),
             (BRIDGE, 'task_bridge.py'), (CONFIG, 'config.json')]
    for path, name in files:
        shutil.copy2(path, backup / name)
    # Consistent disaster-recovery snapshot only; normal rollback never rewinds it.
    state = sqlite3.connect('file:/var/lib/pf1007l-reminders-bridge/tasks.sqlite?mode=ro', uri=True)
    dest = sqlite3.connect(backup / 'tasks.sqlite');state.backup(dest);dest.close();state.close()
    shutil.copytree(UI, backup / 'ui')
    (backup / 'rollback.txt').write_text('Restore collector.py and readonly_caldav.py to ' + str(CAL) +
        '; task_bridge.py to ' + str(BRIDGE) + '; config.json to ' + str(CONFIG) +
        '; restore ui directory. Restart only pf1007l-calendar and pf1007l-reminders-bridge. '
        'Keep current task SQLite, Radicale data, credentials, registry, exact-IP guards. Never restore tasks.sqlite for normal rollback.\n')
    try:
        for name, target in [('collector.py', CAL / 'collector.py'), ('readonly_caldav.py', CAL / 'readonly_caldav.py'), ('task_bridge.py', BRIDGE)]:
            shutil.copyfile(ROOT / name, target);target.chmod(0o644)
        staged = CONFIG.with_suffix('.sprint-tmp')
        staged.write_text(json.dumps(config));staged.chmod(0o600);os.replace(staged, CONFIG)
        # Assets first, index last: existing readers never reference absent chunks.
        for path in sorted((ROOT / 'ui').rglob('*'), key=lambda p: p.name == 'index.html'):
            target = UI / path.relative_to(ROOT / 'ui')
            if path.is_dir():target.mkdir(exist_ok=True);target.chmod(0o755)
            else:shutil.copyfile(path,target);target.chmod(0o644)
        command('systemctl', 'restart', 'pf1007l-calendar', 'pf1007l-reminders-bridge')
        deadline = time.monotonic() + 150
        while True:
            try:
                after = calendar_snapshot()
                assert not after['stale'] and len(after['calendars']) == 4
                assert {'School','General','Appointments'} <= {c['name'] for c in after['calendars']}
                assert {c['id'] for c in original} <= {c['id'] for c in after['calendars']}
                break
            except Exception:
                if time.monotonic() >= deadline:raise RuntimeError('Calendar readiness failed') from None
                time.sleep(2)
        tasks_after = probe.snapshot(force=True)
        if tasks_after.get('stale') or tasks_after['items'] != tasks_before['items'] or tasks_after['list'] != 'Do It':
            raise RuntimeError('Task identity/state changed during deployment')
        command('systemctl', 'is-active', '--quiet', 'pf1007l-calendar', 'pf1007l-reminders-bridge', 'pf1007l-proxy-https', 'jellyfin', 'tailscaled')
        print('DEPLOYED: four calendars fresh; selected identities retained; Do It tasks unchanged; services healthy.')
        print('Private rollback backup: ' + str(backup))
    except Exception:
        for target, name in files:shutil.copy2(backup / name, target)
        # Overlay old UI; keep extra immutable assets harmlessly for existing clients.
        shutil.copytree(backup / 'ui', UI, dirs_exist_ok=True)
        command('systemctl', 'restart', 'pf1007l-calendar', 'pf1007l-reminders-bridge')
        print('Deployment failed; prior code/config/UI restored. Task history preserved.')
        raise RuntimeError('Deployment rolled back; inspect private backup') from None
    finally:
        probe.db.close()


if __name__ == '__main__':
    try:main()
    except Exception as error:
        # Avoid transport/library exception details containing personal content.
        print('STOPPED: ' + (str(error) if isinstance(error, RuntimeError) else 'Private deployment check failed'))
        sys.exit(1)
