import { getWeather } from './weather.js';

export const WEATHER_REFRESH_MS = 15 * 60 * 1000;
const flights = new WeakMap();
const cacheKey = env => 'weather:v1:' + [env.WEATHER_LAT, env.WEATHER_LON, env.WEATHER_UNIT || 'fahrenheit', env.WEATHER_TZ || 'auto'].join(':');
const output = (entry, now) => ({ ...entry.data, stale: entry.failed === true || now - Date.parse(entry.data.updated) > 30 * 60 * 1000 });

// Dedicated desk KV key; never replaces calendar data. Keep the last good copy
// without a TTL so a provider outage does not erase the only useful forecast.
export async function cachedWeather(env, now = Date.now()) {
  const kv = env.CALENDAR;
  if (!kv) throw new Error('Weather storage unavailable');
  let active = flights.get(kv);
  if (!active) { active = new Map(); flights.set(kv, active); }
  const key = cacheKey(env);
  if (active.has(key)) return active.get(key);
  const pending = (async () => {
    const previous = await kv.get(key, 'json');
    if (previous && Number.isFinite(previous.checkedAt) && now >= previous.checkedAt && now - previous.checkedAt < WEATHER_REFRESH_MS) {
      if (previous.data) return output(previous, now);
      throw new Error('Weather temporarily unavailable');
    }
    let entry;
    try {
      const data = await getWeather(env);
      if (data.error) throw new Error('Weather not configured');
      entry = { data, checkedAt: now, failed: false };
    } catch {
      entry = { data: previous?.data || null, checkedAt: now, failed: true };
    }
    await kv.put(key, JSON.stringify(entry));
    if (!entry.data) throw new Error('Weather temporarily unavailable');
    return output(entry, now);
  })();
  active.set(key, pending);
  try { return await pending; } finally { active.delete(key); }
}
