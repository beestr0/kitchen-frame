import test from 'node:test';
import assert from 'node:assert/strict';
import { DEFAULT_DURATIONS, minutes, newSession, remaining, toggle, restore } from './focus.js';
test('timer pauses and resumes without losing elapsed time', () => {
  let s = toggle(newSession('focus', DEFAULT_DURATIONS), 1000);
  assert.equal(remaining(s, 61000), 24 * 60000);
  s = toggle(s, 61000);
  assert.equal(remaining(s, 99999999), 24 * 60000);
  s = toggle(s, 100000);
  assert.equal(remaining(s, 160000), 23 * 60000);
});
test('persisted deadline survives a reload and throttled ticks; completion never goes negative', () => {
  const session = toggle(newSession('break', DEFAULT_DURATIONS), 1000);
  const restored = restore(JSON.parse(JSON.stringify({session, durations: DEFAULT_DURATIONS})));
  assert.equal(remaining(restored.session, 301000), 0);
  assert.equal(remaining(restored.session, 99999999), 0);
  assert.equal(toggle(toggle(restored.session, 301000), 302000).running, false);
  assert.equal(newSession('focus', restored.durations).remaining, 25 * 60000);
});
test('duration limits and invalid saved state recover safely', () => {
  for (const n of ['', 0, -1, 121, 1.5, NaN, Infinity]) assert.equal(minutes(n, 25), 25);
  assert.equal(minutes('120',25),120);
  for (const saved of [null, {}, {session:{phase:'invalid'}}, {session:{phase:'focus',running:true,remaining:100,deadline:null}}]) {
    assert.deepEqual(restore(saved).session, newSession('focus', DEFAULT_DURATIONS));
  }
});
