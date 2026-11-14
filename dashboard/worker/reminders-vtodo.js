// Preparation only. Not imported by either Worker or the running LAN proxy.
import ICAL from 'ical.js';

export function completeVtodo(text, uid, now = new Date()) {
  if (typeof text !== 'string' || text.length > 256 * 1024) throw new Error('Invalid task resource');
  const root = new ICAL.Component(ICAL.parse(text));
  const todos = root.getAllSubcomponents('vtodo');
  if (root.name !== 'vcalendar' || todos.length !== 1 || root.getAllSubcomponents('vevent').length ||
      todos[0].getFirstPropertyValue('uid') !== uid) throw new Error('Unexpected task resource');
  const todo = todos[0];
  // Never mark an entire recurring series complete by guessing occurrence semantics.
  if (['rrule', 'rdate', 'recurrence-id'].some((name) => todo.hasProperty(name))) {
    throw new Error('Recurring completion requires compatibility validation');
  }
  if (todo.getFirstPropertyValue('status') === 'CANCELLED') throw new Error('Task cancelled');
  if (todo.getFirstPropertyValue('status') === 'COMPLETED') return text;
  const stamp = ICAL.Time.fromJSDate(now, true);
  todo.updatePropertyWithValue('status', 'COMPLETED');
  todo.updatePropertyWithValue('percent-complete', 100);
  todo.updatePropertyWithValue('completed', stamp);
  todo.updatePropertyWithValue('dtstamp', stamp);
  todo.updatePropertyWithValue('last-modified', stamp);
  todo.updatePropertyWithValue('sequence', Number(todo.getFirstPropertyValue('sequence') || 0) + 1);
  // Preserve DUE, DTSTART, alarms, descriptions, timezone definitions and unknown properties.
  return root.toString();
}
