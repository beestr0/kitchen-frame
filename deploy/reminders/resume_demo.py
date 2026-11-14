#!/usr/bin/env python3
"""Resume the installed pilot only; no pip, apt, credential rotation or unit edits."""
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import xml.etree.ElementTree as ET

import install_demo as pilot


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    require(os.geteuid() == 0 and os.isatty(0), 'Native SSH sudo TTY required')
    os.umask(0o077)
    import fcntl
    lock = open('/run/lock/pf1007l-reminders-demo-install.lock', 'a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    previous = Path('/root/pf1007l-reminders-install-failure.txt')
    locations = []
    if previous.exists():
        # Report code location only; never copy arbitrary private exception text.
        locations = re.findall(r'File "[^"\n]*/(install_demo\.py)", line (\d+)', previous.read_text())
    pilot.status('resume-authenticated', previousFailureCodeLocations=locations)
    for unit in [pilot.UNIT, 'pf1007l-proxy.service', 'pf1007l-proxy-https.service', 'jellyfin', 'tailscaled']:
        require(pilot.run(['systemctl', 'is-active', unit]).strip() == 'active', 'Existing service needs review')
    account = json.loads((pilot.ETC / 'demo-account.json').read_text())
    require(account.get('username') == pilot.USER, 'Unexpected demo account')
    password = account['password']
    path = '/' + pilot.USER + '/pf1007l-test/'
    require(pilot.request('PROPFIND', path, headers={'Depth': '0'})[0] == 401, 'Missing authentication not rejected')
    require(pilot.request('PROPFIND', path, 'incorrect-pilot-password', headers={'Depth': '0'})[0] == 401, 'Wrong authentication not rejected')
    propfind = b'''<D:propfind xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav"><D:prop><D:displayname/><D:resourcetype/><C:supported-calendar-component-set/></D:prop></D:propfind>'''
    code, _, body = pilot.request('PROPFIND', path, password, propfind, {'Depth': '0', 'Content-Type': 'application/xml'})
    require(code == 207, 'Existing collection unavailable')
    root = ET.fromstring(body)
    require(any(x.text == 'PF1007L Test' for x in root.iter('{DAV:}displayname')), 'Unexpected collection name')
    require(any(x.attrib.get('name') == 'VTODO' for x in root.iter('{urn:ietf:params:xml:ns:caldav}comp')), 'Collection does not advertise VTODO')
    pilot.status('existing-test-list-verified', previousFailureCodeLocations=locations)
    # Every probe gets its own fresh resource; do not recreate or edit existing tasks.
    uid = 'pf1007l-resume-probe-' + secrets.token_hex(8)
    target = path + uid + '.ics'
    data = ('BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//PF1007L Demo//EN\r\nBEGIN:VTODO\r\n'
            'UID:' + uid + '\r\nDTSTAMP:20261114T120000Z\r\nSUMMARY:Demo resume probe\r\n'
            'DUE;VALUE=DATE:20261115\r\nSTATUS:NEEDS-ACTION\r\nEND:VTODO\r\nEND:VCALENDAR\r\n').encode()
    require(pilot.request('PUT', target, password, data, {'Content-Type': 'text/calendar', 'If-None-Match': '*'})[0] == 201, 'New probe creation failed')
    code, headers, before = pilot.request('GET', target, password)
    require(code == 200 and headers.get('ETag'), 'Probe read failed')
    edited = before.replace(b'SUMMARY:Demo resume probe', b'SUMMARY:Demo edited probe')
    require(edited != before, 'Probe edit shaping failed')
    require(pilot.request('PUT', target, password, edited, {'Content-Type': 'text/calendar', 'If-Match': headers['ETag']})[0] in (201, 204), 'Conditional edit failed')
    _, headers, edited = pilot.request('GET', target, password)
    completed = edited.replace(b'STATUS:NEEDS-ACTION', b'STATUS:COMPLETED\r\nPERCENT-COMPLETE:100\r\nCOMPLETED:20261114T120000Z')
    require(completed != edited, 'Probe completion shaping failed')
    require(pilot.request('PUT', target, password, completed, {'Content-Type': 'text/calendar', 'If-Match': headers['ETag']})[0] in (201, 204), 'Conditional completion failed')
    require(pilot.request('PUT', target, password, edited, {'Content-Type': 'text/calendar', 'If-Match': headers['ETag']})[0] == 412, 'Stale edit was not rejected')
    _, _, final = pilot.request('GET', target, password)
    require(b'STATUS:COMPLETED' in final and b'DUE;VALUE=DATE:20261115' in final, 'Completion or due date was lost')
    pilot.status('dav-resume-tests-passed', demoDAVCreateEditComplete=True, stalePutRejected=True,
                 existingListPreserved=True, previousFailureCodeLocations=locations)
    state = json.loads(pilot.run(['tailscale', 'status', '--json']))
    hostname = state['Self']['DNSName'].rstrip('.')
    require(hostname == 'hub-inspiron-5570.tailb76e1b.ts.net', 'Unexpected tailnet hostname')
    serve = json.loads(pilot.run(['tailscale', 'serve', 'status', '--json']))
    require(not any(serve.get('AllowFunnel', {}).values()), 'Funnel must not be enabled')
    if serve:
        # Reuse only the exact pilot mapping. Never reset/replace another mapping.
        expected = serve.get('Web', {}).get(hostname + ':443', {}).get('Handlers', {}).get('/', {})
        require(expected.get('Proxy') == 'http://127.0.0.1:5238', 'Existing Serve mapping requires review')
    else:
        pilot.status('awaiting-native-tailnet-https-setup', demoDAVCreateEditComplete=True,
                     stalePutRejected=True, existingListPreserved=True)
        print('Authorize HTTPS/Serve only if Tailscale displays a link below. Do not enable Funnel.', flush=True)
        subprocess.run(['tailscale', 'serve', '--bg', '--https=443', 'http://127.0.0.1:5238'], check=True)
    serve = json.loads(pilot.run(['tailscale', 'serve', 'status', '--json']))
    require(not any(serve.get('AllowFunnel', {}).values()), 'Unexpected Funnel configuration')
    # Same-host checks must bind the client to tailscale0, preserving Serve's
    # ingress restriction and normal CA/hostname validation.
    import verify_https
    verify_https.main()
    print('PF1007L_PRIVATE_HTTPS_VERIFIED. Ready for iPhone account setup.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # All RuntimeError messages above are fixed strings. Other exception text
        # may contain private endpoint/auth details and stays in root-private logs.
        import traceback
        log = Path('/root/pf1007l-reminders-resume-failure.txt')
        log.write_text(traceback.format_exc())
        log.chmod(0o600)
        safe = str(error) if type(error) is RuntimeError else 'Private diagnostics retained on Mint'
        pilot.status('resume-failed', error=safe, exceptionType=type(error).__name__)
        print('Resume stopped: ' + safe, file=sys.stderr)
        sys.exit(1)
