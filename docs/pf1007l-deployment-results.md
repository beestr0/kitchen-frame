# PF1007L test deployment results — 2026-11-13

**The new Pages site and private backend are deployed and pass Mac/browser security
tests. Android HTTPS is still blocked by the hostname's issued certificate chain.
The physical frame has been restored to its working USB Home screen.** No cutover
to permanent Wi-Fi operation was made.

## Created resources

| Resource | Deployed value |
| --- | --- |
| Public dashboard | https://pf1007l-desk-dashboard.pages.dev/ |
| Pages project | `pf1007l-desk-dashboard`, Direct Upload, production branch `main` |
| Pages deployment | `6e15e200-68d3-4b26-a6b6-2a972b5cfcb5` |
| Deployment alias | https://6e15e200.pf1007l-desk-dashboard.pages.dev |
| Private Worker | `pf1007l-desk-dashboard` |
| Active Worker version | `7904b84a-b794-4cb2-8ae2-232759b77653` |
| Worker deployment | `19cc639d-0384-4cb8-a3c3-e347056c807b` |
| KV | `pf1007l-desk-dashboard-calendar`, ID `97c251442031407eb7bac4b330fbe07b` |
| SQLite Durable Object | `pf1007l-desk-dashboard_MessageRoom`, namespace `beb1bc44b89c40c89ce701fba964de93` |
| Pages → Worker | production `DESK_API` service binding; preview API binding absent |
| Worker bindings | `CALENDAR`, `MESSAGES`, `ASSETS`, `DISPLAY_TZ`, new `DASHBOARD_KEY` |
| Public backend endpoints | workers.dev and preview URLs disabled; no custom domain or route |

All resources belong to the previously inspected account ending `de8d`. Existing
`home-hq`, its D1/AlertHub/secret/bindings and cron were not changed. Its Worker
modification timestamp remains `2026-11-12T19:24:16.113922Z`; pre/post binding metadata
matches. No existing personal data was read or modified.

### Cost and deployment fixes

Cloudflare explicitly identified the account as **Free** when rejecting an attempted
custom `cpu_ms: 10` setting (code 100328). Removed that unsupported override; the
platform's Free-plan CPU limit remains enforced. The retry deployed successfully
without a subscription, certificate purchase, domain purchase or upgrade. KV,
SQLite Durable Objects, Pages and the small test workload use available Free resources.
The first rejected upload did not replace the existing HomeHQ Worker.

Wrangler Pages also required two safe local fixes: it does not support `account_id`
in Pages configuration, and a config staged under the Vite project collided with
Vite's deployment redirect. The backend config pins the account; Pages deployment
selects it through `CLOUDFLARE_ACCOUNT_ID`. Its generated config is staged outside
the repository's ancestor tree, while assets remain in ignored `dist-desk-pages/`.
No other resource was changed to solve these local configuration failures.

## Authentication and security

Generated an independent 384-bit random dashboard key. It is installed only as the
new backend's `DASHBOARD_KEY` secret and stored locally in
`backups/pf1007l-desk/dashboard-key` (ignored by Git, mode 0600, parent directory 0700).
The value was supplied through stdin, not command arguments, URLs, chat or committed
files. A scan of tracked/unignored source files found no copy of the key. Preserve
this protected local backup; do not paste or commit it.

The public shell contains no private data. APIs require the new key; when the secret
is missing the production entry fails closed. Correct-key API reads and WebSocket
upgrade/ping/pong passed. No real provider credentials, agent token or new cron is set.
The backend's public workers.dev route and previews are disabled, request observability
is not enabled, and Pages preview has no DESK_API service binding.

The app's existing WebSocket/image authentication can place the device key in query
strings. No personal integrations were configured; review same-origin secure session
cookies before adding private content. Do not put a production key into a kiosk URL.

## Verification completed

| Check | Result |
| --- | --- |
| Local automated suite | **37 passed**, zero failures |
| Production build and Pages packaging | Passed; USB `dist/client/` was preserved |
| Deployed browser regression (Mac Chrome) | Passed touch navigation, calendar, demo task add/complete, failure retry, persistent Focus, Settings and solar-theme tests; no page errors |
| Public HTML | HTTP 200; `Cache-Control: no-store`, no-referrer and nosniff headers |
| Hashed JavaScript asset | HTTP 200; immutable one-year cache; no embedded key |
| Missing/wrong API key | HTTP 401 |
| Correct key: calendar | HTTP 200; empty events from new KV with no configured feed |
| Correct key: photos/messages | HTTP 200 from the new backend |
| Correct key: Todoist | HTTP 503 as expected without TODOIST_TOKEN |
| Correct key: weather | HTTP 200 with unconfigured-weather payload; no location supplied |
| Dashboard key used to post an agent message | HTTP 401 as intended |
| Wrong WebSocket key / unauthenticated recipe POST | HTTP 401 |
| Authenticated WebSocket | Upgrade succeeded, ping → pong through Pages relay and new MessageRoom |
| Existing HomeHQ cloud resources | Pre/post timestamp and bindings unchanged |

The browser regression uses invented data and mocked integration responses; it does
not establish real calendar/Todoist/weather behavior. Actual backend authentication,
KV access and MessageRoom connectivity were checked separately without mocks.

Cloudflare rejects Python's default urllib User-Agent with HTTP 403/code 1010 on
this public site. Normal browser/curl clients work. The verification script used a
normal browser User-Agent afterward; no Cloudflare security setting was weakened.
HTTP 403 from that client was a successful TLS connection, distinct from Android's
certificate handshake failure.

## Physical HTTPS blocker and investigation

Immediately after deployment, the exact production hostname temporarily presented
a **GTS WE1 → cross-signed GTS Root R4 → GlobalSign** chain with a generic `pages.dev`
leaf. Hostname and chain verification using the copied frame roots returned code 0.
That successful initial check justified the authorized physical probe.

The frame then logged:

```text
handshake failed; returned -1, SSL error code 1, net_error -202
FrameKiosk: ssl error 3
```

DevTools confirmed `ERR_CERT_AUTHORITY_INVALID`. The deployed dashboard did not boot,
and no deployed-view/performance test could run on the frame. Its Wi-Fi-only operation
is **not verified**. The planned temporary removal of the USB reverse mapping was
never reached; the fallback stayed available.

Repeat Mac captures after certificate provisioning showed a different, hostname-specific
leaf for `pf1007l-desk-dashboard.pages.dev`, issued by **Let's Encrypt YE1**, valid
2026-11-13 21:47:59 UTC through 2027-02-11 21:47:58 UTC. The chain continues through
ISRG Root YE / X2 / X1, which the frame cannot anchor. Both default-TLS and TLS-1.2
checks now fail against copied frame roots; the deployment-specific alias fails too.
This is consistent with the newly issued project certificate replacing the initial
generic wildcard during provisioning, rather than a dashboard or authentication bug.

A control probe in the **same physical WebView**, without a key or bypass, loaded
`https://pki.goog/` successfully and reported `isSecureContext: true`. Its GTS chain
validates through the frame's existing GlobalSign trust anchor. The frame can use
proper HTTPS; it needs a compatible server certificate chain.

No supported free CA selector for the platform-owned Pages hostname was found.
Cloudflare documents that advanced certificates do not override Pages' certificate
selection. No undocumented certificate mutations, paid service, trust-anchor install,
SSL-error override or Android setting change was attempted.

- [Pages certificate limitations](https://developers.cloudflare.com/pages/platform/known-issues/)
- [Certificate/hostname priority](https://developers.cloudflare.com/ssl/reference/certificate-and-hostname-priority/)
- [Old-client chain compatibility](https://developers.cloudflare.com/ssl/troubleshooting/general-ssl-errors/)

Relevant sanitized evidence is retained under ignored `diagnostics/pf1007l/cloudflare/`:
`deployed-pages-chain.txt` (initial compatible chain), `root-modern-chain.txt` and
`deployed-pages-tls12-chain.txt` (later incompatible chain), `android-tls-details.json`,
`android-gts-control.json`, `https-security-tests.json`, `websocket-test.json`,
`frame-deployed-results.json`, `deployed-resources.json`, and Worker deployment metadata.
Full CLI failures were preserved in local `/private/tmp/pf1007l-*.log` files.

## Final state and rollback

The test kiosk is back at `http://127.0.0.1:5173/?diag`, displaying **Home, light theme,
invented data**. Native screenshot confirmation showed approximately 61 fps. Its saved
URL is the same local URL as before the test; cloud navigation used DevTools rather
than permanently saving a cloud URL. The loopback server returns HTTP 200 and
`tcp:5173 → tcp:5173` USB reverse mapping is active. Temporary debugging was disabled,
the debugging socket was confirmed closed and port-9223 forwarding was removed.
HomeHQ and Rootless Launcher remain available and unchanged.

Nothing needs to be uninstalled or reverted on Android. If needed, launch HomeHQ:

```sh
adb -d shell am start -n com.wesbos.homehq/.MainActivity
```

The new cloud stack remains deployed on Free for inspection from a current browser.
At the public URL, Settings → Demo mode → On shows invented content without entering
any key. No real data is configured. Do not treat a modern-browser success as proof
of frame compatibility.

For future code rollback, use the recorded Pages deployment and Worker version above
as a matched pair; preserve the new KV/DO data and verify the key binding afterward.
Do not roll back to initial Worker version `d0344b36-1ea0-4af6-9e8f-6b6777eb26b7`
unless intentionally testing missing-secret rejection: it predates secret provisioning.
No cloud rollback/deletion is currently necessary. If removing the test stack later,
obtain deletion approval and remove only the new Pages/Worker/DO/KV resources after
checking dependencies; leave HomeHQ's D1 and AlertHub untouched.

## Remaining work and next integrations

First resolve certificate hosting. The smallest no-purchase next step is to ask
Cloudflare whether this new project's Pages certificate can be reissued using a
GTS chain compatible with old Android. A support request was not sent because no
external messaging was authorized. Resolution and support availability are not
guaranteed. If that cannot be done without an upgrade, revisit an owner-controlled
custom hostname on a **Worker custom domain** with a compatible chain; this requires
separate domain/DNS/certificate approval. No eligible domain currently exists in the
inspected account, and no purchase is authorized. Do not buy ACM expecting it to fix
a `pages.dev` hostname.

After a compatible endpoint passes the frame test, repeat all four views, themes,
reload/error recovery and performance, then temporarily remove USB forwarding and
reload to prove Wi-Fi independence. Keep the known local fallback until accepted.
The current restriction against permanent kiosk URL changes remains in force.

Only after that acceptance, configure the new backend, never the old HomeHQ Worker:

1. **Weather:** choose location/unit and set WEATHER_LAT, WEATHER_LON, WEATHER_UNIT
   through secure local/cloud settings. No provider API key is needed. Confirm local
   timezone and sunrise/sunset behavior before relying on automatic themes.
2. **Calendar:** obtain the desired read-only iCloud shared-calendar feed URLs and
   store CALENDAR_URLS as a new Worker secret through secure input, not chat. These
   URLs are sensitive. Force an authenticated calendar refresh and verify timezone,
   recurrence and stale-data retention. If adding cron refresh, first add a scheduled
   handler delegation to `worker/desk.js`; this first deployment intentionally has none.
3. **Todoist:** securely provision a dedicated TODOIST_TOKEN and explicitly select
   TODOIST_TODO_PROJECT before disabling demo mode. Review add/complete write behavior
   and use a test task/project first. No live task mutation is authorized yet.

Spotify Now Playing and read-only Bambu status remain unimplemented. The existing
separate view/server-module structure is preserved, with no new browser dependency.
