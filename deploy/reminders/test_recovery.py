"""Invented CalDAV fixtures only: no server credentials or live collections."""
from datetime import date
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from xml.sax.saxutils import escape

from task_bridge import Bridge, COLLECTION, TaskError, parse_task, task_path
from test_bridge import fixture


def report(*resources):
    return ('<D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">' + ''.join(
        '<D:response><D:href>' + escape(href) + '</D:href><D:propstat><D:prop><D:getetag>' + escape(etag) +
        '</D:getetag><C:calendar-data>' + escape(ics) + '</C:calendar-data></D:prop><D:status>HTTP/1.1 200 OK</D:status></D:propstat></D:response>'
        for href, etag, ics in resources) + '</D:multistatus>').encode()


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'state.sqlite'
        self.now = 1000.0
        self.settings = {'apiKey': 'invented-test-key'}
        self.account = {'username': 'pf1007l-demo', 'password': 'invented'}
        self.make_bridge()
        self.current = fixture()
        self.etag = '"one"'
        self.calls = []
        self.failure = None
        self.put_failure = None
        self.bridge.dav = self.dav
        self.snapshot = self.bridge.snapshot()
        self.item = self.snapshot['items'][0]
        self.operation = 'invented-operation-123456'

    def make_bridge(self):
        self.bridge = Bridge(self.account, self.settings, self.path, clock=lambda: self.now, jitter=lambda a,b: 1)

    def tearDown(self):
        self.bridge.db.close(); self.temp.cleanup()

    def dav(self, method, path, body=None, etag=None):
        self.calls.append(method)
        if self.failure: raise self.failure
        if method == 'REPORT': return 207, {}, report((COLLECTION + 'one.ics', self.etag, self.current))
        if method == 'GET': return 200, {'ETag': self.etag}, self.current.encode()
        self.assertEqual(method, 'PUT'); self.assertEqual(etag, self.etag)
        if self.put_failure == 'before': raise TaskError(503, 'Invented interruption')
        self.current, self.etag = body.decode(), '"two"'
        if self.put_failure == 'after': raise TaskError(503, 'Invented response loss')
        return 204, {}, b''

    def complete(self): return self.bridge.complete(self.item['id'], self.item['version'], self.operation)

    def test_backend_outage_retains_cache_backs_off_and_recovers_same_ids(self):
        self.failure = TaskError(503, 'Invented outage')
        self.now += 16
        stale = self.bridge.snapshot()
        self.assertTrue(stale['stale']); self.assertEqual(stale['items'], self.snapshot['items'])
        attempts = len(self.calls)
        for _ in range(100): self.bridge.snapshot()
        self.assertEqual(len(self.calls), attempts)
        self.assertEqual(stale['diagnostics']['retrySeconds'], 15)
        self.now += 16
        self.assertEqual(self.bridge.snapshot()['diagnostics']['retrySeconds'], 30)
        self.failure = None; self.now += 31
        fresh = self.bridge.snapshot()
        self.assertFalse(fresh['stale']); self.assertEqual(fresh['items'][0]['id'], self.item['id'])
        self.assertNotIn('diagnostics', fresh)

    def test_retry_after_and_long_outage_are_bounded(self):
        self.failure = TaskError(503, 'Invented busy', 'rate_limited', 120)
        self.assertEqual(self.bridge.snapshot(force=True)['diagnostics']['retrySeconds'], 120)
        self.failure = TaskError(503, 'Invented outage')
        for _ in range(40): stale = self.bridge.snapshot(force=True)
        self.assertEqual(stale['diagnostics']['retrySeconds'], 300)

    def test_restart_retains_last_good_and_operations(self):
        self.complete()
        self.bridge.db.close(); self.make_bridge()
        self.assertEqual(self.bridge.load('snapshot')['items'][0]['id'], self.item['id'])
        self.bridge.dav = lambda *args: self.fail('Committed operation was replayed after restart')
        self.assertTrue(self.complete()['completed'])
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_committed_write_lost_response_then_poll_then_restart_reconciles_once(self):
        self.put_failure = 'after'
        with self.assertRaises(TaskError): self.complete()
        self.assertEqual(self.bridge.db.execute('SELECT result FROM operations').fetchone()[0], 'pending')
        # A normal poll may see the new revision before the client retries.
        self.bridge.snapshot(force=True)
        self.bridge.db.close(); self.make_bridge(); self.bridge.dav = self.dav
        self.assertTrue(self.complete()['completed'])
        self.assertEqual(self.calls.count('PUT'), 1)

    def test_interruption_before_write_keeps_task_open_then_single_retry(self):
        self.put_failure = 'before'
        with self.assertRaises(TaskError): self.complete()
        self.assertFalse(parse_task(self.current)[2]['completed'])
        self.put_failure = None
        self.assertTrue(self.complete()['completed'])
        self.assertTrue(parse_task(self.current)[2]['completed'])
        self.assertEqual(self.calls.count('PUT'), 2)

    def test_pending_write_never_overwrites_later_phone_edit(self):
        self.put_failure = 'before'
        with self.assertRaises(TaskError): self.complete()
        self.current = fixture(title='Invented phone edit'); self.etag = '"phone-revision"'
        self.bridge.snapshot(force=True)
        self.put_failure = None
        with self.assertRaises(TaskError) as error: self.complete()
        self.assertEqual(error.exception.status, 409)
        self.assertEqual(self.calls.count('PUT'), 1)
        self.assertIn('Invented phone edit', self.current)

    def test_conditional_put_conflict_does_not_claim_completion(self):
        original = self.bridge.dav
        def raced(method, *args):
            if method == 'PUT': raise TaskError(409, 'Invented conditional conflict')
            return original(method, *args)
        self.bridge.dav = raced
        with self.assertRaises(TaskError) as error: self.complete()
        self.assertEqual(error.exception.status, 409)
        self.assertFalse(parse_task(self.current)[2]['completed'])
        self.assertEqual(self.bridge.db.execute('SELECT result FROM operations').fetchone()[0], 'pending')

    def test_operation_reuse_cannot_target_another_task_or_revision(self):
        self.complete()
        for identity, version in [('a'*64, self.item['version']), (self.item['id'], 'b'*64)]:
            with self.assertRaises(TaskError): self.bridge.complete(identity, version, self.operation)

    def test_duplicate_uid_snapshot_is_rejected_atomically(self):
        self.bridge.dav = lambda *args: (207, {}, report((COLLECTION+'one.ics', '"one"', fixture()), (COLLECTION+'two.ics', '"two"', fixture())))
        stale = self.bridge.snapshot(force=True)
        self.assertTrue(stale['stale']); self.assertEqual(stale['items'], self.snapshot['items'])
        self.assertEqual(len(self.bridge.load('resources')), 1)

    def test_publish_transaction_rolls_back_both_resources_and_snapshot(self):
        resources = self.bridge.load('resources')
        self.bridge.db.execute("CREATE TRIGGER deny_snapshot BEFORE INSERT ON state WHEN NEW.key='snapshot' BEGIN SELECT RAISE(ABORT, 'invented failure'); END")
        with self.assertRaises(sqlite3.DatabaseError): self.bridge.publish({'items': []}, {})
        self.assertEqual(self.bridge.load('resources'), resources)
        self.assertEqual(self.bridge.load('snapshot'), self.snapshot)

    def test_malformed_xml_and_entity_input_never_clear_cache(self):
        for data in [b'<partial>', b'<!DOCTYPE x [<!ENTITY x "bad">]><x/>', b'\xff', b'<x>\0</x>']:
            self.bridge.dav = lambda *args: (207, {}, data)
            self.assertEqual(self.bridge.snapshot(force=True)['items'], self.snapshot['items'])

    def test_encoded_and_nested_routes_are_denied(self):
        for path in [COLLECTION+'../one.ics', COLLECTION+'%2e%2e%2fone.ics', COLLECTION+'a%252fb.ics',
                     COLLECTION+'a%2fb.ics', COLLECTION+'a\\b.ics', COLLECTION+'a.ics?query', '//example/a.ics', COLLECTION+'a%00.ics']:
            with self.assertRaises(TaskError, msg=path): task_path(path)
        self.assertEqual(task_path(COLLECTION+'apple-uid.ics'), COLLECTION+'apple-uid.ics')

    def test_recurrence_variants_are_read_only_and_preserve_raw_resource(self):
        for extra in ['RRULE:FREQ=DAILY;COUNT=4', 'RDATE;VALUE=DATE:20261115', 'EXDATE;VALUE=DATE:20261115',
                      'RECURRENCE-ID;VALUE=DATE:20261115', 'EXRULE:FREQ=WEEKLY']:
            self.current = fixture(extra)
            self.assertTrue(parse_task(self.current)[2]['recurring'], extra)
            before = self.current; calls = self.calls.count('PUT')
            with self.assertRaises(TaskError): self.complete()
            self.assertEqual(self.current, before); self.assertEqual(self.calls.count('PUT'), calls)

    def test_detached_instances_are_preserved_but_mixed_uid_and_multiple_masters_fail(self):
        instance = 'BEGIN:VTODO\r\nUID:demo\r\nRECURRENCE-ID;VALUE=DATE:20261115\r\nSUMMARY:Exception\r\nEND:VTODO\r\n'
        resource = fixture('RRULE:FREQ=DAILY').replace('END:VCALENDAR', instance+'END:VCALENDAR')
        self.assertTrue(parse_task(resource)[2]['recurring'])
        for invalid in [resource.replace('UID:demo\r\nRECURRENCE', 'UID:other\r\nRECURRENCE'), resource.replace('RECURRENCE-ID;VALUE=DATE:20261115\r\n', '')]:
            with self.assertRaises(TaskError): parse_task(invalid)

    def test_alarm_and_due_survive_nonrecurring_completion(self):
        self.current = fixture('BEGIN:VALARM\r\nACTION:DISPLAY\r\nTRIGGER:-PT15M\r\nDESCRIPTION:Invented alarm\r\nEND:VALARM')
        self.complete()
        _, task, item = parse_task(self.current)
        self.assertTrue(item['completed']); self.assertEqual(task.due.value, date(2026,11,14))
        self.assertEqual(task.valarm.description.value, 'Invented alarm')
        self.assertEqual(task.contents['x-demo'][0].value, 'preserve')

    def test_weak_and_missing_etags_block_writes(self):
        for etag in ['', 'W/"one"']:
            self.etag = etag
            with self.assertRaises(TaskError): self.complete()
        self.assertEqual(self.calls.count('PUT'), 0)

    def test_backend_auth_failure_requires_operator_not_retry_storm(self):
        self.bridge.auth_failed = True
        for _ in range(20):
            stale = self.bridge.snapshot(force=True)
            self.assertTrue(stale['stale'])
        self.assertEqual(self.calls, ['REPORT'])

    def test_state_symlink_is_rejected(self):
        link = Path(self.temp.name)/'link.sqlite'; link.symlink_to(self.path)
        with self.assertRaises(RuntimeError): Bridge(self.account, self.settings, link)


if __name__ == '__main__': unittest.main()
