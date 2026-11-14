// Linux-only event shaping. No network, credentials, browser or Worker imports.
import { createHash } from 'node:crypto';
import { pathToFileURL } from 'node:url';
import ICAL from '../../dashboard/node_modules/ical.js/dist/ical.js';
import { expand } from '../../dashboard/worker/calendar.js';
const MAX = 5 * 1024 * 1024;
const fail = () => { throw Error('Calendar normalization failed'); };
export function normalize(input) {
  const { rows, calendar, from, to, timezone } = input || {};
  const lo = Date.parse(from), hi = Date.parse(to);
  if (!Array.isArray(rows) || rows.length > 1000 || !calendar ||
      !/^[a-zA-Z0-9_-]{1,64}$/.test(calendar.id || '') || typeof calendar.name !== 'string' || calendar.name.length > 120 ||
      !/^#[a-fA-F0-9]{6}$/.test(calendar.color || '') || ![from,to].every(x=>typeof x==='string' && /Z$/.test(x)) ||
      !Number.isFinite(lo) || !Number.isFinite(hi) || hi<=lo || hi-lo>366*864e5) fail();
  try { new Intl.DateTimeFormat('en',{timeZone:timezone}); } catch { fail(); }
  let size=0; const seen=new Set(), events=[];
  for (const row of rows) {
    if (typeof row?.ical!=='string' || (size+=Buffer.byteLength(row.ical))>MAX) fail();
    const root=new ICAL.Component(ICAL.parse(row.ical));
    const components=root.getAllSubcomponents('vevent');
    if (root.name!=='vcalendar' || !components.length || root.getAllSubcomponents().some(c=>!['vevent','vtimezone'].includes(c.name))) fail();
    const uids=new Set(), instances=new Set();
    const known=new Set(root.getAllSubcomponents('vtimezone').map(c=>c.getFirstPropertyValue('tzid')));
    const checkZone=z=>{ if (z && !known.has(z)) { try { new Intl.DateTimeFormat('en',{timeZone:z}); } catch { fail(); } } };
    checkZone(root.getFirstPropertyValue('x-wr-timezone'));
    for (const c of components) {
      const uid=c.getFirstPropertyValue('uid'), rid=c.getFirstPropertyValue('recurrence-id');
      if (typeof uid!=='string' || !uid || uid.length>1024) fail();
      uids.add(uid);
      const instance=rid ? String(rid) : 'master';
      if (instances.has(instance)) fail(); instances.add(instance);
      if (String(c.getFirstPropertyValue('status')).toUpperCase()!=='CANCELLED' && !c.hasProperty('dtstart')) fail();
      for (const prop of ['dtstart','dtend','recurrence-id']) checkZone(c.getFirstProperty(prop)?.getParameter('tzid'));
      for (const prop of c.getAllProperties('rrule')) {
        const r=prop.getFirstValue();
        if (!['DAILY','WEEKLY','MONTHLY','YEARLY'].includes(r.freq) || r.count>10000) fail();
      }
    }
    if (uids.size!==1 || seen.has([...uids][0])) fail(); seen.add([...uids][0]);
    const expanded=expand(row.ical,0,lo,hi,timezone);
    for (const e of expanded) {
      if (!Number.isFinite(e.startMs) || !Number.isFinite(e.endMs) || e.endMs<e.startMs) fail();
      events.push({uid:'ical:'+createHash('sha256').update(calendar.id+'\0'+e.uid).digest('hex'),
        calendarId:calendar.id,calendarName:calendar.name,color:calendar.color,cal:0,
        title:e.title.slice(0,500),allDay:e.allDay,start:e.start,end:e.end});
      if (events.length>2000) fail();
    }
  }
  return events.sort((a,b)=>a.start.localeCompare(b.start)||a.uid.localeCompare(b.uid));
}
if (process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href) {
  try {
    let size=0;const parts=[];
    for await (const part of process.stdin) { if ((size+=part.length)>MAX) fail();parts.push(part); }
    process.stdout.write(JSON.stringify(normalize(JSON.parse(Buffer.concat(parts).toString('utf8'))))+'\n');
  } catch { process.stderr.write('Calendar normalization failed\n');process.exitCode=1; }
}
