from datetime import date, datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from task_bridge import Bridge, TaskError, due_value, parse_task, COLLECTION


def fixture(extra='', title='Demo'):
    return '\r\n'.join(['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Test//EN', 'BEGIN:VTODO', 'UID:demo',
                          'SUMMARY:' + title, 'DUE;VALUE=DATE:20261114', 'STATUS:NEEDS-ACTION',
                          'X-DEMO:preserve', extra, 'END:VTODO', 'END:VCALENDAR'])


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.bridge = Bridge({'username': 'pf1007l-demo', 'password': 'invented'},
                             {'apiKey': 'invented-test-key'}, Path(self.temp.name) / 'state.sqlite')
        self.identifier = self.bridge.opaque(COLLECTION + '\0demo')
        self.etag = '"one"'
        self.version = self.bridge.opaque(self.etag)
        self.bridge.save('resources', {self.identifier: {'href': COLLECTION + 'one.ics', 'uid': 'demo', 'etag': self.etag, 'version': self.version}})

    def tearDown(self):
        self.bridge.db.close(); self.temp.cleanup()

    def test_dates_and_floating_dst(self):
        self.assertEqual(due_value(date(2026, 11, 14)), {'day': '2026-11-14'})
        self.assertEqual(due_value(datetime(2026, 11, 14, 2, tzinfo=timezone.utc))['day'], '2026-11-13')
        self.assertEqual(due_value(datetime(2026, 11, 14, 9))['at'], '2026-11-14T14:00:00Z')
        with self.assertRaises(TaskError): due_value(datetime(2026, 3, 8, 2, 30))

    def test_completion_preserves_due_uid_unknown_fields_and_is_idempotent(self):
        current = {'ics': fixture(), 'etag': '"one"', 'puts': 0}
        def dav(method, path, body=None, etag=None):
            self.assertEqual(path, COLLECTION + 'one.ics')
            if method == 'GET': return 200, {'ETag': current['etag']}, current['ics'].encode()
            self.assertEqual(etag, '"one"'); current.update(ics=body.decode(), etag='"two"', puts=current['puts'] + 1)
            return 204, {}, b''
        self.bridge.dav = dav
        self.bridge.snapshot = lambda **kwargs: {}
        self.bridge.complete(self.identifier, self.version, 'demo-operation-123456')
        _, task, item = parse_task(current['ics'])
        self.assertTrue(item['completed']); self.assertEqual(str(task.uid.value), 'demo')
        self.assertEqual(task.due.value, date(2026, 11, 14)); self.assertEqual(task.contents['x-demo'][0].value, 'preserve')
        self.bridge.complete(self.identifier, self.version, 'demo-operation-123456')
        self.assertEqual(current['puts'], 1)

    def test_phone_edit_conflict_and_recurring_are_never_overwritten(self):
        self.bridge.dav = lambda *args: (200, {'ETag': '"phone-new"'}, fixture(title='Phone edited').encode())
        with self.assertRaises(TaskError) as error:
            self.bridge.complete(self.identifier, self.version, 'demo-operation-123456')
        self.assertEqual(error.exception.status, 409)
        self.bridge.dav = lambda *args: (200, {'ETag': '"one"'}, fixture('RRULE:FREQ=DAILY').encode())
        with self.assertRaises(TaskError): self.bridge.complete(self.identifier, self.version, 'demo-operation-123456')

    def test_failed_and_partial_queries_retain_last_good_successful_empty_clears(self):
        old = {'items': [{'id': 'old'}], 'lastSuccess': 'before', 'stale': False}
        self.bridge.save('snapshot', old)
        self.bridge.dav = lambda *args: (207, {}, b'<D:multistatus xmlns:D="DAV:"><D:response><D:href>/wrong/</D:href></D:response></D:multistatus>')
        stale = self.bridge.snapshot(force=True)
        self.assertTrue(stale['stale']); self.assertEqual(stale['items'], old['items'])
        self.assertEqual(stale['lastSuccess'], 'before')
        self.bridge.dav = lambda *args: (207, {}, b'<D:multistatus xmlns:D="DAV:"/>')
        empty = self.bridge.snapshot(force=True)
        self.assertEqual(empty['items'], []); self.assertFalse(empty['stale'])

    def test_no_non_demo_route_or_mutations_other_than_put(self):
        for method, path in [('DELETE', COLLECTION + 'one.ics'), ('GET', '/other/one.ics'), ('PUT', COLLECTION + '../other.ics')]:
            with self.assertRaises(TaskError): self.bridge.dav(method, path)


if __name__ == '__main__': unittest.main()
