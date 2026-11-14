import { test } from 'node:test';
import assert from 'node:assert/strict';
import { reminderKey, reminderViews, reconcileReminders, projectReminders } from './reminders.js';
import { eventsOn } from './format.js';
import { DemoTaskStore } from '../../../deploy/reminders/demo.mjs';

test('selected lists, namespaced IDs, due dates, timed markers and recurring gates', () => {
  const store = new DemoTaskStore();
  const view = reminderViews(store.snapshot(), ['desk', 'home']);
  assert.equal(view.tasks.length, 1); assert.equal(view.events.length, 3);
  assert.equal(new Set([...view.tasks, ...view.events].map(x => x.id)).size, 4);
  assert.equal(view.events[0].end, '2026-11-16');
  assert.equal(view.events[1].start, '2026-11-15T20:00:00Z');
  assert.equal(view.events[2].canComplete, false);
  assert.equal(reminderViews(store.snapshot(), []).events.length, 0);
  assert.equal(reminderViews(store.snapshot(), ['desk']).events.length, 1);
});
test('frame completion and phone edits reconcile; stale writes cannot lose an edit', () => {
  const store = new DemoTaskStore(), [item] = store.snapshot(), id = reminderKey(item);
  store.phoneEdit(id, { title: 'Edited on phone', due: { day: '2026-11-20' } });
  assert.throws(() => store.complete(id, '1', ['desk']), /Conflict/);
  let view = reminderViews(store.snapshot(), ['desk']);
  assert.equal(view.tasks.length, 0); assert.equal(view.events[1].title, 'Edited on phone');
  assert.throws(() => store.complete(id, '2', ['home']), /unavailable/);
  store.complete(id, '2', ['desk']);
  view = reminderViews(store.snapshot(), ['desk']); assert.equal(view.events.length, 1);
  assert.equal(store.snapshot()[0].completed, true);
  store.phoneEdit(id, { completed: false });
  assert.equal(reminderViews(store.snapshot(), ['desk']).events.length, 2);
});
test('failed snapshots retain last-good; authoritative empty success removes old tasks', () => {
  const old = { items: new DemoTaskStore().snapshot(), lastSuccess: 'before' };
  const stale = reconcileReminders(old, { ok: false });
  assert.equal(stale.items, old.items); assert.equal(stale.stale, true);
  assert.equal(stale.lastSuccess, 'before');
  assert.deepEqual(reconcileReminders(stale, { ok: true, items: [], at: 'after' }),
    { items: [], stale: false, error: null, lastSuccess: 'after' });
});
test('duplicate identities and malformed dates fail rather than publish ambiguous data', () => {
  const items = new DemoTaskStore().snapshot();
  assert.throws(() => reminderViews([items[0], items[0]], ['desk']), /Duplicate/);
  items[1].due.day = '2026-02-30';
  assert.throws(() => reminderViews(items, ['home']), /due date/);
});

test('demo bridge projection keeps dated tasks in Tasks and the correct Calendar day', () => {
  const item = { id: 'a'.repeat(64), title: 'Phone task', version: 'v1', due: { day: '2026-11-14' } };
  const view = projectReminders({ items: [item], stale: false });
  assert.equal(view.tasks.length, 1); assert.equal(view.events.length, 1);
  assert.equal(view.events[0].task.id, item.id);
  assert.equal(eventsOn(view.events, new Date(2026, 10, 14)).length, 1);
  assert.equal(eventsOn(view.events, new Date(2026, 10, 15)).length, 0);
  assert.equal(projectReminders({ items: [{ ...item, due: null }] }).events.length, 0);
  assert.equal(projectReminders({ items: [item], stale: true }).tasks[0].canComplete, false);
  assert.equal(projectReminders({ items: [{ ...item, completed: true }] }).tasks.length, 0);
});
