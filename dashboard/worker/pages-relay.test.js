import { test } from 'node:test';
import assert from 'node:assert/strict';
import relay from '../hosting/pages-relay.js';

test('Pages API relay fails closed when its service binding is absent', async () => {
  const response = await relay.fetch(new Request('https://desk.test/api/calendar'), {});
  assert.equal(response.status, 503);
  assert.equal(response.headers.get('Cache-Control'), 'no-store');
});

test('Pages passes the original request and response to the private API unchanged', async () => {
  for (const init of [
    { method: 'POST', headers: { Authorization: 'Bearer invented' }, body: 'invented task' },
    { headers: { Upgrade: 'websocket' } },
  ]) {
    const req = new Request('https://desk.test/api/messages/live', init);
    const response = new Response('test');
    const result = await relay.fetch(req, { DESK_API: { fetch: async actual => {
      assert.equal(actual, req);
      return response;
    } } });
    assert.equal(result, response);
  }
});

test('Pages static content uses assets without calling the private API', async () => {
  const response = await relay.fetch(new Request('https://desk.test/'), {
    ASSETS: { fetch: async () => new Response('static shell') },
    DESK_API: { fetch() { throw Error('Static request reached API'); } },
  });
  assert.equal(await response.text(), 'static shell');
});
