import { test, mock } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import http from 'node:http';
import { Readable, Writable, PassThrough } from 'node:stream';
import { remindersDemoHandler } from './reminders-demo-proxy.mjs';

const prefix = '/__reminders-demo/';
const origin = 'https://beestr0.duckdns.org:8789';
const config = { remindersDemo: { enabled: true, uiDirectory: '/opt/pf1007l-reminders-bridge/ui' } };
const inventedKey = 'invented-proxy-test-credential-for-fixtures-only';

async function fixture(run) {
  const directory = mkdtempSync(join(tmpdir(), 'pf1007l-proxy-fixture-'));
  const previous = process.env.CREDENTIALS_DIRECTORY;
  writeFileSync(join(directory, 'reminders-demo-key'), inventedKey, { mode: 0o600 });
  process.env.CREDENTIALS_DIRECTORY = directory;
  try { await run(remindersDemoHandler(config, true)); }
  finally {
    mock.restoreAll();
    if (previous === undefined) delete process.env.CREDENTIALS_DIRECTORY;
    else process.env.CREDENTIALS_DIRECTORY = previous;
    rmSync(directory, { recursive: true });
  }
}

function request(method = 'POST', headers = {}, body = '{}') {
  const req = Readable.from(body ? [body] : []);
  Object.assign(req, { method, headers, pilotRemote: '192.0.2.23' });
  return req;
}
function response() {
  let body = '';
  const res = new Writable({ write(chunk, encoding, next) { body += chunk; next(); } });
  res.fields = {};
  res.setHeader = (name, value) => { res.fields[name] = value; };
  res.getHeader = name => res.fields[name];
  res.writeHead = (status, fields) => { res.status = status; Object.assign(res.fields, fields); };
  res.done = new Promise(resolve => res.on('finish', () => resolve(body)));
  return res;
}

test('reminder proxy is HTTPS-only, opt-in and fixed-directory', () => {
  assert.equal(remindersDemoHandler(config, false), null);
  assert.equal(remindersDemoHandler({}, true), null);
  assert.throws(() => remindersDemoHandler({ remindersDemo: { enabled: true, uiDirectory: '/other' } }, true));
});

test('device challenge/proof forwarding fixes backend and client identity and preserves HttpOnly cookie', () => fixture(async handle => {
  const calls = [];
  mock.method(http, 'request', (options, callback) => {
    calls.push(options);
    const upstream = new PassThrough(); upstream.resume();
    setImmediate(() => {
      const reply = Readable.from(['{"mode":"device-v1"}']);
      Object.assign(reply, { statusCode: 200, headers: { 'set-cookie': ['invented-fixture-cookie; Secure; HttpOnly'] } });
      callback(reply);
    });
    return upstream;
  });
  for (const route of ['device/challenge', 'device/prove']) {
    const res = response();
    assert.equal(handle(request('POST', { origin, 'content-type': 'application/json', 'x-pilot-key': 'spoofed', 'x-pilot-client': 'spoofed' }), res, new URL(origin + prefix + route)), true);
    assert.deepEqual(JSON.parse(await res.done), { mode: 'device-v1' });
    assert.equal(res.status, 200);
    assert.equal(res.fields['Set-Cookie'][0], 'invented-fixture-cookie; Secure; HttpOnly');
    assert.match(res.fields['Content-Security-Policy'], /frame-src 'none'; object-src 'none'/);
  }
  for (const call of calls) {
    assert.equal(call.hostname, '127.0.0.1'); assert.equal(call.port, 5240);
    assert.equal(call.headers['X-Pilot-Key'], inventedKey); assert.equal(call.headers['X-Pilot-Client'], '192.0.2.23');
    assert.equal(call.headers.origin, origin); assert.equal(call.method, 'POST');
  }
}));

test('wrong methods and query-bearing auth URLs never reach backend', () => fixture(async handle => {
  mock.method(http, 'request', () => { throw new Error('Unexpected forwarding'); });
  for (const [method, route, expected] of [['GET','device/prove',405], ['GET','device/challenge',405], ['POST','session',405], ['POST','device/prove?token=forbidden',400]]) {
    const res = response(); handle(request(method), res, new URL(origin+prefix+route));
    await res.done; assert.equal(res.status, expected);
  }
}));

test('ordinary dashboard paths do not enter reminder handling', () => fixture(async handle => {
  assert.equal(handle(request('GET'), response(), new URL(origin+'/api/weather')), false);
}));

test('backend outage gives a fixed error without disclosing transport details or credentials', () => fixture(async handle => {
  mock.method(http, 'request', () => {
    const upstream = new PassThrough(); upstream.resume();
    setImmediate(() => upstream.emit('error', new Error('invented sensitive transport detail')));
    return upstream;
  });
  const res = response(); handle(request('GET'), res, new URL(origin+prefix+'snapshot'));
  const body = await res.done;
  assert.equal(res.status,503); assert.equal(body,'{"error":"Demo tasks temporarily unavailable"}');
  assert.ok(!body.includes(inventedKey)); assert.ok(!body.includes('sensitive'));
}));
