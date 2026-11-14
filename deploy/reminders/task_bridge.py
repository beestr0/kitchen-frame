#!/usr/bin/env python3
"""Demo-only, fixed-collection task adapter. No create/delete or arbitrary DAV path API."""
import base64
from datetime import date, datetime, timezone
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import sqlite3
import threading
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

import vobject
from dateutil.tz import tzutc

COLLECTION = '/pf1007l-demo/pf1007l-test/'
ORIGIN = 'https://beestr0.duckdns.org:8789'
ZONE = ZoneInfo('America/Indiana/Indianapolis')
PREFIX = '/__reminders-demo/'
QUERY = b'''<C:calendar-query xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav"><D:prop><D:getetag/><C:calendar-data/></D:prop><C:filter><C:comp-filter name="VCALENDAR"><C:comp-filter name="VTODO"/></C:comp-filter></C:filter></C:calendar-query>'''


class TaskError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


def due_value(value):
    if isinstance(value, datetime):
        if value.tzinfo is None:
            aware = value.replace(tzinfo=ZONE)
            if aware.astimezone(timezone.utc).astimezone(ZONE).replace(tzinfo=None) != value:
                raise TaskError(503, 'Reminder has an invalid floating local time')
            value = aware
        return {'day': value.astimezone(ZONE).date().isoformat(),
                'at': value.astimezone(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')}
    if isinstance(value, date):
        return {'day': value.isoformat()}
    raise TaskError(503, 'Unsupported reminder due date')


def parse_task(text):
    if len(text.encode()) > 262144:
        raise TaskError(503, 'Reminder resource too large')
    root = vobject.readOne(text)
    tasks = root.contents.get('vtodo', [])
    if root.name != 'VCALENDAR' or not tasks or root.contents.get('vevent'):
        raise TaskError(503, 'Invalid VTODO resource')
    # Preserve resources with recurrence exceptions, but don't guess instance writes.
    task = next((x for x in tasks if 'recurrence-id' not in x.contents), tasks[0])
    if not hasattr(task, 'uid') or not str(task.uid.value):
        raise TaskError(503, 'Reminder identity missing')
    recurring = len(tasks) > 1 or any(k in task.contents for k in ('rrule', 'rdate', 'recurrence-id'))
    status = str(task.status.value).upper() if hasattr(task, 'status') else 'NEEDS-ACTION'
    return root, task, {'title': str(task.summary.value)[:500] if hasattr(task, 'summary') else '(Untitled reminder)',
                        'due': due_value(task.due.value) if hasattr(task, 'due') else None,
                        'completed': status == 'COMPLETED' or hasattr(task, 'completed'),
                        'cancelled': status == 'CANCELLED', 'recurring': recurring}


class Bridge:
    def __init__(self, account, settings, database):
        if account.get('username') != 'pf1007l-demo':
            raise RuntimeError('Dedicated demo account required')
        self.account, self.settings = account, settings
        self.db = sqlite3.connect(database, check_same_thread=False)
        self.db.execute('CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS operations (key TEXT PRIMARY KEY, task TEXT, version TEXT, result TEXT)')
        self.db.commit()
        self.lock = threading.RLock()
        self.attempt = 0
        self.auth_failed = False
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def load(self, key, default=None):
        row = self.db.execute('SELECT value FROM state WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def save(self, key, value):
        self.db.execute('INSERT OR REPLACE INTO state VALUES (?,?)', (key, json.dumps(value)))
        self.db.commit()

    def opaque(self, value):
        return hmac.new(self.settings['apiKey'].encode(), value.encode(), hashlib.sha256).hexdigest()

    def dav(self, method, path, body=None, etag=None):
        if method not in ('REPORT', 'GET', 'PUT') or not path.startswith(COLLECTION) or '?' in path or '#' in path or '\\' in path or '..' in path or '//' in path:
            raise TaskError(403, 'Task route denied')
        auth = base64.b64encode((self.account['username'] + ':' + self.account['password']).encode()).decode()
        headers = {'Authorization': 'Basic ' + auth, 'Depth': '1' if method == 'REPORT' else '0',
                   'Content-Type': 'text/calendar; charset=utf-8' if method == 'PUT' else 'application/xml',
                   'User-Agent': 'PF1007L-disposable-task-bridge/1'}
        if etag:
            headers['If-Match'] = etag
        request = urllib.request.Request('http://127.0.0.1:5238' + path, data=body, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=10) as response:
                data = response.read(2097153)
                if len(data) > 2097152:
                    raise TaskError(503, 'Task response too large')
                return response.status, response.headers, data
        except urllib.error.HTTPError as error:
            code = error.code; error.close()
            if code in (401, 403):
                self.auth_failed = True
            raise TaskError(409 if code == 412 else 503, 'Task changed; refresh before retrying' if code == 412 else 'Task service unavailable') from None
        except (urllib.error.URLError, OSError):
            raise TaskError(503, 'Task service unavailable') from None

    def snapshot(self, force=False):
        cached = self.load('snapshot', {'items': [], 'lastSuccess': None, 'stale': True})
        if self.auth_failed:
            return {**cached, 'stale': True, 'error': 'Demo account authorization needs attention'}
        if not force and time.monotonic() - self.attempt < 15:
            return cached
        self.attempt = time.monotonic()
        try:
            _, _, data = self.dav('REPORT', COLLECTION, QUERY)
            if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
                raise TaskError(503, 'Invalid task response')
            root = ET.fromstring(data)
            if root.tag != '{DAV:}multistatus':
                raise TaskError(503, 'Invalid task response')
            items, resources, seen = [], {}, set()
            for response in root.findall('{DAV:}response'):
                props = {}
                for stat in response.findall('{DAV:}propstat'):
                    if ' 200 ' in stat.findtext('{DAV:}status', ''):
                        prop = stat.find('{DAV:}prop')
                        if prop is not None:
                            props.update({x.tag: x.text for x in prop})
                href = response.findtext('{DAV:}href', '')
                text, etag = props.get('{urn:ietf:params:xml:ns:caldav}calendar-data'), props.get('{DAV:}getetag')
                if not href.startswith(COLLECTION) or not href.endswith('.ics') or text is None or not etag:
                    raise TaskError(503, 'Incomplete task response')
                _, task, item = parse_task(text)
                uid = str(task.uid.value)
                identifier = self.opaque(COLLECTION + '\0' + uid)
                if identifier in seen:
                    raise TaskError(503, 'Duplicate task identity')
                seen.add(identifier)
                version = self.opaque(etag)
                items.append({**item, 'id': identifier, 'uid': identifier, 'listId': 'pf1007l-test',
                              'version': version, 'canComplete': not item['recurring']})
                resources[identifier] = {'href': href, 'uid': uid, 'etag': etag, 'version': version}
                if len(items) > 500:
                    raise TaskError(503, 'Demo collection item limit exceeded')
            snapshot = {'items': items, 'lastSuccess': datetime.now(timezone.utc).isoformat(), 'stale': False,
                        'list': 'PF1007L Test', 'timezone': str(ZONE)}
            # All-or-nothing publication: a failed collection read never deletes items.
            self.save('resources', resources)
            self.save('snapshot', snapshot)
            return snapshot
        except Exception:
            stale = {**cached, 'stale': True, 'error': 'Could not refresh demo reminders; last good data retained'}
            self.save('snapshot', stale)
            return stale

    def complete(self, identifier, version, key):
        if not re.fullmatch(r'[a-f0-9]{64}', identifier) or not re.fullmatch(r'[A-Za-z0-9-]{16,80}', key):
            raise TaskError(400, 'Invalid completion request')
        prior = self.db.execute('SELECT task,version,result FROM operations WHERE key=?', (key,)).fetchone()
        if prior and (prior[0] != identifier or prior[1] != version):
            raise TaskError(409, 'Completion key reused for different task')
        if prior and prior[2] == 'done':
            return {'completed': True}
        resource = self.load('resources', {}).get(identifier)
        if not resource or resource['version'] != version:
            raise TaskError(409, 'Task changed; refresh before retrying')
        _, headers, data = self.dav('GET', resource['href'])
        root, task, item = parse_task(data.decode())
        if str(task.uid.value) != resource['uid'] or item['recurring'] or item['cancelled']:
            raise TaskError(409, 'Complete recurring or changed reminders on iPhone')
        if item['completed']:
            self.db.execute('INSERT OR REPLACE INTO operations VALUES (?,?,?,?)', (key, identifier, version, 'done')); self.db.commit()
            return {'completed': True}
        if headers.get('ETag') != resource['etag']:
            raise TaskError(409, 'Task changed; refresh before retrying')
        self.db.execute('INSERT OR IGNORE INTO operations VALUES (?,?,?,?)', (key, identifier, version, 'pending')); self.db.commit()
        # vobject's serializer recognizes its dateutil UTC singleton; stdlib UTC
        # is not accepted by the installed serializer's TZID registry.
        stamp = datetime.now(tzutc())
        for name, value in [('status', 'COMPLETED'), ('percent-complete', '100'), ('completed', stamp), ('dtstamp', stamp), ('last-modified', stamp)]:
            if not hasattr(task, name.replace('-', '_')) and name not in task.contents:
                task.add(name)
            task.contents[name][0].value = value
        if 'sequence' not in task.contents:
            task.add('sequence').value = '0'
        task.sequence.value = str(int(task.sequence.value) + 1)
        self.dav('PUT', resource['href'], root.serialize().encode(), resource['etag'])
        self.db.execute('UPDATE operations SET result=? WHERE key=?', ('done', key)); self.db.commit()
        self.snapshot(force=True)
        return {'completed': True}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def handler(bridge):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def response(self, code, value, cookie=False):
            data = json.dumps(value).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(data)))
            if cookie:
                self.send_header('Set-Cookie', 'pf1007l-demo=' + bridge.settings['session'] + '; Path=' + PREFIX + '; Secure; HttpOnly; SameSite=Strict; Max-Age=86400')
            self.end_headers(); self.wfile.write(data)

        def process(self):
            if not hmac.compare_digest(self.headers.get('X-Pilot-Key', ''), bridge.settings['apiKey']):
                raise TaskError(403, 'Demo bridge access denied')
            if self.headers.get('X-Pilot-Client') != bridge.settings['frameIP']:
                raise TaskError(403, 'Demo frame access denied')
            if self.headers.get('Origin') not in (None, ORIGIN):
                raise TaskError(403, 'Origin denied')
            authenticated = ('pf1007l-demo=' + bridge.settings['session']) in self.headers.get('Cookie', '').split('; ')
            route = self.path
            if route == PREFIX + 'session' and self.command == 'GET':
                if not authenticated and bridge.load('provisioned', False):
                    raise TaskError(403, 'Demo frame session needs local reprovisioning')
                bridge.save('provisioned', True)
                self.response(200, {'demo': True, 'csrf': bridge.settings['csrf']}, cookie=True); return
            if not authenticated:
                raise TaskError(401, 'Demo frame session required')
            if route == PREFIX + 'snapshot' and self.command == 'GET':
                self.response(200, bridge.snapshot()); return
            if route == PREFIX + 'complete' and self.command == 'POST':
                if self.headers.get('Origin') != ORIGIN or not hmac.compare_digest(self.headers.get('X-Pilot-CSRF', ''), bridge.settings['csrf']):
                    raise TaskError(403, 'Completion origin or token denied')
                if self.headers.get('Content-Type') != 'application/json':
                    raise TaskError(415, 'JSON required')
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 2048:
                    raise TaskError(413, 'Completion body limit')
                value = json.loads(self.rfile.read(length))
                result = bridge.complete(str(value.get('id', '')), str(value.get('version', '')), str(value.get('operation', '')))
                self.response(200, result); return
            raise TaskError(404, 'Demo route unavailable')

        def do_GET(self):
            try:
                with bridge.lock:
                    self.process()
            except TaskError as error:
                self.response(error.status, {'error': error.message})
            except Exception:
                self.response(503, {'error': 'Demo task operation unavailable'})

        do_POST = do_GET
    return Handler


if __name__ == '__main__':
    credentials = Path(os.environ['CREDENTIALS_DIRECTORY'])
    account = json.loads((credentials / 'demo-account').read_text())
    settings = json.loads((credentials / 'bridge-settings').read_text())
    state = Path(os.environ['STATE_DIRECTORY'])
    bridge = Bridge(account, settings, state / 'tasks.sqlite')
    ThreadingHTTPServer(('127.0.0.1', 5240), handler(bridge)).serve_forever()
