import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from collector import Collector,selected
from readonly_caldav import CalendarError,ReadonlyCalDAV
import tempfile
import unittest
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
import xml.etree.ElementTree as ET


def config(*ids):
 return {'enabled':True,'readOnly':True,'allowCloudUpload':False,'syncMinutes':5,
 'selectedCalendars':[{'id':i,'name':i,'color':'#123456','href':'https://p01-caldav.icloud.com/home/'+i+'/'} for i in ids]}

class CollectorTests(unittest.TestCase):
 def setUp(self):
  self.now=1000000;self.calls=[];self.fail=set();self.rows={}
  class Client:
   def metadata(client,href):
    return {'name':href.rstrip('/').split('/')[-1], 'color':None}
   def query_events(client,href,start,end):
    self.calls.append(href)
    if href in self.fail:raise CalendarError('Calendar transport unavailable')
    return self.rows.get(href,[])
  self.client=Client()
  def normalize(rows,c,*args):return [dict(uid='ical:'+c['id'],start='2026-11-14',end='2026-11-15',allDay=True,title='Invented',calendarId=c['id']) for _ in rows]
  self.normalize=normalize
 def collector(self,cfg=None,db=':memory:'):
  obj=Collector(cfg or config('work','home'),self.client,db,self.normalize,lambda:self.now)
  self.addCleanup(obj.db.close);return obj
 def test_rename_color_identity_and_offline_restart(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'fixture.sqlite';c=self.collector(db=path)
   self.rows[c.calendars[0]['href']]=[1];before=c.refresh();uid=before['events'][0]['uid']
   with patch.object(self.client,'metadata',return_value={'name':'School','color':'#ABCDEF'}):
    self.now+=301;after=c.refresh()
   self.assertEqual(after['events'][0]['uid'],uid)
   self.assertEqual(after['events'][0]['calendarName'],'School')
   self.assertEqual(after['calendars'][0]['id'],'work')
   self.assertEqual(after['events'][0]['color'],'#ABCDEF')
   restarted=self.collector(db=path)
   with patch.object(self.client,'metadata',side_effect=CalendarError('Calendar transport unavailable')):
    stale=restarted.refresh()
   self.assertTrue(stale['stale']);self.assertEqual(stale['events'][0]['calendarName'],'School')
   self.assertEqual(stale['events'][0]['uid'],uid)
 def test_only_selected_calendars_and_successful_empty(self):
  c=self.collector();href=c.calendars[0]['href'];self.rows[href]=[1]
  first=c.refresh();self.assertEqual(len(first['events']),1);self.assertEqual(len(self.calls),2)
  self.now+=301;self.rows[href]=[];self.assertEqual(c.refresh()['events'],[])
 def test_partial_failure_retains_only_failed_calendar_last_good_and_backs_off(self):
  c=self.collector();a,b=[x['href'] for x in c.calendars]
  self.rows={a:[1],b:[1]};c.refresh();self.now+=301;self.fail.add(a);self.rows[b]=[]
  state=c.refresh();self.assertEqual(len(state['events']),1);self.assertTrue(state['stale'])
  before=len(self.calls);c.refresh();self.assertEqual(len(self.calls),before)
  self.now+=301;self.fail.clear();self.assertFalse(c.refresh()['stale'])
 def test_restart_retains_stale_cache_and_selection_changes_purge_removed(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'fixture.sqlite';c=self.collector(db=path);self.rows[c.calendars[0]['href']]=[1];c.refresh()
   self.now+=1000;c2=self.collector(db=path);self.assertTrue(c2.snapshot()['stale']);self.assertEqual(len(c2.snapshot()['events']),1)
   c3=self.collector(config('home'),path);self.assertEqual(c3.snapshot()['events'],[])
 def test_auth_failure_stops_automatic_account_attempts_until_restart(self):
  c=self.collector()
  with patch.object(self.client,'query_events',side_effect=CalendarError('Calendar authorization required')) as query:
   self.assertTrue(c.refresh()['stale']);self.now+=10000;c.refresh();self.assertEqual(query.call_count,1)
 def test_bad_parser_output_never_replaces_last_good(self):
  c=self.collector();self.rows[c.calendars[0]['href']]=[1];c.refresh();self.now+=301
  c.normalizer=lambda *args:(_ for _ in ()).throw(ValueError('invented-private-title'))
  state=c.refresh();self.assertEqual(len(state['events']),1);self.assertNotIn('invented-private-title',str(state))
 def test_configuration_does_not_activate_without_explicit_selected_scope(self):
  for cfg in [dict(config('work'),enabled=False),config(),dict(config('work'),allowCloudUpload=True),config('work','work')]:
   with self.assertRaises(CalendarError):selected(cfg)
 def test_failed_multistatus_or_missing_etag_cannot_be_empty_deletion(self):
  c=ReadonlyCalDAV('invented@example.invalid','invented')
  now=datetime.now(timezone.utc)
  for xml in ['<d:multistatus xmlns:d="DAV:"><d:response><d:href>/home/work/one.ics</d:href><d:status>HTTP/1.1 500 Failed</d:status></d:response></d:multistatus>',
              '<d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav"><d:response><d:href>/home/work/one.ics</d:href><d:propstat><d:status>HTTP/1.1 200 OK</d:status><d:prop><c:calendar-data>invented</c:calendar-data></d:prop></d:propstat></d:response></d:multistatus>']:
   with patch.object(c,'_request',return_value=('https://p01-caldav.icloud.com/home/work/',ET.fromstring(xml))):
    with self.assertRaises(CalendarError):c.query_events('https://p01-caldav.icloud.com/home/work/',now,now+timedelta(days=1))


class SelectionTests(unittest.TestCase):
 def test_owner_selects_explicit_calendars_with_colors_without_accessing_events(self):
  from authorize import choose
  rows=[{'href':'https://p01-caldav.icloud.com/home/a/','name':'Invented','color':'#112233'},
        {'href':'https://p01-caldav.icloud.com/home/b/','name':'Other','color':None}]
  chosen=choose(rows,'2,1');self.assertEqual(chosen[0]['name'],'Other');self.assertEqual(chosen[1]['color'],'#112233')
  for bad in ['0','1,1','3','']:
   with self.assertRaises((ValueError,IndexError)):choose(rows,bad)
