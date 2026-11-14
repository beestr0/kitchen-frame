import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { normalize } from '../../deploy/icloud-calendar/normalize.mjs';
const ics=(extra='',uid='invented')=>['BEGIN:VCALENDAR','VERSION:2.0','BEGIN:VEVENT','UID:'+uid,
 'DTSTART;VALUE=DATE:20261114','DTEND;VALUE=DATE:20261115','SUMMARY:Invented appointment',
 'LOCATION:Omit private location','DESCRIPTION:Omit private notes','ATTENDEE:mailto:invented@example.invalid',extra,'END:VEVENT','END:VCALENDAR'].filter(Boolean).join('\r\n');
const input=(text=ics())=>({rows:[{ical:text}],calendar:{id:'work',name:'Work',color:'#123456'},
 from:'2026-11-01T00:00:00Z',to:'2026-12-01T00:00:00Z',timezone:'America/Indiana/Indianapolis'});
test('private calendar minimizes fields and preserves stable calendar/color/all-day end',()=>{
 const [e]=normalize(input());assert.equal(e.end,'2026-11-15');assert.equal(e.calendarId,'work');assert.equal(e.color,'#123456');assert.match(e.uid,/^ical:[a-f0-9]{64}$/);
 assert.deepEqual(Object.keys(e),['uid','calendarId','calendarName','color','cal','title','allDay','start','end']);
 assert.ok(!JSON.stringify(e).includes('Omit'));assert.ok(!JSON.stringify(e).includes('mailto:'));
 assert.equal(normalize(input())[0].uid,e.uid);
 assert.notEqual(normalize({...input(),calendar:{id:'other',name:'Other',color:'#654321'}})[0].uid,e.uid);
});
test('private recurring event excludes cancelled/exception dates and authoritative empty removes old rows',()=>{
 assert.deepEqual(normalize(input(ics('RRULE:FREQ=DAILY;COUNT=3\r\nEXDATE;VALUE=DATE:20261115'))).map(e=>e.start),['2026-11-14','2026-11-16']);
 assert.deepEqual(normalize(input(ics('STATUS:CANCELLED'))),[]);
 assert.deepEqual(normalize({...input(),rows:[]}),[]);
});
test('private floating times use configured zone and DST retains wall time',()=>{
 const text=ics().replace('DTSTART;VALUE=DATE:20261114','DTSTART:20261114T090000').replace('DTEND;VALUE=DATE:20261115','DTEND:20261114T100000');
 assert.equal(normalize(input(text))[0].start,'2026-11-14T14:00:00.000Z');
 const spring=text.replaceAll('20261114','20260307').replace('END:VEVENT','RRULE:FREQ=DAILY;COUNT=3\r\nEND:VEVENT');
 const events=normalize({...input(spring),from:'2026-03-01T00:00:00Z',to:'2026-04-01T00:00:00Z'});
 assert.deepEqual(events.map(e=>e.start),['2026-03-07T14:00:00.000Z','2026-03-08T13:00:00.000Z','2026-03-09T13:00:00.000Z']);
});
test('invalid or duplicate resources and unbounded rules cannot publish partial event lists',()=>{
 for(const text of ['invalid',ics().replace('UID:invented\r\n',''),ics().replace('DTSTART;VALUE=DATE:20261114\r\n',''),ics('RRULE:FREQ=SECONDLY'),ics().replace('DTSTART;VALUE=DATE:20261114','DTSTART;TZID=Unknown/Private:20261114T090000')]) assert.throws(()=>normalize(input(text)));
 assert.throws(()=>normalize({...input(),rows:[{ical:ics()},{ical:ics()}]}));
 assert.throws(()=>normalize({...input(),to:'2030-01-01T00:00:00Z'}));
});
test('normalization CLI returns fixed errors without event payloads',()=>{
 const run=spawnSync(process.execPath,[fileURLToPath(new URL('../../deploy/icloud-calendar/normalize.mjs',import.meta.url))],{input:'invented-private-bad-payload',encoding:'utf8'});
 assert.equal(run.status,1);assert.equal(run.stdout,'');assert.equal(run.stderr,'Calendar normalization failed\n');
});
