# PF1007L live Indianapolis weather

Deployed and physically verified November 14, 2026 UTC.

## Configuration and data path

- Location: Indianapolis city center, latitude `39.7684`, longitude `-86.1581`.
- Units: Fahrenheit (existing default).
- Timezone: `America/Indiana/Indianapolis` (EST/EDT with daylight-saving time).
- Provider: Open-Meteo non-commercial free API, no account, key or paid subscription.
- Dashboard: `https://beestr0.duckdns.org:8789/` (saved URL unchanged).
- Linux HTTPS: explicit `liveWeather=true`, `demoOnly=true`. Only exact GET
  `/api/weather` without query parameters can reach the authenticated cloud backend.
- HTTP fallback on 8788 remains unchanged and demo-only, including weather.
- Calendar, Todoist, Spotify, Bambu, photos and other integrations remain unconfigured
  and blocked/synthetic at the Linux proxy. Browser calendar/tasks stay in demo mode.

The existing private `pf1007l-desk-dashboard` Worker fetches and reduces the provider
response to current temperature, apparent temperature, WMO condition code, day/night,
five daily forecasts, precipitation probability and sunrise/sunset. Existing icons
map those codes locally; no weather SDK, image downloads or new browser dependency
was added. Home uses day zero for high/low and days one through four for the forecast.
Layout and existing clock stay intact. Provider attribution is below the forecast.

Open-Meteo's published free service is for non-commercial use, limited to 10,000
calls/day, without an uptime guarantee. No paid fallback or billing product was
activated. See [provider pricing](https://open-meteo.com/en/pricing) and
[forecast documentation](https://open-meteo.com/en/docs).

## Refresh, caching and outages

`worker/weather-cache.js` stores a namespaced weather record in this project's
existing KV binding, separate from the calendar key. It includes last-good data,
last attempt time and failure status. No expiration deletes the last-good forecast.

- Browser refresh remains every 15 minutes; unchanged data skips storage/render work.
- A weather-only Worker cron runs every 15 minutes even if the frame is idle/off.
  It does not invoke the original calendar scheduled handler.
- Requests and cron share the 15-minute backend freshness/backoff window, with
  same-isolate concurrent request deduplication. KV's eventual consistency means
  separate isolates can occasionally duplicate a refresh; this is not a global lock.
- Provider calls have an eight-second timeout and a 15-minute Cloudflare fetch cache.
- Malformed/partial provider results never overwrite the last valid forecast.
- Failures retain last-good data and mark the API result stale; retries back off for
  15 minutes. A cold outage without cached data returns an honest unavailable error.
- The browser retains its own last-good weather across reloads. It labels the
  forecast **Outdated** with the original update time on fetch failure, backend
  stale status, or age exceeding 30 minutes. Successful refresh clears the warning.
- API responses are no-store; the durable cache is backend-controlled. Browser
  polling does not fetch Open-Meteo directly or receive backend/provider secrets.

Nominally about 96 provider refresh opportunities/day plus limited startup/race
requests, far below the published free allowance. Weather KV writes are similarly
small; existing account aggregate Cloudflare billing/allowances remain subject to
the separate cost assessment. No new namespace, Durable Object or paid service
was created. The existing private Worker, Pages service binding and dashboard key
were preserved.

## Validation

- Full dashboard suite: **43 tests passed**, including concurrent cache reuse,
  outage retention/backoff, cold outage, configuration-separated cache keys,
  malformed-provider rejection, authentication/method restrictions and weather-only cron.
- Proxy/TLS suite: **48 tests passed**, including that HTTP cannot opt into live
  weather even if a weather flag is accidentally present.
- Production build and deploy succeeded for only the PF1007L Worker/Pages project.
- Worker version: `54bd0f3e-3173-4ce1-bace-3dd18ddf1a57`.
- Pages deployment alias: `e29ce9eb.pf1007l-desk-dashboard.pages.dev`.
- Physical WebView: three secure HTTPS 200 document loads, normal ZeroSSL validation.
- Live weather received; exactly four future days and five weather SVG icons rendered.
  Repeated weather API reads returned the same cached update timestamp.
- Weather API outage was simulated only in the test WebView: cached forecast survived
  a full reload, showed Outdated, then recovered with no warning. Cloud cache and
  provider data were not poisoned. Backend provider-outage retention was separately
  tested in isolated automated tests, not by disrupting the real provider.
- Light: **59.25 FPS**, two >50 ms frames in ten seconds (maximum 66.5 ms).
  Dark: **60.15 FPS**, zero >50 ms frames. No significant regression from the baseline.
- Frame PSS after navigation: 74,775 KiB (about 73 MiB).
- Home weather fits the 1280×800 viewport; no horizontal overflow. Navigation through
  Calendar, Tasks and Focus remained responsive. Automatic theme selected Dark at
  local nighttime using the live solar schedule.
- Android's configured timezone is already correct. WebView 106 reports the older
  equivalent alias `America/Indianapolis`; winter and summer local formatting matched
  the canonical zone. A first assertion expected the canonical spelling and was
  corrected; that failure output was retained. No Android timezone setting changed.
- Existing date/time display agreed with local Indianapolis time. The weather API does
  not replace the device clock or change its synchronization settings.
- Unauthenticated cloud weather returned 401; no access key is stored in the frontend.
- No USB reverse mapping is present. App debugging and temporary forward were removed.
  The optional on-screen diagnostics overlay was disabled for a clean final display.
- Linux activation confirmed original HTTP source/configuration and HTTP/Jellyfin/
  Tailscale service PIDs/state unchanged. Certificate renewal/monitor timers remain enabled.

Evidence and screenshots are in ignored `diagnostics/pf1007l/weather/`. No iCloud or
Todoist credentials were entered, and no personal calendar/task data was requested.

## Linux change and rollback

The scoped native-sudo helper `deploy/lan-proxy/tls/enable_weather.py` checked the
installed source hash, verified the new JavaScript syntax, backed up only the
isolated HTTPS source/configuration, restarted only that HTTPS service and verified
normal TLS health. It automatically restores those files if activation fails.
The helper exited successfully; it is not a background root service.

Protected backup:
`/etc/pf1007l-tls/weather-backup-1794629852683961003/`

To withdraw live weather, an administrator can restore `proxy.mjs` to
`/opt/pf1007l-tls/proxy.mjs` and `config.json` to
`/etc/pf1007l-proxy-https/config.json` from that backup, preserving root ownership
and mode 0644, then restart **only** `pf1007l-proxy-https.service`. Do not restore
TLS certificates or change the guard, original HTTP service, Jellyfin or Tailscale.
Alternatively remove only `liveWeather` from the HTTPS config and restart that
service. Keep `demoOnly=true` in both proxy configurations.

Cloud rollback: disable WEATHER_ENABLED and remove only this project's weather cron,
then deploy the reviewed desk configuration; revert only the weather UI/code if
needed. No key rotation or KV deletion is required. The independent HTTP fallback
remains available at `http://10.157.1.115:8788/` with the rollback procedure in the
[permanent HTTPS report](pf1007l-permanent-https.md). Future full proxy reinstall
procedures must deliberately preserve the reviewed weather source/config flag;
certificate renewal itself does not reinstall or overwrite them.

## Next: iCloud Calendar, pending approval

Choose the calendar(s), verify the Indianapolis timezone, and decide whether Apple's
public read-only link model is acceptable. Anyone who obtains a feed URL can read
that calendar, so supply links only through a hidden secure Terminal prompt, never
chat or source files. A dedicated display calendar can limit exposure. If public
links are unacceptable, an authenticated CalDAV connector is a separate implementation.

Before storing any feed: review strong kiosk authorization and navigation/bridge
restrictions, add a narrowly scoped HTTPS-only calendar route while retaining the
HTTP demo barrier, and approve Worker secrets plus calendar-only cache/cron changes.
Then test one feed for all-day/recurring/DST events, failure retention and privacy.
Keep Todoist/Spotify/Bambu disabled. See the
[personal integration plan](pf1007l-personal-integrations-plan.md).
