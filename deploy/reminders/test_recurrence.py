"""Disposable recurrence compatibility: actual Radicale WSGI + restricted bridge.

No TCP listener, real account, clock waiting, existing task or running service.
"""
import base64
from datetime import date
import io
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from wsgiref.util import setup_testing_defaults

from task_bridge import Bridge, COLLECTION, QUERY, TaskError, parse_task


def calendar(rule='RRULE:FREQ=DAILY;COUNT=3', override='', due='20261114'):
    return '\r\n'.join([
        'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//PF1007L invented recurrence//EN',
        'BEGIN:VTODO', 'UID:invented-series', 'DTSTAMP:20261114T120000Z',
        'DTSTART;VALUE=DATE:20261114', 'DUE;VALUE=DATE:' + due,
        'SUMMARY:Invented recurring reminder', 'STATUS:NEEDS-ACTION',
        'X-APPLE-SORT-ORDER:123', 'DESCRIPTION:Preserve invented notes', rule,
        'BEGIN:VALARM', 'ACTION:DISPLAY', 'TRIGGER:-PT15M',
        'DESCRIPTION:Invented alarm', 'END:VALARM', 'END:VTODO', override,
        'END:VCALENDAR', ''])


def exception(day='20261115', status='COMPLETED'):
    return '\r\n'.join(['BEGIN:VTODO', 'UID:invented-series',
        'RECURRENCE-ID;VALUE=DATE:'+day, 'DUE;VALUE=DATE:'+day,
        'DTSTAMP:20261114T120000Z', 'STATUS:'+status, 'END:VTODO'])


class RecurrenceSafetyTests(unittest.TestCase):
    def setUp(self):
        self.bridge = Bridge({'username':'pf1007l-demo','password':'invented'},
                             {'apiKey':'invented'}, ':memory:')
        self.identifier = self.bridge.opaque(COLLECTION+'\0invented-series')
        self.version = self.bridge.opaque('"one"')
        self.bridge.save('resources',{self.identifier:{'href':COLLECTION+'series.ics',
            'uid':'invented-series','etag':'"one"','version':self.version}})

    def tearDown(self): self.bridge.db.close()

    def test_all_recurrence_shapes_reject_completion_without_any_write(self):
        shapes = ['RRULE:FREQ=DAILY;COUNT=3', 'RRULE:FREQ=WEEKLY;UNTIL=20261231',
                  'RRULE:FREQ=MONTHLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=-1',
                  'RDATE;VALUE=DATE:20261115,20261120', 'EXDATE;VALUE=DATE:20261115',
                  'EXRULE:FREQ=WEEKLY;BYDAY=SA,SU',
                  'RECURRENCE-ID;VALUE=DATE:20261114']
        texts = [calendar(rule) for rule in shapes] + [calendar(override=exception())]
        for text in texts:
            with self.subTest(shape=text):
                before = text.encode(); calls = []
                def dav(method,path,body=None,etag=None):
                    calls.append(method)
                    self.assertEqual(method,'GET')
                    return 200,{'ETag':'"one"'},before
                self.bridge.dav = dav
                with self.assertRaises(TaskError) as result:
                    self.bridge.complete(self.identifier,self.version,'invented-operation-123')
                self.assertEqual(result.exception.status,409)
                self.assertEqual(calls,['GET'])
                self.assertEqual(self.bridge.db.execute('SELECT COUNT(*) FROM operations').fetchone()[0],0)
                root,task,item = parse_task(text)
                self.assertTrue(item['recurring']);self.assertFalse(item['completed'])
                self.assertEqual(task.contents['x-apple-sort-order'][0].value,'123')
                self.assertEqual(len(task.contents['valarm']),1)

    def test_duplicate_detached_occurrence_is_ambiguous(self):
        with self.assertRaises(TaskError):
            parse_task(calendar(override=exception()+'\r\n'+exception()))

    def test_phone_advancement_keeps_identity_and_never_generates_own_occurrences(self):
        def report(text,etag):
            root = ET.Element('{DAV:}multistatus');response = ET.SubElement(root,'{DAV:}response')
            ET.SubElement(response,'{DAV:}href').text = COLLECTION+'series.ics'
            stat=ET.SubElement(response,'{DAV:}propstat');prop=ET.SubElement(stat,'{DAV:}prop')
            ET.SubElement(prop,'{DAV:}getetag').text=etag
            ET.SubElement(prop,'{urn:ietf:params:xml:ns:caldav}calendar-data').text=text
            ET.SubElement(stat,'{DAV:}status').text='HTTP/1.1 200 OK'
            return ET.tostring(root)
        current = {'text':calendar(),'etag':'"one"'}
        self.bridge.dav=lambda *args:(207,{},report(current['text'],current['etag']))
        first=self.bridge.snapshot(force=True)['items'];self.assertEqual(len(first),1)
        current.update(text=calendar(due='20261115'),etag='"two"')
        second=self.bridge.snapshot(force=True)['items'];self.assertEqual(len(second),1)
        self.assertEqual(first[0]['id'],second[0]['id'])
        self.assertNotEqual(first[0]['version'],second[0]['version'])
        self.assertEqual(second[0]['due'],{'day':'2026-11-15'})
        self.assertFalse(second[0]['canComplete']);self.assertFalse(second[0]['completed'])
        # This is a hypothetical client update, not proof of Apple's actual strategy.


class RadicaleRecurrenceTests(unittest.TestCase):
    def setUp(self):
        import radicale
        from radicale.config import load
        self.temp=tempfile.TemporaryDirectory(prefix='pf1007l-fictional-recurrence-',
            dir='/dev/shm' if Path('/dev/shm').is_dir() else None)
        root=Path(self.temp.name); users=root/'users';users.write_text('pf1007l-demo:invented-fixture-only\n')
        config=load([])
        config.update({'auth':{'type':'htpasswd','htpasswd_filename':str(users),'htpasswd_encryption':'plain'},
                       'storage':{'filesystem_folder':str(root/'data')},'rights':{'type':'owner_only'}})
        self.app=radicale.Application(config)
        status,_,_=self.request('MKCALENDAR',COLLECTION,
            b'<C:mkcalendar xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav"><D:set><D:prop><C:supported-calendar-component-set><C:comp name="VTODO"/></C:supported-calendar-component-set></D:prop></D:set></C:mkcalendar>')
        self.assertEqual(status,201)

    def tearDown(self):self.temp.cleanup()

    def request(self,method,path,body=b'',etag=None):
        env={};setup_testing_defaults(env)
        env.update(REQUEST_METHOD=method,PATH_INFO=path,CONTENT_LENGTH=str(len(body)),
                   CONTENT_TYPE='text/calendar' if method=='PUT' else 'application/xml',
                   HTTP_AUTHORIZATION='Basic '+base64.b64encode(b'pf1007l-demo:invented-fixture-only').decode(),
                   HTTP_DEPTH='1',**{'wsgi.input':io.BytesIO(body),'wsgi.errors':io.StringIO()})
        if etag:env['HTTP_IF_MATCH']=etag
        elif method=='PUT':env['HTTP_IF_NONE_MATCH']='*'
        output={}
        def start(status,headers,exc_info=None):output.update(status=int(status.split()[0]),headers=dict(headers))
        body=b''.join(self.app(env,start))
        return output['status'],output['headers'],body

    def test_actual_server_preserves_series_alarm_exceptions_and_conditional_writes(self):
        path=COLLECTION+'fictional.ics'
        text=calendar(override=exception())
        self.assertEqual(self.request('PUT',path,text.encode())[0],201)
        status,headers,raw=self.request('GET',path);self.assertEqual(status,200)
        root,task,item=parse_task(raw.decode())
        self.assertTrue(item['recurring']);self.assertEqual(len(root.contents['vtodo']),2)
        self.assertEqual(task.due.value,date(2026,11,14));self.assertEqual(len(task.contents['valarm']),1)
        original=raw
        changed=raw.replace(b'Invented recurring reminder',b'Invented phone edit')
        self.assertEqual(self.request('PUT',path,changed,headers['ETag'])[0],204)
        self.assertEqual(self.request('PUT',path,original,headers['ETag'])[0],412)
        latest=self.request('GET',path)[2]
        self.assertIn(b'Invented phone edit',latest)
        self.assertEqual(len(parse_task(latest.decode())[0].contents['vtodo']),2)
        status,_,report=self.request('REPORT',COLLECTION,QUERY)
        self.assertEqual(status,207)
        self.assertEqual(len(ET.fromstring(report).findall('{DAV:}response')),1)
        self.assertEqual(self.request('GET',path)[2],latest)
