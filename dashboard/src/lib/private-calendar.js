// Calendar-only source transition. No event/credential persistence in browser storage.
export function reconcileCalendar(previous, response) {
  if (response?.source === 'disabled') return { ...previous, enabled: false };
  if (response?.source !== 'private-caldav') throw Error('Invalid calendar source');
  if (response.available === false) return { ...previous, enabled: true, stale: true, error: 'Calendar temporarily unavailable' };
  if (!Array.isArray(response.events) || response.events.length>4000 || !Array.isArray(response.calendars)) throw Error('Invalid calendar snapshot');
  const calendars=new Map();
  for (const c of response.calendars) {
    if (typeof c.id!=='string' || calendars.has(c.id) || typeof c.name!=='string' || !/^#[a-fA-F0-9]{6}$/.test(c.color)) throw Error('Invalid calendar metadata');
    calendars.set(c.id,c);
  }
  const seen=new Set();
  const events=response.events.map(e=>{
    const c=calendars.get(e.calendarId), key=e.uid+'|'+e.start;
    if (!c || !/^ical:[a-f0-9]{64}$/.test(e.uid) || seen.has(key) || typeof e.title!=='string' || typeof e.allDay!=='boolean') throw Error('Invalid calendar event');
    const valid=x=>typeof x==='string' && (e.allDay ? /^\d{4}-\d{2}-\d{2}$/.test(x) && new Date(x+'T00:00:00Z').toISOString().slice(0,10)===x : /Z$/.test(x) && Number.isFinite(Date.parse(x)));
    if (!valid(e.start)||!valid(e.end)||e.end<e.start) throw Error('Invalid calendar date');
    seen.add(key);
    return {uid:e.uid,calendarId:c.id,calendarName:c.name,color:c.color,cal:0,
      title:e.title,allDay:e.allDay,start:e.start,end:e.end};
  });
  return {enabled:true,events,calendars:response.calendars,updated:response.updated,
    stale:response.stale!==false,window:response.window,error:response.error||null};
}

export function combineCalendar(privateSource, demoEvents, reminders) {
  const events=privateSource.enabled ? privateSource.events : demoEvents;
  return [...(events||[]),...(reminders||[])].sort((a,b)=>a.start.localeCompare(b.start));
}
