import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cachedWeather, WEATHER_REFRESH_MS } from './weather-cache.js';
import desk from './desk.js';

const payload = () => ({ timezone: 'America/Indiana/Indianapolis',
  current: { temperature_2m: 62.3, apparent_temperature: 60, weather_code: 2, is_day: 1 },
  daily: { time: Array.from({length:5},(_,i)=>`2026-11-${14+i}`), temperature_2m_max:[65,66,67,68,69], temperature_2m_min:[45,46,47,48,49], weather_code:[2,3,61,0,1], precipitation_probability_max:[5,10,80,0,0], sunrise:Array(5).fill('2026-11-14T07:25'), sunset:Array(5).fill('2026-11-14T17:30') } });
function setup(){ const data=new Map();return {WEATHER_ENABLED:'true',WEATHER_LAT:'39.7684',WEATHER_LON:'-86.1581',WEATHER_TZ:'America/Indiana/Indianapolis',WEATHER_LOCATION:'Indianapolis',DASHBOARD_KEY:'invented',CALENDAR:{get:async k=>data.has(k)?JSON.parse(data.get(k)):null,put:async(k,v)=>data.set(k,v)}} }

test('weather shares requests, persists last-good forecast, and throttles failed refreshes', async()=>{
 const original=globalThis.fetch;try{const env=setup();let calls=0;
 globalThis.fetch=async(url,init)=>{calls++;assert.equal(new URL(url).searchParams.get('timezone'),'America/Indiana/Indianapolis');assert(init.signal);return Response.json(payload())};
 const now=Date.now();const [a,b]=await Promise.all([cachedWeather(env,now),cachedWeather(env,now)]);assert.equal(calls,1);assert.deepEqual(a,b);assert.equal(a.days.length,5);assert.equal(a.location,'Indianapolis');assert.equal(a.stale,false);
 assert.deepEqual(await cachedWeather(env,now+1000),a);assert.equal(calls,1);
 globalThis.fetch=async()=>{calls++;throw Error('invented outage')};
 const stale=await cachedWeather(env,now+WEATHER_REFRESH_MS+1);assert.equal(calls,2);assert.equal(stale.stale,true);assert.equal(stale.updated,a.updated);assert.deepEqual(stale.days,a.days);
 await cachedWeather(env,now+WEATHER_REFRESH_MS+100);assert.equal(calls,2);
 globalThis.fetch=async()=>{calls++;return Response.json(payload())};assert.equal((await cachedWeather(env,now+2*WEATHER_REFRESH_MS+2)).stale,false);assert.equal(calls,3);
 }finally{globalThis.fetch=original}
});
test('malformed provider data cannot overwrite last-good forecast',async()=>{const original=globalThis.fetch;try{const env=setup(),now=Date.now();globalThis.fetch=async()=>Response.json(payload());const first=await cachedWeather(env,now);globalThis.fetch=async()=>{const p=payload();p.daily.temperature_2m_max[0]=null;return Response.json(p)};const stale=await cachedWeather(env,now+WEATHER_REFRESH_MS);assert.equal(stale.stale,true);assert.deepEqual(stale.days,first.days)}finally{globalThis.fetch=original}});
test('cold outage reports unavailable and backs off rather than caching fabricated data',async()=>{const original=globalThis.fetch;try{let calls=0;globalThis.fetch=async()=>{calls++;throw Error('outage')};const env=setup(),now=Date.now();await assert.rejects(cachedWeather(env,now),/temporarily unavailable/);await assert.rejects(cachedWeather(env,now+1000));assert.equal(calls,1)}finally{globalThis.fetch=original}});
test('weather configuration changes cannot reuse another location cache',async()=>{const original=globalThis.fetch;try{let calls=0;globalThis.fetch=async()=>{calls++;return Response.json(payload())};const env=setup();await cachedWeather(env);await cachedWeather({...env,WEATHER_LAT:'40'});assert.equal(calls,2)}finally{globalThis.fetch=original}});
test('desk weather remains authenticated, GET-only and explicitly enabled',async()=>{const env=setup();for(const [key,method,enabled,status]of[['','GET','true',401],['invented','POST','true',405],['invented','GET','false',503]]){const r=await desk.fetch(new Request('https://desk.test/api/weather',{method,headers:{Authorization:'Bearer '+key}}),{...env,WEATHER_ENABLED:enabled},{});assert.equal(r.status,status);assert.equal(r.headers.get('Cache-Control'),'no-store')}});
test('weather schedule never invokes calendar fetches',async()=>{const original=globalThis.fetch;try{globalThis.fetch=async u=>{assert.equal(new URL(u).hostname,'api.open-meteo.com');return Response.json(payload())};const work=[];await desk.scheduled({},setup(),{waitUntil:p=>work.push(p)});await Promise.all(work);assert.equal(work.length,1)}finally{globalThis.fetch=original}});
