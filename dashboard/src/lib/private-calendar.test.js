import { test } from 'node:test';
import assert from 'node:assert/strict';
import { reconcileCalendar,combineCalendar } from './private-calendar.js';
import { calVars,eventsOn } from './format.js';
const calendar={id:'work',name:'Work',color:'#123456'};
const event={uid:'ical:'+'a'.repeat(64),calendarId:'work',title:'Invented',allDay:true,start:'2026-11-14',end:'2026-11-15'};
const response={source:'private-caldav',available:true,stale:false,calendars:[calendar],events:[event],updated:'2026-11-14T12:00:00Z'};
test('real calendar replaces fictional appointments but retains visually distinct reminders',()=>{
 const state=reconcileCalendar({},response),reminder={uid:'reminder:x',kind:'reminder',start:'2026-11-14'};
 const events=combineCalendar(state,[{uid:'fictional',start:'2026-11-14'}],[reminder]);
 assert.equal(events.length,2);assert.ok(!events.some(e=>e.uid==='fictional'));assert.equal(events[1].kind,'reminder');
 assert.match(calVars(events[0]),/--c:#123456/);
});
test('cold unavailable live calendar never returns fictional events; outage retains prior private events',()=>{
 const cold=reconcileCalendar({events:[]},{source:'private-caldav',available:false});
 assert.deepEqual(combineCalendar(cold,[event],[]),[]);
 const good=reconcileCalendar({},response),bad=reconcileCalendar(good,{source:'private-caldav',available:false});
 assert.equal(bad.events,good.events);assert.equal(bad.stale,true);
 assert.equal(reconcileCalendar(good,{...response,events:[]}).events.length,0);
});
test('malformed calendar batch fails before replacing last good state',()=>{
 for(const e of [{...event,calendarId:'unselected'},{...event,start:'2026-02-30'}, {...event,title:null}])assert.throws(()=>reconcileCalendar({}, {...response,events:[event,e]}));
 assert.throws(()=>reconcileCalendar({}, {...response,events:[event,event]}));
 assert.equal(reconcileCalendar({}, {source:'disabled'}).enabled,false);
});
test('timed events spanning midnight appear on each touched day with exclusive end',()=>{
 const a=new Date(2026,10,14,23),b=new Date(2026,10,16,0);
 const events=[{uid:'overnight',allDay:false,start:a.toISOString(),end:b.toISOString()}];
 assert.equal(eventsOn(events,new Date(2026,10,14)).length,1);assert.equal(eventsOn(events,new Date(2026,10,15)).length,1);
 assert.equal(eventsOn(events,new Date(2026,10,16)).length,0);
});
