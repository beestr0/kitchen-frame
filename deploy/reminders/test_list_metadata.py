"""Fixed-collection metadata boundaries, without network or personal records."""
import unittest
from unittest.mock import patch
from task_bridge import Bridge, COLLECTION, TaskError


def metadata(name='Do It', href=COLLECTION, status='200 OK'):
    return ('<d:multistatus xmlns:d="DAV:"><d:response><d:href>' + href +
            '</d:href><d:propstat><d:status>HTTP/1.1 '+status+'</d:status>'+
            '<d:prop><d:displayname>'+name+'</d:displayname></d:prop></d:propstat></d:response></d:multistatus>').encode()


class ListMetadataTests(unittest.TestCase):
    def setUp(self):
        self.bridge = Bridge({'username':'pf1007l-demo','password':'invented'}, {'apiKey':'invented'}, ':memory:')
        self.addCleanup(self.bridge.db.close)

    def test_exact_fixed_collection_display_name_and_rename(self):
        for name in ('Do It', 'Renamed fixture'):
            with patch.object(self.bridge, 'dav', return_value=(207, {}, metadata(name))) as request:
                self.assertEqual(self.bridge.list_name(), name)
                self.assertEqual(request.call_args.args[:2], ('PROPFIND', COLLECTION))

    def test_missing_ambiguous_wrong_collection_and_unsafe_xml_are_rejected(self):
        for data in (metadata(href='/unrelated/'), metadata(status='404 Missing'), metadata(name=''),
                     b'<!DOCTYPE x><x/>', b'<d:multistatus xmlns:d="DAV:"/>'):
            with patch.object(self.bridge, 'dav', return_value=(207, {}, data)):
                with self.assertRaises(TaskError):self.bridge.list_name()

    def test_propfind_cannot_read_any_other_collection_or_task(self):
        for path in ('/unrelated/', COLLECTION+'one.ics'):
            with patch.object(self.bridge.opener, 'open') as transport:
                with self.assertRaises(TaskError):self.bridge.dav('PROPFIND', path)
                transport.assert_not_called()
