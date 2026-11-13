# Personal desk dashboard — PF1007L

The desk interface uses the original Kitchen Frame palette, type, panels and automatic day/night theme. Its main sections are **Home, Calendar, Tasks and Focus**, with Settings in the top-right corner. Recipes, Groceries and Music implementations/API routes are retained for future use but omitted from the main navigation. Future integrations can add a view in `dashboard/src/views/` and a server-side module in `dashboard/worker/`; only the active view is mounted.

## Development and validation

From `dashboard/` with Node 22.12+ or Node 24:

```sh
npm ci
npm test
npm run build
npm run dev
```

In the managed cloud environment, first export `XDG_CONFIG_HOME=/workspace/.cloud-config` and `WRANGLER_SEND_METRICS=false`. No production credentials are needed. Open Settings → Demo mode for invented calendar/tasks. Demo task changes do not reach Todoist.

`npm test` includes the existing Worker/parser tests plus solar-boundary, invalid-cache, focus pause/resume/reload and iCloud HTTPS/failure-retention tests. Build targets remain `chrome106` for JS and `chrome61` for CSS. No new runtime dependencies, filters, shadows or incompatible color functions are used. Controls have a minimum 48 CSS-pixel height; Settings uses a native modal dialog with focus containment, Escape support and internal scrolling.

The optional browser suite requires Playwright and an installed Chromium. It drives touch interactions at 1280×800, checks Tasks add/complete and failed completion retry, calendar week/month navigation, Focus persistence, saved settings and exact solar transitions. It uses invented data and mocked integration responses. With the cloud dev server running:

```sh
PLAYWRIGHT_MODULE=/workspace/.browser-tools/node_modules/playwright/index.mjs \
  node scripts/desk-smoke.mjs
```

Elsewhere, provide `PLAYWRIGHT_MODULE` as an absolute Playwright module path and `CHROMIUM_PATH` for your browser binary. `DASHBOARD_URL` overrides the local test origin. `SCREENSHOT_DIR` optionally captures light/dark Home, Focus and Settings images; create the directory first. This is a desktop Chromium check, not proof of Android WebView 106 or A33 performance. Use `?diag` on the physical device to measure viewport, heap, DOM count and frame timing. A short cloud Chromium 156 Home comparison against the original HEAD (same 1280×800 demo data, no weather) showed 127 DOM nodes, approximately 7 MB JS heap, and 61 reported fps with zero >50 ms frames for both versions. This is a desktop baseline only; it does not measure the A33/Mali-400.

## Behavior

- **Appearance:** Automatic follows today's sunrise/sunset from Open-Meteo; until valid weather is available it retains the original local 7 AM–7 PM fallback. Light and Dark override solar times. Preferences and `?theme=auto|light|dark` persist across reloads. Match the frame's timezone to its weather location. Original theme colors are unchanged.
- **Refresh:** Calendar and Tasks share a configurable 1, 5 or 15 minute interval (default 5); weather remains every 15 minutes. A changed interval takes effect when the pending poll schedules its next run. Refresh now fetches data immediately, preserving saved content if unavailable. Calendar polling reads the Worker's cache; the existing ten-minute cron handles upstream refresh. Reload retains its original forced calendar refresh behavior.
- **Focus:** Focus/break lengths are 1–120 minutes, default 25/5. Start, pause, reset and next-session controls use persisted deadlines so background throttling and tab changes do not lose time. Completion waits for the user to start the next session; no automatic cycle or sound. The automatic clock screen is held off during an active countdown. Per-second rendering runs only while Focus is mounted and running; other views keep the minute clock.

## Integrations and secrets

No credentials were added. The browser calls same-origin `/api/*`; the Cloudflare Worker holds credentials and talks to providers. Configure real integrations only through a local ignored `dashboard/.dev.vars` or Cloudflare's server-side secret settings, never browser code, committed files or chat.

- **iCloud:** `CALENDAR_URLS` contains one or more public iCloud calendar `webcal://` links separated by spaces. These links are sensitive. The Worker converts them to HTTPS, expands repeats with `ical.js`, merges calendars, and retains each feed's last good events on failure in `CALENDAR` KV. Public feed links are read-only; event editing/CalDAV login is not implemented. `DISPLAY_TZ` supplies a timezone for floating times. Existing tests cover iCloud folding, recurrence exceptions, all-day events and DST.
- **Todoist:** `TODOIST_TOKEN` is a Worker secret. `TODOIST_TODO_PROJECT` selects the task project by name (the existing configuration uses `Household`; choose your own before deployment). The Worker paginates API v1 projects/tasks, returns section/assignee metadata, and adds or closes tasks server-side. Existing parent-task filtering is retained. Completion is optimistic with rollback and an error if the provider rejects it; retry remains possible.
- **Weather:** configure `WEATHER_LAT`, `WEATHER_LON`, optional `WEATHER_UNIT` (`fahrenheit` default or `celsius`). Open-Meteo needs no API key. Weather location determines the solar schedule.
- **Access:** set a strong server-side `DASHBOARD_KEY` before exposing the app. The original frame key mechanism is retained. Never include a production key in screenshots, logs, shell history or documentation. Before deployment, review the Cloudflare account, the existing `wrangler.jsonc` KV namespace ID, Durable Object migration and image binding for your own account. No Cloudflare deployment or account mutation was performed.

## Local Mac / Codex CLI handoff

USB is attached to the Mac, not the cloud. No physical-device testing has been performed. Start Codex CLI in this repository on the M1 Mac and ask it to read this document and `AGENTS.md`.

1. If ADB is missing, install via `brew install --cask android-platform-tools`. Run `adb devices` locally; approve the USB-debugging prompt on the frame. With multiple devices, select the intended serial using `ANDROID_SERIAL` locally (do not paste identifiers in a public issue).
2. Run `bash scripts/pf1007l-check.sh`. This is a read-only check of model/board, Android/API/CPU, display size/density, clock, and WebView package/provider versions. It does not install anything, change settings, capture personal data, root, erase or flash the frame. The script was syntax-checked in cloud; it has not run against the actual device.
3. Confirm Android 6.0.1/API 23, WebView 106, landscape viewport and touch accuracy on the actual hardware. Check the full existing `docs/frame.md` before planning kiosk work; it records a different frame and its device-specific modifications, not instructions to apply blindly to the PF1007L.
4. After the owner authorizes installation/configuration, Codex CLI can set up JDK 17 and Android command-line tools, build the existing API-23-compatible kiosk with `kiosk/build.sh`, verify its signature, and propose the precise `adb install -r` command and dashboard URL configuration. Confirm any existing kiosk signature/app data before an upgrade. Do not uninstall to bypass a signature mismatch.
5. Before any firmware, root, launcher, WebView-provider, package-disable, display-density, timezone or factory-reset change, explain the command, backup/undo path and ask for approval. No such change is authorized by this handoff.
6. Once a local test app is approved and running, verify all four views, manual and solar themes, focus pause/resume across sleep, keyboard/task interactions, reconnection and `?diag` performance. Cloud rendering cannot establish battery behavior, GPU smoothness, native keyboard resizing or installed WebView compatibility.
