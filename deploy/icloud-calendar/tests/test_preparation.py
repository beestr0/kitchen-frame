import importlib.util
import json
from pathlib import Path
import ssl
import sys
import tempfile
import unittest
import urllib.error
from unittest.mock import patch

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE))
from readonly_caldav import ReadonlyCalDAV,CalendarError,approved_url,xml
from prepare_credentials import save

class Reply:
    status=207
    def __init__(self,data):self.data=data
    def read(self,limit):return self.data[:limit]
    def __enter__(self):return self
    def __exit__(self,*args):pass

def multi(href, props):
    return ('<d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav" xmlns:a="http://apple.com/ns/ical/">'
      '<d:response><d:href>'+href+'</d:href><d:propstat><d:prop>'+props+'</d:prop><d:status>HTTP/1.1 200 OK</d:status>'
      '</d:propstat></d:response></d:multistatus>').encode()

class Preparation(unittest.TestCase):
    def test_no_account_network_on_construction_and_tls_checks_enabled(self):
        with patch('urllib.request.build_opener') as build, patch('ssl.create_default_context', wraps=ssl.create_default_context) as factory:
            client=ReadonlyCalDAV('invented@example.test','invented-password')
            self.assertNotIn('invented',repr(client));build.return_value.open.assert_not_called()
            context=build.call_args.args[-1]._context
            self.assertTrue(context.check_hostname);self.assertEqual(context.verify_mode,ssl.CERT_REQUIRED)
            self.assertGreaterEqual(context.minimum_version,ssl.TLSVersion.TLSv1_2)
    def test_only_approved_https_endpoints(self):
        for bad in ['http://caldav.icloud.com/','https://evil.test/','https://caldav.icloud.com.evil.test/',
                    'https://caldav.icloud.com:444/','https://name:secret@caldav.icloud.com/','https://caldav.icloud.com/?secret=x',
                    'https://caldav.icloud.com/#token','https://caldav.icloud.com/\r\nsecret','https://contacts.icloud.com/']:
            with self.subTest(bad=bad),self.assertRaises(CalendarError):approved_url(bad)
        self.assertEqual(approved_url('/private/calendars/','https://p123-caldav.icloud.com/principal/'),'https://p123-caldav.icloud.com/private/calendars/')
    def test_writes_rejected_before_transport(self):
        c=ReadonlyCalDAV('invented@example.test','invented-password')
        with patch.object(c._opener,'open') as call:
            for method in ['PUT','POST','DELETE','PATCH','PROPPATCH','MKCALENDAR','MOVE','COPY']:
                with self.assertRaises(CalendarError):c._request(method,'https://caldav.icloud.com/')
            call.assert_not_called()
    def test_reject_xml_entities_utf16_and_oversized_data(self):
        for text in [b'<!DOCTYPE x [<!ENTITY y "secret">]><x>&y;</x>', '<x/>'.encode('utf-16'), b'x'*(5*1024*1024+1)]:
            with self.assertRaises(CalendarError):xml(text)
    def test_unapproved_redirect_cannot_receive_credentials(self):
        c=ReadonlyCalDAV('invented@example.test','invented-password')
        failure=urllib.error.HTTPError('https://caldav.icloud.com/',302,'redirect',{'Location':'https://evil.test/'},None)
        with patch.object(c._opener,'open',side_effect=failure) as call:
            with self.assertRaises(CalendarError):c._request('PROPFIND','https://caldav.icloud.com/')
            self.assertEqual(call.call_count,1)
    def test_errors_never_echo_transport_secrets(self):
        c=ReadonlyCalDAV('invented@example.test','invented-password')
        with patch.object(c._opener,'open',side_effect=OSError('invented-password private event title')):
            with self.assertRaises(CalendarError) as raised:c._request('PROPFIND','https://caldav.icloud.com/')
            self.assertEqual(str(raised.exception),'Calendar transport unavailable')
    def test_discovery_reads_names_without_querying_events(self):
        c=ReadonlyCalDAV('invented@example.test','invented-password')
        replies=[Reply(multi('/', '<d:current-user-principal><d:href>/principal/</d:href></d:current-user-principal>')),
                 Reply(multi('/principal/','<c:calendar-home-set><d:href>https://p01-caldav.icloud.com/home/</d:href></c:calendar-home-set>')),
                 Reply(multi('/home/work/','<d:resourcetype><c:calendar/></d:resourcetype><d:displayname>Invented Work</d:displayname><a:calendar-color>#123456FF</a:calendar-color>'))]
        with patch.object(c._opener,'open',side_effect=replies) as call:
            rows=c.discover();self.assertEqual(rows[0]['name'],'Invented Work');self.assertEqual(rows[0]['color'],'#123456')
            self.assertEqual([v.args[0].method for v in call.call_args_list],['PROPFIND']*3)
    def test_bounded_vevent_query_and_no_event_export(self):
        from datetime import datetime,timezone,timedelta
        c=ReadonlyCalDAV('invented@example.test','invented-password');now=datetime.now(timezone.utc)
        with patch.object(c._opener,'open',return_value=Reply(multi('/home/work/one.ics','<d:getetag>"one"</d:getetag><c:calendar-data>BEGIN:VCALENDAR\nEND:VCALENDAR</c:calendar-data>'))) as call:
            rows=c.query_events('https://p01-caldav.icloud.com/home/work/',now,now+timedelta(days=10));self.assertEqual(len(rows),1)
            req=call.call_args.args[0];self.assertEqual(req.method,'REPORT');self.assertIn(b'VEVENT',req.data)
            with self.assertRaises(CalendarError):c.query_events('https://p01-caldav.icloud.com/home/work/',now,now+timedelta(days=367))
    def test_credentials_private_and_never_overwritten(self):
        with tempfile.TemporaryDirectory() as parent:
            directory=Path(parent)/'private';save(directory,'invented@example.test','abcd-efgh-ijkl-mnop')
            target=directory/'apple.json';self.assertEqual(directory.stat().st_mode&0o777,0o700);self.assertEqual(target.stat().st_mode&0o777,0o600)
            old=target.read_bytes()
            with self.assertRaises(ValueError):save(directory,'other@example.test','abcd-efgh-ijkl-mnop')
            self.assertEqual(target.read_bytes(),old)
    def test_existing_symlinks_and_main_password_rejected(self):
        with tempfile.TemporaryDirectory() as parent:
            root=Path(parent);directory=root/'private';directory.mkdir(mode=0o700);(directory/'apple.json').symlink_to(root/'missing')
            with self.assertRaises(ValueError):save(directory,'invented@example.test','abcd-efgh-ijkl-mnop')
            with self.assertRaises(ValueError):save(root/'second','invented@example.test','ordinary-main-password')
            self.assertFalse((root/'second').exists())
if __name__=='__main__':unittest.main()
