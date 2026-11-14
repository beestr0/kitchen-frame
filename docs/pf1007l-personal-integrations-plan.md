# PF1007L personal integration plan

Prepared November 14, 2026 UTC. The permanent kiosk URL is HTTPS; the Linux HTTP
fallback must remain demo-only. Weather was subsequently authorized, deployed and physically verified; see
[weather results](pf1007l-weather.md). All other integrations remain disabled and
no personal provider credentials have been installed. Changes below require owner review and approval.

## Recommended sequence and required input

| Stage | Owner supplies securely or chooses | Proposed behavior |
| --- | --- | --- |
| Weather | City or approximate latitude/longitude, Fahrenheit/Celsius, timezone | First live integration; 15-minute refresh and sunrise/sunset theme schedule |
| iCloud Calendar | Approve Linux-local private CalDAV; choose credential account, selected calendars and colors | Read-only selected-calendar sync, ten-minute local refresh, last-good cache; no public links or Apple data in Cloudflare |
| Todoist | Dedicated project name; API token via hidden prompt; whether writes should ever be allowed | Start read-only; add/complete tasks only after separate approval |
| Spotify | Existing Premium eligibility, developer app, authorized account and browser consent | Artwork/title/artist/status/progress only; no streaming or playback controls |
| Bambu A1 Mini | Firmware version, current network mode, printer LAN address, serial and LAN access code securely | Read-only telemetry, no camera, file transfer or print control |

Timezone currently configured for this project is `America/Indiana/Indianapolis`;
confirm it before enabling real calendar or solar behavior. No secrets should be
pasted into chat. Provider setup uses browser authorization or hidden native
Terminal prompts; credentials remain in project-specific Worker secrets or
root-private Linux files. Do not reuse HomeHQ credentials or modify its resources.

## Privacy gate before any personal data

The current HTTPS proxy also has `demoOnly=true`, as does the original HTTP proxy.
The browser remains in demo mode. Do not simply turn demo mode off everywhere.
Prepare an HTTPS-only route/method allowlist for approved providers and keep HTTP
permanently synthetic, including API and WebSocket paths. Verify it cannot relay
private data even when Worker secrets are populated. Keep unrelated routes blocked.

Keep the existing server-side dashboard authentication and validated outbound TLS.
The frame must not receive upstream provider tokens or the dashboard backend key.
Before personal use, review LAN client authorization: current source-IP/Host/Origin
restrictions are useful but IP allowlisting alone is not strong device identity.
Consider a separately provisioned, revocable kiosk session held in protected app
storage/secure cookie, issued through a local provisioning step, rather than
exposing the global cloud key or placing credentials in URLs. Review the native
JavaScript bridge, mixed-content policy and navigation allowlist before handling
private content. Changes must preserve the tested HTTPS routing and HomeHQ.

Return only minimum display fields. Do not put private responses in public Pages
assets, public CDN caches, request logs or screenshots. Use no-store responses,
bounded server caches with explicit stale timestamps, redacted logs, token
revocation instructions and defined retention. Private calendar events retained
in KV must be cleared when disconnecting the integration if requested.

## Private iCloud direction — awaiting method approval

The owner prefers authenticated access without public sharing. The recommended
replacement is a Linux-local read-only CalDAV collector with a dedicated Apple
app-specific password, ideally a separate privately invited view-only reader
account where practical. Apple credentials and private event snapshots stay on
Linux, not in Cloudflare. Prepared code is inactive and fixture-tested only. See
[the authentication comparison, secure entry and activation proposal](pf1007l-private-icloud-plan.md).
No account was accessed and no personal sync was activated.

## Legacy iCloud public-feed implementation — not selected

The Worker already accepts `CALENDAR_URLS` as sensitive iCalendar feed links,
normalizes to HTTPS, expands recurrence, merges calendars and preserves last-good
feed data in the separate `CALENDAR` KV binding. `DISPLAY_TZ` handles floating
times. The desk deployment currently has no calendar cron; enabling a ten-minute
schedule is a proposed change only to this project's Worker configuration.

Apple's supported public-calendar link is readable by anyone possessing it; it is
not equivalent to authenticated private calendar sharing. Treat links as secrets
and confirm this privacy tradeoff first. Prefer a dedicated display calendar if
needed. No Apple account password is required by the existing feed implementation.
If public-link sharing is unacceptable, stop this route and design an authenticated
CalDAV connector separately; the current code does not implement it.
[Apple sharing documentation](https://support.apple.com/en-gb/guide/icloud/mm6b1a9479/icloud)

Acceptance: one selected calendar first; timezone, all-day events, DST and recurring
exceptions; upstream failure retains prior data and shows age; HTTP still synthetic.

## Existing Todoist implementation

The Worker uses API v1 with `TODOIST_TOKEN` and `TODOIST_TODO_PROJECT`; the latter
selects a project by name. Confirm the exact project rather than assuming the
legacy Household/To-do defaults. Existing code can list, add and close tasks, so
initial read-only deployment needs server-side method restrictions and matching UI
behavior. A personal API token is an account credential, not a project-scoped
read-only capability; enforce the selected project in the backend and never send
the token to WebView. Separate approval is needed for real task creation/completion.
[Todoist API](https://developer.todoist.com/api/v1/)

Acceptance: pagination, sections/assignees, due dates, failures and 429 backoff;
verify mutations are blocked until approved. Start with a dedicated test project.

## Existing weather implementation

Use `WEATHER_LAT`, `WEATHER_LON`, `WEATHER_UNIT` and the existing Open-Meteo fetcher.
Approximate city-level coordinates are generally sufficient. No API key is needed
for the non-commercial free API. Its published free limit is 10,000 calls/day and
there is no uptime guarantee. Cache/deduplicate fetches and retain the existing
15-minute frame refresh; do not fetch separately on every clock tick.
[Open-Meteo pricing](https://open-meteo.com/en/pricing)

Acceptance: units, location, current conditions, sunrise/sunset, stale-data behavior
and automatic theme fallback. Weather can be rolled back independently.

## Spotify Now Playing — later module

Add an isolated backend module and lazy-mounted view; do not add the Web Playback
SDK or audio streaming. Use browser OAuth authorization-code flow, state validation
and server-side refresh-token storage. Register an exact supported redirect URI
before authorization; a temporary modern-Mac authorizer can be used for setup,
while runtime must not depend on the Mac. Final callback design needs review.
Request only `user-read-currently-playing` / `user-read-playback-state` as required;
no playback modification scope. Serve minimal metadata through the authenticated
HTTPS dashboard. Show inactive/private/paused sessions gracefully. Poll roughly
15–30 seconds only when useful, interpolate progress locally, back off on 429,
cache small artwork and validate allowed artwork origins if proxying it.

Spotify currently requires the development app owner to have Premium. Verify
existing eligibility before implementation; do not purchase a subscription or
promise this integration is free for a non-Premium account. If ineligible, leave
it disabled. Recheck current access rules at implementation time.
[Spotify development restrictions](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide),
[scopes](https://developer.spotify.com/documentation/web-api/concepts/scopes),
[redirect rules](https://developer.spotify.com/documentation/web-api/concepts/redirect_uri)

## Bambu Lab A1 Mini — later Linux-local module

Prefer a separate low-resource Linux collector rather than exposing the printer
to Cloudflare or installing printer protocols on Android. Inspect firmware and
supported authentication/telemetry behavior first. Bambu's third-party access
varies with firmware, LAN-only and Developer Mode; do not assume all requested
fields or read-only access work with the current configuration. Do not change
printer modes/firmware without approval or disrupt Bambu Studio/Handy.
[Official Bambu third-party integration explanation](https://blog.bambulab.com/updates-and-third-party-integration-with-bambu-connect/)

If supported, subscribe only to required status topics with server-side LAN
credentials and verified TLS, using the documented manufacturer trust chain or
an independently verified device identity. Never use rejectUnauthorized=false.
Do not publish printer commands, request camera streams or expose MQTT publicly.
Map progress, ETA, nozzle/bed temperatures, status and available AMS Lite fields
into bounded JSON snapshots served over the existing HTTPS origin. Mark missing
AMS fields unknown rather than inventing values. Use reconnect backoff and stale
indicators; test concurrent Studio/Handy behavior. If secure supported telemetry
cannot be established, leave this integration disabled and report the blocker.

## Deployment and rollback gates

Implement provider flags, cache limits and tests locally before cloud/service
changes. Review exact diffs and obtain approval; modify only the separate desk
Worker/KV/configuration, never home-hq or unrelated resources. Enable one provider
at a time with secure credential entry and a physical acceptance check. Keep the
frame's demo state until each selected live provider is ready. Preserve 58–60 FPS
with only the active view mounted, bounded DOM/artwork and no background animation.

Disable a provider flag, revoke its credential and restore demo mode for rollback;
retain the permanent HTTPS URL and HTTP demo fallback. No router forwarding or
new subscription is needed for the first three integrations under published free
allowances, but Cloudflare account billing/aggregate usage remains separately
unverified as documented in the HTTPS cost assessment. Future API terms and
provider availability can change; do not silently migrate to a paid service.
