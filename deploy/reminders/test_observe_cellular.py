import json
import unittest
from unittest.mock import patch
import observe_cellular as observer


class CellularObserverTests(unittest.TestCase):
    def test_projection_excludes_unrelated_titles_and_raw_uid(self):
        def task(title, uid):
            return '<C:calendar-data>BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VTODO\nUID:'+uid+'\nSUMMARY:'+title+'\nDUE;VALUE=DATE:20261115\nSTATUS:NEEDS-ACTION\nEND:VTODO\nEND:VCALENDAR\n</C:calendar-data>'
        xml = ('<D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">'+
               task('Cellular pilot WiFi 01','invented-uid')+task('Private unrelated title','other-uid')+
               task('Cellular pilot arbitrary private suffix','third-uid')+'</D:multistatus>').encode()
        data = observer.project_calendar(xml)
        self.assertEqual(len(data),1)
        self.assertEqual(data[0]['due'],'2026-11-15')
        self.assertFalse(data[0]['completed'])
        self.assertNotIn('invented-uid',json.dumps(data))
        self.assertNotIn('Private',json.dumps(data))

    def test_native_authorization_required_before_any_read(self):
        for uid,tty in [(501,True),(0,False)]:
            with patch.object(observer.os,'geteuid',return_value=uid), patch.object(observer.os,'isatty',return_value=tty), patch.object(observer,'observe') as observe:
                with self.assertRaises(SystemExit):observer.main()
                observe.assert_not_called()


if __name__ == '__main__': unittest.main()
