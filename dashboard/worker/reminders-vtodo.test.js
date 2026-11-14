import { test } from 'node:test';
import assert from 'node:assert/strict';
import ICAL from 'ical.js';
import { completeVtodo } from './reminders-vtodo.js';
const resource = (extra = '') => ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//PF1007L Demo//EN',
  'BEGIN:VTODO', 'UID:demo', 'SUMMARY:Demonstration', 'DUE;VALUE=DATE:20261115',
  'DESCRIPTION:Keep this', 'X-DEMO:keep', extra, 'BEGIN:VALARM', 'ACTION:DISPLAY',
  'DESCRIPTION:Demo alarm', 'TRIGGER:-PT15M', 'END:VALARM', 'END:VTODO', 'END:VCALENDAR'].filter(Boolean).join('\r\n');
test('completion preserves due date, unknown fields, notes and alarms; is idempotent', () => {
  const output = completeVtodo(resource(), 'demo', new Date('2026-11-14T12:00:00Z'));
  const task = new ICAL.Component(ICAL.parse(output)).getFirstSubcomponent('vtodo');
  assert.equal(task.getFirstPropertyValue('status'), 'COMPLETED');
  assert.equal(task.getFirstPropertyValue('percent-complete'), 100);
  assert.equal(task.getFirstPropertyValue('completed').toString(), '2026-11-14T12:00:00Z');
  assert.equal(task.getFirstPropertyValue('due').toString(), '2026-11-15');
  assert.equal(task.getFirstPropertyValue('x-demo'), 'keep');
  assert.equal(task.getFirstPropertyValue('description'), 'Keep this');
  assert.equal(task.getAllSubcomponents('valarm').length, 1);
  assert.equal(completeVtodo(output, 'demo'), output);
});
test('recurring tasks, detached instances, wrong UID and cancelled tasks fail closed', () => {
  for (const extra of ['RRULE:FREQ=DAILY', 'RDATE;VALUE=DATE:20261116', 'RECURRENCE-ID;VALUE=DATE:20261115']) {
    assert.throws(() => completeVtodo(resource(extra), 'demo'), /Recurring/);
  }
  assert.throws(() => completeVtodo(resource(), 'other'), /Unexpected/);
  assert.throws(() => completeVtodo(resource('STATUS:CANCELLED'), 'demo'), /cancelled/);
});


test('exclusion-only recurrence also fails closed before any completion serialization', () => {
  for (const property of ['EXDATE;VALUE=DATE:20261115', 'EXRULE:FREQ=WEEKLY;BYDAY=SA,SU']) {
    const text = 'BEGIN:VCALENDAR\r\nVERSION:2.0\r\nBEGIN:VTODO\r\nUID:fixture\r\nSUMMARY:Invented\r\n'+property+'\r\nEND:VTODO\r\nEND:VCALENDAR\r\n';
    assert.throws(() => completeVtodo(text, 'fixture'), /Recurring/);
  }
});
