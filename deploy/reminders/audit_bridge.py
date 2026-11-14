"""Real demo-only bridge access, conflict and restart checks; no existing task edits."""
import http.client
import json
from pathlib import Path
import secrets
import subprocess
import time
import xml.etree.ElementTree as ET
from install_demo import request, BASE


def execute(stage):
    settings = json.loads(Path('/etc/pf1007l-reminders-bridge/settings.json').read_text())
    account = json.loads(Path('/etc/pf1007l-reminders-demo/demo-account.json').read_text())
    path = '/pf1007l-demo/pf1007l-test/'
    def api(route, body=None, overrides=None):
        headers = {'X-Pilot-Key': settings['apiKey'], 'X-Pilot-Client': settings['frameIP'],
                   'Cookie': 'pf1007l-demo=' + settings['session'], 'Origin': 'https://beestr0.duckdns.org:8789',
                   'X-Pilot-CSRF': settings['csrf'], 'Content-Type': 'application/json'}
        headers.update(overrides or {})
        connection = http.client.HTTPConnection('127.0.0.1', 5240, timeout=15)
        connection.request('POST' if body is not None else 'GET', '/__reminders-demo/' + route,
                           json.dumps(body).encode() if body is not None else None, headers)
        response = connection.getresponse(); data = json.loads(response.read()); connection.close()
        return response.status, data
    assert api('snapshot', overrides={'X-Pilot-Key': ''})[0] == 403
    assert api('snapshot', overrides={'Cookie': ''})[0] == 401
    assert api('snapshot', overrides={'X-Pilot-Client': '10.157.1.250'})[0] == 403
    assert api('complete', {}, {'X-Pilot-CSRF': ''})[0] == 403
    assert api('complete', {}, {'Origin': 'https://unrelated.example'})[0] == 403
    def ics(uid, title):
        return ('BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//PF1007L Pilot//EN\r\nBEGIN:VTODO\r\nUID:' + uid + '\r\nDTSTAMP:20261114T120000Z\r\nSUMMARY:' + title + '\r\nSTATUS:NEEDS-ACTION\r\nEND:VTODO\r\nEND:VCALENDAR\r\n').encode()
    undated_path = path + 'pf1007l-undated-pilot.ics'
    status = request('PUT', undated_path, account['password'], ics('pf1007l-undated-pilot', 'Undated dashboard pilot'), {'Content-Type': 'text/calendar', 'If-None-Match': '*'})[0]
    assert status in (201, 412)
    uid = 'pf1007l-conflict-probe-' + secrets.token_hex(6)
    probe_path = path + uid + '.ics'
    assert request('PUT', probe_path, account['password'], ics(uid, 'Demo conflict probe'), {'Content-Type': 'text/calendar', 'If-None-Match': '*'})[0] == 201
    time.sleep(16) # Honor the adapter's bounded refresh cadence.
    status, snapshot = api('snapshot'); assert status == 200 and not snapshot['stale']
    probe = next(x for x in snapshot['items'] if x['title'] == 'Demo conflict probe')
    _, headers, raw = request('GET', probe_path, account['password'])
    edited = raw.replace(b'SUMMARY:Demo conflict probe', b'SUMMARY:Demo concurrent edit preserved')
    assert request('PUT', probe_path, account['password'], edited, {'Content-Type': 'text/calendar', 'If-Match': headers['ETag']})[0] == 204
    status, _ = api('complete', {'id': probe['id'], 'version': probe['version'], 'operation': 'conflict-probe-' + secrets.token_hex(10)})
    assert status == 409
    _, headers, raw = request('GET', probe_path, account['password'])
    assert b'SUMMARY:Demo concurrent edit preserved' in raw and b'STATUS:NEEDS-ACTION' in raw
    # Retire only the newly-created probe by completing it, retaining its history.
    completed = raw.replace(b'STATUS:NEEDS-ACTION', b'STATUS:COMPLETED\r\nPERCENT-COMPLETE:100\r\nCOMPLETED:20261114T120000Z')
    assert request('PUT', probe_path, account['password'], completed, {'Content-Type': 'text/calendar', 'If-Match': headers['ETag']})[0] == 204
    subprocess.run(['systemctl', 'restart', 'pf1007l-reminders-bridge.service'], check=True)
    for _ in range(20):
        try:
            status, after = api('snapshot')
            if status == 200 and not after['stale']: break
        except OSError: pass
        time.sleep(1)
    else: raise RuntimeError('Bridge restart recovery failed')
    prior = {x['id'] for x in snapshot['items'] if x['id'] != probe['id']}
    assert prior.issubset({x['id'] for x in after['items']})
    resources = subprocess.run(['systemctl', 'show', 'pf1007l-reminders-bridge.service', '-p', 'MemoryCurrent', '-p', 'CPUUsageNSec'], check=True, capture_output=True, text=True).stdout.splitlines()
    return {'bridgeAuthentication': True, 'frameCookie': True, 'csrf': True, 'origin': True,
            'unapprovedFrameDenied': True, 'staleWrite409': True, 'concurrentEditPreserved': True,
            'restartRecoveredSameIDs': True, 'undatedDemoAvailable': any(x['title'] == 'Undated dashboard pilot' and not x['completed'] for x in after['items']),
            'resources': resources}
