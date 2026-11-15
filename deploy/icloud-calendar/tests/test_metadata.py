import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
from readonly_caldav import ReadonlyCalDAV,CalendarError

URL='https://p01-caldav.icloud.com/home/invented/'

class MetadataTests(unittest.TestCase):
 def test_reads_exact_collection_name_and_optional_color(self):
  client=ReadonlyCalDAV('invented@example.invalid','invented')
  for color,expected in [('#123456FF','#123456'),('unavailable',None)]:
   root=ET.fromstring('<d:multistatus xmlns:d="DAV:" xmlns:a="http://apple.com/ns/ical/"><d:response><d:href>'+URL+'</d:href><d:propstat><d:status>HTTP/1.1 200 OK</d:status><d:prop><d:displayname>School</d:displayname><a:calendar-color>'+color+'</a:calendar-color></d:prop></d:propstat></d:response></d:multistatus>')
   with patch.object(client,'_props',return_value=(URL,root)) as request:
    self.assertEqual(client.metadata(URL),{'name':'School','color':expected})
    self.assertEqual(request.call_args.args[0],URL)
    self.assertEqual(len(request.call_args.args),2) # default depth zero
 def test_missing_or_other_collection_cannot_replace_metadata(self):
  client=ReadonlyCalDAV('invented@example.invalid','invented')
  for data in ['<d:multistatus xmlns:d="DAV:"/>','<d:multistatus xmlns:d="DAV:"><d:response><d:href>/other/</d:href><d:propstat><d:status>HTTP/1.1 200 OK</d:status><d:prop><d:displayname>Other</d:displayname></d:prop></d:propstat></d:response></d:multistatus>']:
   with patch.object(client,'_props',return_value=(URL,ET.fromstring(data))):
    with self.assertRaises(CalendarError):client.metadata(URL)
