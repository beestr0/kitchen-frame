#!/usr/bin/env python3
"""Approved demo-only Mint installer. Run via sudo in a private native SSH TTY."""
import base64
import fcntl
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

STAGE = Path(__file__).resolve().parent
ROOT = Path('/opt/pf1007l-reminders-demo')
ETC = Path('/etc/pf1007l-reminders-demo')
UNIT = 'pf1007l-reminders-demo.service'
BASE = 'http://127.0.0.1:5238'
USER = 'pf1007l-demo'


def run(args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


def status(phase, **fields):
    report = STAGE / 'pilot-status.json'
    temporary = STAGE / '.pilot-status.new'
    temporary.write_text(json.dumps({'phase': phase, **fields}, indent=2))
    temporary.chmod(0o644)
    temporary.replace(report)
    print('PF1007L_DEMO_PHASE: ' + phase, flush=True)


def request(method, path, password=None, body=b'', headers=None, base=BASE):
    fields = dict(headers or {})
    if password:
        fields['Authorization'] = 'Basic ' + base64.b64encode((USER + ':' + password).encode()).decode()
    req = urllib.request.Request(base + path, data=body if body else None, method=method, headers=fields)
    # No environment proxy inheritance. This is a same-host loopback hop only.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=15) as response:
            return response.status, response.headers, response.read(2 * 1024 * 1024)
    except urllib.error.HTTPError as error:
        with error:
            return error.code, error.headers, error.read(2 * 1024 * 1024)


def main():
    if sys.platform != 'linux' or os.geteuid() != 0 or not os.isatty(0):
        raise ValueError('Private native SSH sudo Terminal required')
    os.umask(0o077)
    lock = open('/run/lock/pf1007l-reminders-demo-install.lock', 'a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    status('preflight')
    for service in ['pf1007l-proxy.service', 'pf1007l-proxy-https.service', 'jellyfin', 'tailscaled']:
        if run(['systemctl', 'is-active', service]).strip() != 'active':
            raise ValueError('Existing service baseline requires review')
    # Never take over an existing installation belonging to another task.
    marker = ROOT / 'pf1007l-demo-only'
    if ROOT.exists() and not marker.exists():
        raise ValueError('Existing unmarked project directory preserved')
    if not ROOT.exists():
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 5238))
        ROOT.mkdir(mode=0o755)
        marker.write_text('Dedicated disposable Reminders pilot, not iCloud\n')
        marker.chmod(0o644)
    ROOT.chmod(0o755)
    # Guard the reviewed dependency addition against removals/upgrades.
    if not Path('/usr/lib/python3.12/ensurepip').is_dir():
        apt = ['apt-get', '--no-install-recommends', '--no-upgrade', '--no-remove', 'install', 'python3.12-venv']
        simulation = run([apt[0], '-s', *apt[1:]])
        if '0 upgraded,' not in simulation or '0 to remove' not in simulation:
            raise ValueError('Dependency plan changed; existing packages preserved')
        run([apt[0], '-y', *apt[1:]])
    status('installing-isolated-runtime')
    python = str(ROOT / 'venv/bin/python')
    previous_mask = os.umask(0o022)
    try:
        # Runtime code must be readable/executable by DynamicUser; credentials are
        # created only after restoring 0077 below.
        if not (ROOT / 'venv/bin/python').exists():
            run(['python3', '-m', 'venv', str(ROOT / 'venv')])
        run([python, '-m', 'pip', '--disable-pip-version-check', 'install', 'Radicale==3.9.1', 'bcrypt==5.0.0'])
    finally:
        os.umask(previous_mask)
    freeze = run([python, '-m', 'pip', 'freeze'])
    (ROOT / 'requirements.installed.txt').write_text(freeze)
    (ROOT / 'requirements.installed.txt').chmod(0o644)
    ETC.mkdir(mode=0o700, exist_ok=True)
    if ETC.is_symlink() or ETC.stat().st_uid != 0 or ETC.stat().st_mode & 0o077:
        raise ValueError('Private configuration directory requires review')
    credential = ETC / 'demo-account.json'
    if credential.exists():
        account = json.loads(credential.read_text())
        if account['username'] != USER:
            raise ValueError('Existing account preserved')
        password = account['password']
    else:
        password = secrets.token_urlsafe(32)
        with credential.open('x') as stream:
            json.dump({'username': USER, 'password': password}, stream)
        credential.chmod(0o600)
    users = ETC / 'users'
    if not users.exists():
        # Password travels over a private pipe, never shell args or environment.
        code = 'import bcrypt,sys; print(bcrypt.hashpw(sys.stdin.buffer.read(),bcrypt.gensalt(rounds=12)).decode())'
        hashed = subprocess.run([python, '-c', code], input=password, text=True, capture_output=True, check=True).stdout.strip()
        with users.open('x') as stream:
            stream.write(USER + ':' + hashed + '\n')
        users.chmod(0o600)
    config = (STAGE / 'radicale-demo.conf.example').read_text()
    (ETC / 'config').write_text(config)
    (ETC / 'config').chmod(0o600)
    unit = Path('/etc/systemd/system') / UNIT
    expected = (STAGE / UNIT).read_bytes()
    if unit.exists() and unit.read_bytes() != expected:
        raise ValueError('Existing differing unit preserved')
    unit.write_bytes(expected)
    unit.chmod(0o644)
    run(['systemd-analyze', 'verify', str(unit)])
    run(['systemctl', 'daemon-reload'])
    state = subprocess.run(['systemctl', 'is-failed', UNIT], capture_output=True, text=True)
    if state.stdout.strip() == 'failed':
        run(['systemctl', 'reset-failed', UNIT])
    status('starting-loopback-service')
    run(['systemctl', 'enable', '--now', UNIT])
    for _ in range(30):
        try:
            if request('PROPFIND', '/', headers={'Depth': '0'})[0] == 401:
                break
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(1)
    else:
        raise ValueError('Pilot listener not ready')
    assert request('PROPFIND', '/', 'wrong-demo-password', headers={'Depth': '0'})[0] == 401
    assert request('PROPFIND', '/' + USER + '/', password, headers={'Depth': '0'})[0] == 207
    assert request('PROPFIND', '/another-user/', password, headers={'Depth': '0'})[0] in (403, 404)
    path = '/' + USER + '/pf1007l-test/'
    prop = b'''<?xml version="1.0" encoding="utf-8"?>
<C:mkcalendar xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav"><D:set><D:prop>
<D:displayname>PF1007L Test</D:displayname>
<C:supported-calendar-component-set><C:comp name="VTODO"/></C:supported-calendar-component-set>
</D:prop></D:set></C:mkcalendar>'''
    code = request('MKCALENDAR', path, password, prop, {'Content-Type': 'application/xml'})[0]
    assert code in (201, 405), 'Demo collection setup failed'
    # Fixed dedicated test resource; never modify unknown existing objects.
    object_path = path + 'pf1007l-demo-undated.ics'
    data = ('BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//PF1007L Pilot//EN\r\nBEGIN:VTODO\r\n'
            'UID:pf1007l-demo-undated\r\nDTSTAMP:20261114T120000Z\r\nSUMMARY:Demo - verify Reminders sync\r\n'
            'STATUS:NEEDS-ACTION\r\nEND:VTODO\r\nEND:VCALENDAR\r\n').encode()
    code = request('PUT', object_path, password, data, {'Content-Type': 'text/calendar', 'If-None-Match': '*'})[0]
    assert code in (201, 412), 'Demo task setup failed'
    code, headers, body = request('GET', object_path, password)
    assert code == 200 and headers.get('ETag'), 'Demo task unavailable'
    # A stale revision must be rejected, leaving the original data unchanged.
    assert request('PUT', object_path, password, data, {'Content-Type': 'text/calendar', 'If-Match': '"obsolete-demo-revision"'})[0] == 412
    assert request('GET', object_path, password)[2] == body
    # A fresh disposable probe avoids touching any item the phone may have edited.
    probe_id = 'pf1007l-probe-' + secrets.token_hex(6)
    probe_path = path + probe_id + '.ics'
    probe = data.replace(b'UID:pf1007l-demo-undated', ('UID:' + probe_id).encode())
    assert request('PUT', probe_path, password, probe, {'Content-Type': 'text/calendar', 'If-None-Match': '*'})[0] == 201
    _, probe_headers, probe_body = request('GET', probe_path, password)
    edited = probe_body.replace(b'SUMMARY:Demo - verify Reminders sync', b'SUMMARY:Demo - edited through DAV')
    assert edited != probe_body
    assert request('PUT', probe_path, password, edited, {'Content-Type': 'text/calendar', 'If-Match': probe_headers['ETag']})[0] == 204
    _, edited_headers, edited_body = request('GET', probe_path, password)
    assert b'SUMMARY:Demo - edited through DAV' in edited_body
    completed = edited_body.replace(b'STATUS:NEEDS-ACTION', b'STATUS:COMPLETED\r\nPERCENT-COMPLETE:100\r\nCOMPLETED:20261114T120000Z')
    assert completed != edited_body
    assert request('PUT', probe_path, password, completed, {'Content-Type': 'text/calendar', 'If-Match': edited_headers['ETag']})[0] == 204
    assert b'STATUS:COMPLETED' in request('GET', probe_path, password)[2]
    assert request('PUT', probe_path, password, edited, {'Content-Type': 'text/calendar', 'If-Match': edited_headers['ETag']})[0] == 412
    assert b'STATUS:COMPLETED' in request('GET', probe_path, password)[2]
    for service in ['pf1007l-proxy.service', 'pf1007l-proxy-https.service', 'jellyfin', 'tailscaled']:
        assert run(['systemctl', 'is-active', service]).strip() == 'active'
    measurements = run(['systemctl', 'show', UNIT, '-p', 'MemoryCurrent', '-p', 'CPUUsageNSec', '-p', 'TasksCurrent'])
    status('loopback-demo-ready', authentication='required', collection='PF1007L Test',
           stalePutRejected=True, packageVersions=freeze.splitlines(), resources=measurements.splitlines(),
           demoDAVCreateEditComplete=True,
           remoteHTTPS='not-configured', iphone='not-configured')
    print('Loopback pilot ready. No public or tailnet listener was added.', flush=True)
    if '--configure-tailnet' in sys.argv:
        serve = json.loads(run(['tailscale', 'serve', 'status', '--json']))
        if serve:
            raise ValueError('Existing Serve configuration preserved; review additive mapping manually')
        status('awaiting-native-tailnet-https-setup', demoDAVCreateEditComplete=True)
        print('If Tailscale prints an authorization link, open it privately to enable tailnet HTTPS/Serve only. Never enable Funnel.', flush=True)
        subprocess.run(['tailscale', 'serve', '--bg', '--https=443', 'http://127.0.0.1:5238'], check=True)
        serve = json.loads(run(['tailscale', 'serve', 'status', '--json']))
        if any(serve.get('AllowFunnel', {}).values()):
            raise ValueError('Unexpected Funnel configuration; do not use the endpoint')
        state = json.loads(run(['tailscale', 'status', '--json']))
        hostname = state['Self']['DNSName'].rstrip('.')
        if hostname != 'hub-inspiron-5570.tailb76e1b.ts.net':
            raise ValueError('Unexpected tailnet hostname')
        import verify_https
        verify_https.main()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Child output can contain private paths; retain it only on Mint.
        import traceback
        failure = Path('/root/pf1007l-reminders-install-failure.txt')
        failure.write_text(traceback.format_exc())
        failure.chmod(0o600)
        status('failed', error='Details retained in root-private Mint diagnostics')
        print('Installation stopped; existing services were not restarted. Root-private diagnostics retained.', file=sys.stderr)
        sys.exit(1)
