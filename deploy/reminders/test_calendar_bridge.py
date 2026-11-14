"""Calendar relay is local, optional, bounded and never holds Apple credentials."""
import unittest
from unittest.mock import patch,MagicMock
from task_bridge import Bridge

class CalendarRelayTests(unittest.TestCase):
 def setUp(self):
  self.bridge=Bridge({'username':'pf1007l-demo','password':'invented'}, {'apiKey':'invented'},':memory:')
 def tearDown(self):self.bridge.db.close()
 def test_disabled_source_does_not_contact_any_calendar_service(self):
  with patch('task_bridge.http.client.HTTPConnection') as call:
   self.assertEqual(self.bridge.calendar_snapshot(),{'source':'disabled'});call.assert_not_called()
 def test_fixed_loopback_read_and_minimal_service_key(self):
  self.bridge.calendar_key='invented-calendar-service-key'
  with patch('task_bridge.http.client.HTTPConnection') as connect:
   conn=connect.return_value;reply=conn.getresponse.return_value;reply.status=200
   reply.read.return_value=b'{"source":"private-caldav","events":[],"stale":false}'
   self.assertTrue(self.bridge.calendar_snapshot()['available'])
   connect.assert_called_once_with('127.0.0.1',5241,timeout=3)
   conn.request.assert_called_once_with('GET','/snapshot',headers={'X-Calendar-Key':'invented-calendar-service-key'})
   conn.close.assert_called_once()
 def test_transport_errors_do_not_expose_keys_or_return_demo_as_live(self):
  self.bridge.calendar_key='invented-calendar-service-key'
  with patch('task_bridge.http.client.HTTPConnection') as connect:
   connect.return_value.request.side_effect=OSError('invented-secret-payload')
   result=self.bridge.calendar_snapshot()
   self.assertEqual(result['source'],'private-caldav');self.assertFalse(result['available'])
   self.assertTrue(result['stale']);self.assertNotIn('invented',str(result))
