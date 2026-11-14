import { test } from 'node:test';
import assert from 'node:assert/strict';
import desk from './desk.js';

test('desk API fails closed without the production secret, including agent routes', async () => {
  for (const path of ['/api/calendar', '/api/messages', '/api/messages/live', '/api/recipes']) {
    const response = await desk.fetch(new Request('https://desk.test' + path), {}, {});
    assert.equal(response.status, 503);
    assert.equal(response.headers.get('Cache-Control'), 'no-store');
  }
});

test('desk private API rejects missing/wrong keys and accepts the configured key', async () => {
  const env = { DASHBOARD_KEY: 'invented-test-key' };
  for (const key of ['', 'wrong', 'invented-test-key']) {
    const response = await desk.fetch(new Request('https://desk.test/api/photos', {
      headers: { Authorization: 'Bearer ' + key },
    }), env, {});
    assert.equal(response.status, key === env.DASHBOARD_KEY ? 200 : 401);
    assert.equal(response.headers.get('Referrer-Policy'), 'no-referrer');
  }
});

test('desk static HTML stays public and uncached without a secret', async () => {
  const response = await desk.fetch(new Request('https://desk.test/'), {
    ASSETS: { fetch: async () => new Response('<h1>Public shell</h1>', { headers: { 'Content-Type': 'text/html' } }) },
  }, {});
  assert.equal(response.status, 200);
  assert.equal(response.headers.get('Cache-Control'), 'no-store');
  assert.equal(response.headers.get('X-Content-Type-Options'), 'nosniff');
});
