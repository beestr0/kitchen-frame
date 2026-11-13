import test from 'node:test';
import assert from 'node:assert/strict';
import worker from './index.js';

test('iCloud webcal is fetched over HTTPS; failed refresh retains last good events', async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = originalFetch; });
  const store = new Map();
  const env = {
    DASHBOARD_KEY: 'local-test-only', CALENDAR_URLS: 'webcal://calendar.example.test/shared',
    CALENDAR: {get: async (k) => store.has(k) ? JSON.parse(store.get(k)) : null, put: async (k,v) => store.set(k,v)},
  };
  const eventDate = new Date(Date.now() + 86400000).toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z/, 'Z');
  let offline = false;
  globalThis.fetch = async (url) => {
    assert.equal(url, 'https://calendar.example.test/shared');
    if (offline) return new Response('Unavailable', {status:503});
    return new Response(['BEGIN:VCALENDAR','VERSION:2.0','BEGIN:VEVENT','UID:desk-fixture','DTSTAMP:'+eventDate,'DTSTART:'+eventDate,'DURATION:PT1H','SUMMARY:Desk planning','END:VEVENT','END:VCALENDAR'].join('\r\n'));
  };
  const refresh = () => worker.fetch(new Request('https://desk.example.test/api/calendar?refresh', {headers:{Authorization:'Bearer local-test-only'}}), env, {});
  const first = await (await refresh()).json();
  assert.equal(first.events.length, 1);
  assert.equal(first.events[0].title, 'Desk planning');
  assert.deepEqual(first.errors, []);
  offline = true;
  const second = await (await refresh()).json();
  assert.deepEqual(second.events, first.events);
  assert.deepEqual(second.errors, [{cal:0,error:'HTTP 503'}]);
  assert.equal(second.calendars, 1);
});
