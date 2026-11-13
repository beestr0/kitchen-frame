// Absolute deadlines avoid drift when WebView throttles timers or the view is unmounted.
export const DEFAULT_DURATIONS = { focus: 25, break: 5 };
export function minutes(value, fallback) {
  const n = Number(value);
  return Number.isInteger(n) && n >= 1 && n <= 120 ? n : fallback;
}
export function newSession(phase, durations) {
  return { phase, running: false, deadline: null, remaining: durations[phase] * 60000 };
}
export function remaining(session, now) {
  return Math.max(0, session.running ? session.deadline - now : session.remaining);
}
export function toggle(session, now) {
  const ms = remaining(session, now);
  return session.running
    ? { ...session, running: false, deadline: null, remaining: ms }
    : { ...session, running: ms > 0, deadline: ms > 0 ? now + ms : null, remaining: ms };
}
export function restore(saved) {
  const durations = {
    focus: minutes(saved?.durations?.focus, 25),
    break: minutes(saved?.durations?.break, 5),
  };
  const s = saved?.session;
  const valid = s && ['focus', 'break'].includes(s.phase) && typeof s.running === 'boolean'
    && Number.isFinite(s.remaining) && s.remaining >= 0 && s.remaining <= 120 * 60000
    && (!s.running || (Number.isFinite(s.deadline) && s.deadline > 0));
  return { durations, session: valid ? s : newSession('focus', durations) };
}
