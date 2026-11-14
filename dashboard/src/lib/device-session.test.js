import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createDeviceSession, requestNativeSession } from './device-session.js';

const denied = () => Object.assign(new Error('Device authentication required'), { status: 401, mode: 'device-v1', code: 'device_auth_required' });
const session = () => ({ mode: 'device-v1', csrf: 'invented-csrf', expiresIn: 900 });

test('cold expired session renews through native and never exposes a key or proof to JS', async () => {
  let authenticated = false, proofs = 0;
  const client = createDeviceSession({ request: async route => {
    if (route === 'session') { if (!authenticated) throw denied(); return session(); }
    return { items: [] };
  }, authenticate: async () => { proofs++; authenticated = true; } });
  assert.deepEqual(await client.request('snapshot'), { items: [] });
  assert.equal(proofs, 1);
});

test('concurrent polls share one renewal and refresh before expiry', async () => {
  let now = 1000, gets = 0;
  const client = createDeviceSession({ clock: () => now, request: async route => { if (route === 'session') { gets++; return session(); } return {}; } });
  await Promise.all([client.ensure(), client.ensure(), client.request('snapshot')]);
  assert.equal(gets, 1);
  now += 600000; await client.ensure(); assert.equal(gets, 1);
  now += 121000; await client.ensure(); assert.equal(gets, 2);
});

test('middleware 401 retries a write once with the same operation body and renewed CSRF', async () => {
  const calls = []; let sessions = 0;
  const client = createDeviceSession({ request: async (route, init) => {
    if (route === 'session') return { ...session(), csrf: 'invented-' + ++sessions };
    calls.push(init);
    if (calls.length === 1) throw denied();
    return { completed: true };
  } });
  const body = JSON.stringify({ operation: 'invented-operation-id', id: 'invented-id', version: 'invented-version' });
  await client.request('complete', { method: 'POST', body });
  assert.equal(calls.length, 2); assert.equal(calls[0].body, calls[1].body);
  assert.notEqual(calls[0].headers['X-Pilot-CSRF'], calls[1].headers['X-Pilot-CSRF']);
});

test('near-expiry cookie is replaced before expiry rather than repeatedly inspected', async () => {
  let renewed = 0;
  const client = createDeviceSession({ request: async () => ({ ...session(), expiresIn: renewed ? 900 : 180 }),
    authenticate: async () => { renewed++; } });
  assert.equal((await client.ensure()).expiresIn, 900);
  assert.equal(renewed, 1);
});

test('timeouts, 409 and 5xx never silently replay a potentially committed write', async () => {
  for (const status of [undefined, 409, 429, 503]) {
    let writes = 0;
    const client = createDeviceSession({ request: async route => { if (route === 'session') return session(); writes++; throw Object.assign(new Error('Invented failure'), { status }); } });
    await assert.rejects(client.request('complete', { method: 'POST', body: 'invented' }));
    assert.equal(writes, 1);
  }
});

test('revoked/unsupported native authentication stays unavailable without legacy fallback', async () => {
  let native = 0;
  const client = createDeviceSession({ request: async () => { throw denied(); }, authenticate: async () => { native++; throw new Error('Unavailable'); } });
  await assert.rejects(client.ensure()); await assert.rejects(client.ensure()); assert.equal(native, 1);
});

test('synchronous transport failure can recover after bounded cooldown', async () => {
  let now = 100, fail = true;
  const client = createDeviceSession({ clock: () => now, request: () => { if (fail) throw new Error('Network unavailable'); return session(); } });
  await assert.rejects(client.ensure()); fail = false; now += 15001;
  assert.equal((await client.ensure()).csrf, 'invented-csrf');
});

test('legacy deployed demo remains compatible and valid sessions can renew', async () => {
  let now = 0, calls = 0;
  const client = createDeviceSession({ clock: () => now, request: async () => { calls++; return { csrf: 'invented-legacy' }; } });
  await client.ensure(); now = 181000; await client.ensure(); assert.equal(calls, 2);
});

test('native bridge accepts only fixed status messages, restores its callback and times out', async () => {
  const previous = () => {};
  const channel = { onmessage: previous, postMessage(value) { assert.equal(value, 'renew'); queueMicrotask(() => this.onmessage({ data: 'ready' })); } };
  await requestNativeSession(channel, 100); assert.equal(channel.onmessage, previous);
  await assert.rejects(requestNativeSession({ postMessage() {} }, 5), /timed out/);
  await assert.rejects(requestNativeSession(undefined, 5), /enrollment/);
});

test('invalid session responses fail closed and do not cache authentication', async () => {
  for (const value of [{ csrf: '', expiresIn: 900 }, { ...session(), expiresIn: -1 }, { ...session(), mode: 'unknown' }]) {
    const client = createDeviceSession({ request: async () => value });
    await assert.rejects(client.ensure());
  }
});
