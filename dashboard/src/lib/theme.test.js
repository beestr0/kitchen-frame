import test from 'node:test';
import assert from 'node:assert/strict';
import { resolveTheme } from './theme.js';
const weather = { days: [{ date: '2026-11-13', sunrise: '2026-11-13T07:23:00', sunset: '2026-11-13T17:31:00' }] };
const at = (time) => new Date('2026-11-13T' + time);
test('automatic uses configured sunrise and sunset, including exact boundaries', () => {
  for (const [time, expected] of [['07:22:59', 'dark'], ['07:23:00', 'light'], ['17:30:59', 'light'], ['17:31:00', 'dark']]) {
    assert.equal(resolveTheme('auto', at(time), weather), expected);
  }
});
test('manual themes override solar and fallback times', () => {
  assert.equal(resolveTheme('light', at('01:00:00'), weather), 'light');
  assert.equal(resolveTheme('dark', at('12:00:00'), weather), 'dark');
});
test('missing, stale, malformed or reversed solar data uses original local 7–19 fallback', () => {
  for (const w of [null, {}, {days: []}, {days: [{...weather.days[0], date: '2026-11-12'}]}, {days: [{...weather.days[0], sunrise: 'bad'}]}, {days: [{...weather.days[0], sunrise: '2026-11-13T20:00'}]}]) {
    for (const [time, theme] of [['06:59:59','dark'], ['07:00:00','light'], ['18:59:59','light'], ['19:00:00','dark']]) {
      assert.equal(resolveTheme('auto', at(time), w), theme);
    }
  }
});
