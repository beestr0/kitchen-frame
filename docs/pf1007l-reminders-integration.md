# PF1007L native Reminders demonstration — verified November 14, 2026

This supersedes earlier inactive/pending discovery notes. The owner successfully
added the private CalDAV account to native iPhone Reminders. Work is restricted to
`/pf1007l-demo/pf1007l-test/`; iCloud lists/defaults remain unchanged.

## Verified workflow and evidence

| Check | Result |
| --- | --- |
| Phone item on Radicale | `Test dashboard sync`, date-only 2026-11-14, incomplete; UID `pf1007l-demo-undated` |
| Actual phone edit | Title became `Teat dashboard sync - edited on iPhone`, same UID/date/status; no duplicate |
| Physical dashboard | That item appeared in Home/Tasks and the November 14 Week/Month day |
| Frame completion → Radicale | Same UID became COMPLETED, percent 100, completion timestamp; due date preserved |
| Return to iPhone | Owner confirmed completed after a later app refresh; initially delayed, not instant push |
| Undated task | `Undated dashboard pilot` appeared in Tasks and not Calendar |
| Phone completion → frame | Owner completed that item; it disappeared automatically on the frame without page reload |
| Siri creation | Owner explicitly targeted PF1007L Test; `Siri dashboard pilot` had a new UID, no due date, and appeared automatically in frame Tasks; exact UID retained only in ignored local evidence |
| Offline UI | Simulated task-only 503 retained rows, exposed error, disabled completion; recovery restored writes |
| Concurrent edit | Real disposable probe: stale completion returned 409, preserved latest content; no blind overwrite |
| Restart | Only bridge restarted; same IDs/state recovered and frame session remained valid |
| Security | Missing backend key/cookie, wrong frame address, missing CSRF and foreign Origin denied |
| Frame performance | Home/Tasks/Calendar, five-second samples in each theme: 59.95–60.15 FPS, no gaps >50 ms |

The initial five-second completion assertion was too short; subsequent server reads
and physical views verified completion and disappearance. A UI poll race was also
removed: completion waits for an older in-flight poll before issuing a fresh read.
No claim of an exact completion latency SLA is made. The phone's return path was
observably delayed; background fetch and cellular behavior still need acceptance.

Local checks: **50 dashboard tests**, **48 proxy/TLS tests**, **5 Python bridge
fixtures**, **2 redirect-origin tests** passed; isolated demo build passed. Fixture
tests cover date-only/floating/UTC/DST rejection, stable identity, preserved due and
unknown properties, idempotent completion, stale writes, recurring-write rejection,
partial-result last-good retention and authoritative empty results.

Ignored physical evidence is under `diagnostics/pf1007l/reminders/`; it contains
only demonstration data. No Apple credentials, raw personal calendars or iCloud
Reminders were accessed. Prior preparation changes remain uncommitted on the same
feature branch; no PR, merge or cloud deployment occurred.

## Current URLs, services and isolation

- Frame's saved **demo** URL: `https://beestr0.duckdns.org:8789/__reminders-demo/`.
- Original dashboard remains `https://beestr0.duckdns.org:8789/`, with live weather.
- iPhone CalDAV remains `https://hub-inspiron-5570.tailb76e1b.ts.net:443/`, private
  Tailscale Serve → existing Radicale loopback 5238. No Funnel or router ports.
- New adapter: `pf1007l-reminders-bridge.service`, loopback 5240, DynamicUser,
  private state and systemd credentials, restricted to the one disposable collection.
- Runtime: `/opt/pf1007l-reminders-bridge`; private config:
  `/etc/pf1007l-reminders-bridge`; SQLite state: `/var/lib/pf1007l-reminders-bridge`.
  Apple/DAV password is loaded only into this collector, not the HTTPS proxy.
- `scripts/reminders-demo-proxy.mjs` adds only the exact HTTPS demo prefix. The
  proxy receives a separate bridge key by a service drop-in, never the DAV password.
  Ordinary root/HTTP/cloud routes cannot relay the task adapter.
- The frontend is a separate local Vite build (`vite.config.reminders.js`). No
  personal task data/assets were sent to Pages/Workers/KV. Calendar events remain
  synthetic; the actual private iCloud Calendar plan is unchanged and read-only.
- Tasks poll every 30 seconds while Home/Tasks/Calendar is visible, and refresh on
  Tasks opening. Server requests are serialized and cached for 15 seconds. No ICS
  parsing or recurrence expansion occurs on the PF1007L.

Adapter cgroup memory was about **17–18 MB**, Radicale about **22–24 MB**, with
roughly 2.9 GB available server RAM. These are small-pilot samples, not long-term
load or battery measurements. Existing HTTPS/weather, Jellyfin, Tailscale and
HomeHQ are preserved; no launcher/default-list changes were made.

## DHCP and deployment recovery

ADB showed the frame now uses **10.157.1.76**, rather than the previous .247. Only
the dedicated `pf1007l_proxy_tls` nftables table and HTTPS client allowlist were
updated to that physically verified address. Table replacement was atomic; no
Tailscale/unrelated firewall tables or router settings changed. The HTTP fallback's
older allowlist was not broadened. Future DHCP changes still fail closed.

A caught deployment error made the non-secret HTTPS config mode 0600, blocking
DynamicUser startup. Its original 0644 mode was restored and health reverified;
credentials stayed private throughout. The deployment and rollback scripts now
preserve correct public-config permissions. All affected recovery was confined to
the HTTPS proxy; Jellyfin/Tailscale/Radicale were not restarted by that correction.

## Write, identity and privacy contract

IDs are HMACs of collection + VTODO UID, with separate opaque ETag revisions. Only
GET snapshot and POST completion exist; there is no dashboard create/delete/edit
or arbitrary DAV URL API. Completion does a fresh GET, verifies UID/revision and
issues PUT with If-Match. Persisted operation keys prevent replay; ambiguous errors
surface instead of assuming success. Completed records remain in Radicale.

The frame uses a revocable HttpOnly/Secure/SameSite=Strict cookie and per-request
CSRF token; it never receives the DAV password or dashboard cloud key. The initial
session was explicitly provisioned once to the current allowlisted physical frame.
This IP-based bootstrap is suitable only for the disposable pilot, not strong
hardware identity. Native navigation/bridge controls and stronger provisioning
must be reviewed before personal data. The cookie currently has a 24-hour client
lifetime; after it expires, local reprovisioning may be needed. No automatic
credential reset is authorized.

Task payloads stay in frame memory (no task localStorage) and root-protected Linux
last-good state, with no-store responses. Offline completions are disabled, not
queued silently. A cold offline restart may show no tasks until contact resumes;
weather retains its existing independent cache. Corrupt/partial reads retain stale
last-good rows; successful empty results remove old active rows. No upstream DELETE
is issued by the bridge. Recurring tasks are displayed conservatively and must be
completed on the iPhone until occurrence semantics are validated.

## Remaining physical acceptance before everyday use

1. Review the demo account's iPhone Fetch schedule without changing other accounts.
   Measure phone return delay with the app closed/locked. Apple's Automatic fetch
   may depend on charging/Wi-Fi; do not promise instant push for this server.
   [Apple Calendar account/fetch guidance](https://support.apple.com/en-tm/guide/iphone/iphc37be2016/27/ios/27)
2. With Mac off, test Wi-Fi and cellular through Tailscale, disconnect/reconnect,
   offline edits and later reconciliation. No such cellular test is yet claimed.
3. Test timed native reminders, timezone changes/DST and multiple selected lists.
   The current pilot deliberately selects only PF1007L Test. Full recurrence
   advancement, detached instances, subtasks, Apple-only features and persistent
   client session renewal are not everyday-ready.
4. Exercise timeout-after-success/retry across outages and long-duration soak. The
   backend has durable idempotency and revision checks, but broad long-term
   reliability is not established by this small demo.
5. Review retention/backups/restore, device/session security and native WebView
   boundaries before any private/personal collection is approved.

Separate Siri test already passed with: **“Add Siri dashboard pilot to my PF1007L
Test list.”** Verify the actual list destination; keep the default list unchanged.
The new Siri reminder was left incomplete for further demonstration.

## Reversible rollback — prepared, not executed

`deploy/reminders/rollback_bridge.py`, run privately as root after choosing rollback,
stops only the new bridge and restores the saved original proxy implementation and
weather configuration. It retains the current verified frame allowlist, Radicale
data, credentials and private Serve. It does not stop Jellyfin/Tailscale or delete
any task. Baselines are under `/opt/pf1007l-reminders-bridge/baseline-proxy.mjs` and
root-private `/etc/pf1007l-reminders-bridge/baseline-config.json`.

Then restore only the kiosk URL from the Mac:

```sh
adb -d shell am start -n com.huntsyea.frame/.MainActivity -d https://beestr0.duckdns.org:8789/ --ez debug false
```

Do not clear app data, uninstall HomeHQ, reset Serve, delete task storage or revoke
the CalDAV password as an automatic rollback shortcut.
