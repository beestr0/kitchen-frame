// Open-Meteo returns local wall times for the configured weather location.
// The frame's time zone should match that location. Never trust stale/invalid solar data.
export function resolveTheme(preference, now, weather) {
  if (preference === 'light' || preference === 'dark') return preference;
  const date = [now.getFullYear(), String(now.getMonth() + 1).padStart(2, '0'), String(now.getDate()).padStart(2, '0')].join('-');
  const today = weather?.days?.find((d) => d.date === date);
  let rise = new Date(today?.sunrise).getTime();
  let set = new Date(today?.sunset).getTime();
  if (!Number.isFinite(rise) || !Number.isFinite(set) || rise >= set) {
    rise = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 7).getTime();
    set = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 19).getTime();
  }
  return now.getTime() >= rise && now.getTime() < set ? 'light' : 'dark';
}
