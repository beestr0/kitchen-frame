// In-memory protocol simulator, not a server or CalDAV client. No network or disk writes.
import { reminderKey, reminderViews, reconcileReminders } from '../../dashboard/src/lib/reminders.js';

export function demoReminders() {
  return [
    { listId: 'desk', uid: 'one', title: 'Demo: review desk layout', version: '1', completed: false },
    { listId: 'home', uid: 'one', title: 'Demo: water plant', version: '1', completed: false,
      due: { day: '2026-11-15' } },
    { listId: 'desk', uid: 'two', title: 'Demo: test timed reminder', version: '1', completed: false,
      due: { day: '2026-11-15', at: '2026-11-15T20:00:00Z' } },
    { listId: 'home', uid: 'repeat', title: 'Demo: recurring reminder (completion gated)', version: '1',
      recurring: true, completed: false, due: { day: '2026-11-16' } },
  ];
}

export class DemoTaskStore {
  constructor() { this.items = demoReminders(); }
  snapshot() { return structuredClone(this.items); }
  // Simulates conditional PUT: reject obsolete revisions instead of overwriting phone edits.
  complete(id, version, selectedLists) {
    const item = this.items.find((x) => reminderKey(x) === id && selectedLists.includes(x.listId));
    if (!item) throw new Error('Task unavailable');
    if (item.version !== version) throw new Error('Conflict: refresh before retrying');
    if (item.recurring) throw new Error('Recurring completion requires compatibility validation');
    item.completed = true; item.version = String(Number(item.version) + 1);
  }
  phoneEdit(id, patch) {
    const item = this.items.find((x) => reminderKey(x) === id);
    if (!item) throw new Error('Task unavailable');
    for (const key of Object.keys(patch)) {
      if (!['title', 'due', 'completed'].includes(key)) throw new Error('Invalid demo edit');
    }
    Object.assign(item, patch, { version: String(Number(item.version) + 1) });
  }
}

if (process.argv[1] && import.meta.url === new URL('file://' + process.argv[1]).href) {
  const store = new DemoTaskStore(), selected = ['desk', 'home'];
  const first = reminderViews(store.snapshot(), selected);
  console.log('Demo only; no accounts, network, files or services.');
  console.log('Initial:', JSON.stringify(first, null, 2));
  store.complete(first.tasks[0].id, first.tasks[0].version, selected);
  store.phoneEdit(reminderKey(store.items[1]), { completed: true });
  const state = reconcileReminders({}, { ok: true, items: store.snapshot(), at: 'demo' });
  console.log('After frame + simulated phone completion:', JSON.stringify(reminderViews(state.items, selected), null, 2));
}
