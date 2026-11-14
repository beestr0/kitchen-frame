#!/usr/bin/env python3
"""One-hour read-only demo observer. Run checksum-verified in a native sudo TTY.

Outputs only aggregate session metadata and synthetic `Cellular pilot ` reminders.
Never emits credentials, raw UIDs, cookies, headers, proofs or arbitrary task titles.
"""
import base64
from datetime import datetime, timezone
import hashlib
import http.client
import json
import os
from pathlib import Path
import sqlite3
import time
import xml.etree.ElementTree as ET

PREFIX = 'Cellular pilot '
COLLECTION = '/pf1007l-demo/pf1007l-test/'
QUERY = b'''<C:calendar-query xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav"><D:prop><C:calendar-data/></D:prop><C:filter><C:comp-filter name="VCALENDAR"><C:comp-filter name="VTODO"/></C:comp-filter></C:filter></C:calendar-query>'''


def project_calendar(data):
    import vobject
    result = []
    for element in ET.fromstring(data).iter('{urn:ietf:params:xml:ns:caldav}calendar-data'):
        for task in vobject.readOne(element.text).contents.get('vtodo', []):
            title = str(task.summary.value) if hasattr(task, 'summary') else ''
            if not title.startswith(PREFIX):
                continue
            # Only our fixed synthetic labels, never arbitrary suffixes.
            if title not in {PREFIX + label for label in ('WiFi 01', 'Cellular 01', 'Siri 01', 'Reconnect 01', 'Locked 01')}:
                continue
            due = task.due.value.isoformat() if hasattr(task, 'due') else None
            result.append({'title': title, 'uidHash': hashlib.sha256(str(task.uid.value).encode()).hexdigest(),
                           'due': due, 'completed': hasattr(task, 'completed') or
                           (hasattr(task, 'status') and str(task.status.value).upper() == 'COMPLETED')})
    return result


def observe():
    now = time.time()
    with sqlite3.connect('file:/var/lib/pf1007l-reminders-bridge/tasks.sqlite?mode=ro', uri=True, timeout=5) as db:
        issued, expires = db.execute('SELECT MAX(issued),MAX(expires) FROM device_sessions').fetchone()
        active = db.execute('SELECT COUNT(*) FROM device_keys WHERE active=1').fetchone()[0]
        row = db.execute("SELECT value FROM state WHERE key='snapshot'").fetchone()
        snapshot = json.loads(row[0]) if row else {}
    account = json.loads(Path('/etc/pf1007l-reminders-demo/demo-account.json').read_text())
    if account.get('username') != 'pf1007l-demo':
        raise ValueError('Unexpected account')
    authorization = base64.b64encode(('pf1007l-demo:' + account['password']).encode()).decode()
    conn = http.client.HTTPConnection('127.0.0.1', 5238, timeout=10)
    try:
        conn.request('REPORT', COLLECTION, QUERY, {'Authorization': 'Basic ' + authorization,
                     'Content-Type': 'application/xml', 'Depth': '1'})
        response = conn.getresponse()
        if response.status != 207:
            raise ValueError('DAV query failed')
        raw = response.read(2097153)
        if len(raw) > 2097152:
            raise ValueError('DAV query too large')
        tasks = project_calendar(raw)
    finally:
        conn.close()
    titles = {task['title'] for task in tasks}
    return {'observedUTC': datetime.now(timezone.utc).isoformat(), 'observedUnix': now,
            'sessions': {'latestIssuedUnix': issued, 'latestExpiryUnix': expires,
                         'unexpired': bool(expires and expires > now), 'activeDevices': active},
            'radicale': tasks,
            'bridge': {'lastSuccess': snapshot.get('lastSuccess'), 'stale': snapshot.get('stale'),
                       'tasks': [{key: task.get(key) for key in ('id', 'title', 'due', 'completed')}
                                 for task in snapshot.get('items', []) if task.get('title') in titles]}}


def main():
    if os.geteuid() != 0 or not os.isatty(0):
        raise SystemExit('Use a checksum-verified helper in a private native sudo Terminal')
    os.umask(0o077)
    deadline = time.monotonic() + 3600
    print('PF1007L read-only observer active; no service changes or task writes.', flush=True)
    while time.monotonic() < deadline:
        try:
            print(json.dumps(observe()), flush=True)
        except Exception:
            # Exception text can contain transport/authentication details.
            print(json.dumps({'observedUTC': datetime.now(timezone.utc).isoformat(),
                              'observationFailed': True}), flush=True)
        time.sleep(5)


if __name__ == '__main__':
    main()
