// Pure projections for the isolated Linux-local demonstration build.
// Dates/times are normalized on Linux; no ICS parsing or provider credentials here.
export function reminderKey(item) {
  return JSON.stringify([item.listId, item.uid, item.recurrenceId || '']);
}

export function reminderViews(items, selectedLists) {
  const selected = new Set(selectedLists), seen = new Set();
  const tasks = [], events = [];
  if (items.length > 2000) throw new Error('Reminder snapshot too large');
  for (const item of items) {
    if (!selected.has(item.listId)) continue;
    if (!item.uid || !item.listId || typeof item.title !== 'string' || !item.version) throw new Error('Invalid reminder');
    const id = reminderKey(item);
    if (seen.has(id)) throw new Error('Duplicate reminder identity');
    seen.add(id);
    if (item.completed || item.cancelled) continue;
    const common = { id, content: item.title, section: item.listId, version: item.version,
      recurring: !!item.recurring, canComplete: !item.recurring };
    if (!item.due) { tasks.push(common); continue; }
    const { day, at } = item.due;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(day) || !Number.isFinite(Date.parse(day + 'T00:00:00Z')) ||
        new Date(day + 'T00:00:00Z').toISOString().slice(0, 10) !== day ||
        (at && (!/Z$/.test(at) || !Number.isFinite(Date.parse(at))))) throw new Error('Invalid reminder due date');
    // A due marker is not an appointment. Date-only markers have exclusive ends.
    const tomorrow = new Date(day + 'T00:00:00Z'); tomorrow.setUTCDate(tomorrow.getUTCDate() + 1);
    events.push({ ...common, uid: 'reminder:' + id, kind: 'reminder', title: item.title,
      allDay: !at, start: at || day, end: at || tomorrow.toISOString().slice(0, 10), dueDay: day });
  }
  events.sort((a, b) => a.start.localeCompare(b.start) || a.id.localeCompare(b.id));
  return { tasks, events };
}

// State machine for a future UI: failures retain last-good data, never imply completion.
export function reconcileReminders(previous, result) {
  if (!result.ok) return { ...previous, stale: true, error: result.error || 'Sync unavailable' };
  return { items: result.items, stale: false, error: null, lastSuccess: result.at };
}

// Adapter records already have opaque IDs and normalized due dates.
export function projectReminders(snapshot) {
  if (!Array.isArray(snapshot.items) || snapshot.items.length > 500) throw new Error('Invalid task snapshot');
  const tasks = [], events = [], seen = new Set();
  for (const item of snapshot.items) {
    if (!/^[a-f0-9]{64}$/.test(item.id) || seen.has(item.id) || typeof item.title !== 'string') throw new Error('Invalid task identity');
    seen.add(item.id);
    if (item.completed || item.cancelled) continue;
    const task = { id: item.id, content: item.title, section: 'pf1007l-test', version: item.version,
      due: item.due?.day, canComplete: !snapshot.stale && !item.recurring,
      note: item.recurring ? 'Recurring · complete on iPhone' : null };
    tasks.push(task);
    if (item.due) {
      const day = item.due.day, end = new Date(day + 'T00:00:00Z'); end.setUTCDate(end.getUTCDate() + 1);
      events.push({ uid: 'reminder:' + item.id, kind: 'reminder', cal: 1, title: item.title, task,
        dueDay: day, allDay: !item.due.at, start: item.due.at || day,
        end: item.due.at || end.toISOString().slice(0, 10) });
    }
  }
  return { tasks, events };
}
