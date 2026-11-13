import { restore, newSession, toggle, minutes } from './focus.js';
let saved;
try { saved = JSON.parse(localStorage.getItem('frame-focus')); } catch {}
export const focus = $state(restore(saved));
function persist() {
  try { localStorage.setItem('frame-focus', JSON.stringify(focus)); } catch {}
}
export function toggleFocus() { focus.session = toggle(focus.session, Date.now()); persist(); }
export function resetFocus(phase = focus.session.phase) { focus.session = newSession(phase, focus.durations); persist(); }
export function setDuration(phase, value) {
  focus.durations[phase] = minutes(value, focus.durations[phase]);
  if (!focus.session.running && focus.session.phase === phase) resetFocus(phase);
  persist();
}
