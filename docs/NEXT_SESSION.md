# PF1007L — next session

Checkpoint: November 14, 2026, autonomous authentication/reliability development.
Branch: `feat/pf1007l-https-weather-handoff`. Source checkpoint subject:
`Prepare renewable device authentication and resilient demo synchronization`.
Identify its exact commit with `git log -1 --oneline -- docs/NEXT_SESSION.md`.
**Running deployment remains `3a74a35`; this candidate is not activated.** No PR/merge.

## Autonomous session result — read this before deployment

- Prepared opt-in P-256 device proof, owner-managed revocable public-key registry,
  15-minute server-enforced sessions, proactive native renewal, per-session CSRF,
  hash-only session storage, rate limits and no IP/legacy fallback in device mode.
- Added origin-aware native WebView channel, fixed-audience TLS transport,
  restricted navigation/resources and physical enrollment/rollback controls. Built
  and signature-verified the candidate APK without installing over the working app.
- Actual separate-UID probe on the frame: API23, signing + Linux verification,
  identity persistence across launches, wrong-audience rejection, validated native
  HTTPS and WEB_MESSAGE_LISTENER support all passed. **hardwareBacked=false**:
  owner must review software-backed Keystore/unsupported-OS risk before enrollment.
- Added atomic snapshot/revision publication, bounded outage backoff/jitter,
  Retry-After, private SQLite state, pending-write reconciliation across polls and
  restarts, stricter DAV paths and recurrence/ambiguous-resource gates. Candidate
  bridge unit keeps stale-cache service alive when Radicale stops; unit syntax passed.
- No noninteractive sudo authorization remained. Per the absence instructions,
  privileged deployment was skipped. No live credentials read/reset, no live task writes,
  no services restarted, no phone/default-list/iCloud changes and no new Serve mapping.
- Read [device-auth design, acceptance and exact staged resume steps](pf1007l-device-auth.md)
  before changing anything. Remaining gates: owner review + scoped sudo, controlled
  candidate deployment and physical cookie/renewal/revocation tests, cellular phone
  tests, real recurrence semantics, soak/restore and a separately approved reboot.


## Exact resume procedure

1. Run `git status --short --branch` and `git log -1 --oneline`; stay on the current
   feature branch and preserve any later local work. The checkpoint is pushed only
   to the existing `origin` fork (`beestr0/kitchen-frame`), not merged to main.
2. Read this handoff and [hardening priorities](pf1007l-reminders-hardening.md).
   **Next step: review and activate the tested device-auth candidate in controlled
   demo acceptance**, following [the activation runbook](pf1007l-device-auth.md).
   Software-backed key acceptance and fresh scoped sudo are required. Do not start
   another provider or migrate any personal task list.
3. Use `ssh -o BatchMode=yes pf1007l-mint` for read-only health checks:

   ```sh
   systemctl is-active pf1007l-reminders-demo.service pf1007l-reminders-bridge.service pf1007l-proxy.service pf1007l-proxy-https.service jellyfin tailscaled
   systemctl is-enabled pf1007l-reminders-demo.service pf1007l-reminders-bridge.service pf1007l-proxy-https.service
   tailscale serve status --json
   curl --fail --silent --max-time 8 --resolve beestr0.duckdns.org:8789:10.157.1.115 https://beestr0.duckdns.org:8789/__proxy_health
   ```

4. Do not rerun installation. Check the current frame IP if it cannot connect; .76
   was last verified. The native privileged session is deliberately finished. If a
   new reviewed privileged phase needs sudo, stage its reviewed script and atomically
   queue its phase/checksum **before** opening `integration_native.sh` in a NEW native
   Terminal; the old queued `finish` action otherwise exits immediately. Verify the
   actual prompt. Never collect a password in chat or reuse the expired SSH socket.
5. Re-run only checks appropriate to the next change. Commands for the current
   suite: `npm test` and `npx vite build --config vite.config.reminders.js` in
   `dashboard/`; Python unittest discovery in `deploy/lan-proxy/tests`, `deploy/ssh`,
   and `deploy/reminders` (bridge fixtures need the installed vobject runtime on Mint).
   Also run `node --test scripts/reminders-demo-proxy.test.mjs` from the repo root.
   Physical evidence remains ignored; no task data/credentials belong in commits.
   Candidate fixture sources (not a service) are staged privately at
   `/home/hub/pf1007l-autonomous-tests.xc2ZzG`. Run the full Reminders fixture suite
   there using `/opt/pf1007l-reminders-demo/venv/bin/python -m unittest discover -v`.
   Build the offline APK with `python3 kiosk/lan-tls/build.py --auth-candidate`;
   output `kiosk/build-auth-candidate/frame-auth-candidate.apk` is ignored and is
   **not** the APK currently installed on the working kiosk. A disposable capability
   probe remains installed as `com.huntsyea.frame.authprobe`; it is not enrolled and
   has a separate key/application UID. It finishes back to the working kiosk.

## Current result — verified demo loop

The iPhone's native Reminders account is connected successfully. **Do not repeat
installation or account discovery troubleshooting.** Only the disposable
`PF1007L Test` collection is integrated; no existing iCloud reminders/defaults changed.

Verified: phone edit → Radicale → actual frame Tasks/Week/Month → completion tapped
on frame → Radicale → owner-confirmed completion on iPhone. The return to iPhone
was delayed until a later app refresh, so this is not instant push. Owner then
completed the undated test on iPhone; the frame removed it automatically without
reload. Siri explicitly created `Siri dashboard pilot` in the demo list; its new UID
and automatic appearance in frame Tasks were verified. That reminder remains open.

Read [integration results, security limits and rollback](pf1007l-reminders-integration.md).
The older [pilot status](pf1007l-reminders-pilot-status.md) includes historical
pending/failed checkpoints; its latest section is superseded by this handoff.

## Persistent access and running services

- Use **`ssh -o BatchMode=yes pf1007l-mint`**. Dedicated Ed25519 key on the Mac,
  strict remembered-host verification; BatchMode also passed with the agent disabled.
  Never recreate the expired temporary SSH control socket. See
  [SSH instructions](../deploy/ssh/README.md). Sudo remains a separate private prompt.
- Mint: `hub@10.157.1.115`. Frame is now **10.157.1.76**, verified by physical ADB.
  Its DHCP address changed from .247; only the dedicated HTTPS nftables table/client
  allowlist and demo bootstrap were updated. No router or unrelated firewall changes.
- **Saved frame demo URL:** `https://beestr0.duckdns.org:8789/__reminders-demo/`.
  Original weather dashboard stays at `https://beestr0.duckdns.org:8789/`.
- Radicale 3.9.1: `pf1007l-reminders-demo.service`, loopback 5238, existing root-private
  credential and VTODO collection preserved. No credential reset/reinstallation.
- Private iPhone endpoint: `https://hub-inspiron-5570.tailb76e1b.ts.net:443/` via
  Tailscale Serve to loopback Radicale; **Funnel remains off**.
- New `pf1007l-reminders-bridge.service`: loopback 5240, fixed demo collection,
  private SQLite last-good state/operation ledger. Approximately 17–18 MB cgroup RAM;
  Radicale about 22–24 MB. Mac/USB is not a runtime dependency.
- HTTPS proxy, HTTP demo service, Radicale, bridge, Jellyfin and Tailscale were all
  active at final check. HTTPS health had zero upstream errors; Jellyfin health 200.
- Native scoped integration session was finished deliberately. Check
  `/home/hub/pf1007l-reminders-stage.LEZsOd/integration-status.json`; do not assume
  an old Terminal still holds a root session. Start a new scoped native session only
  when a new privileged action actually needs it, without reinstalling components.
- Frame left on Home in the local demo build; automatic theme preference `auto`,
  live Indianapolis weather preserved. Temporary WebView debugging and USB port
  forwarding are off. HomeHQ remains installed/data intact; default launcher unchanged.

## Isolation and actual implementation

The demo UI is built locally using `dashboard/vite.config.reminders.js` and served
only under the HTTPS prefix `/__reminders-demo/`. No cloud assets were deployed and
no private task data enters Cloudflare. All actual calendar events remain synthetic;
private iCloud Calendar access is still inactive. Weather stays independently live.

The adapter uses only `/pf1007l-demo/pf1007l-test/`. Frame IDs/revisions are opaque;
completion uses fresh GET + UID/ETag verification + conditional PUT with a durable
operation key. No task create/delete/arbitrary edit route exists on the frame.
Due dates are normalized on Linux; no ICS parsing on Android. Date-only November 14
was verified, with undated tasks only in Tasks and dated tasks in Tasks + Calendar.
Tasks poll every 30 seconds on active Home/Tasks/Calendar views. No task localStorage;
frame memory + private Linux last-good cache only. An outage disables writes and
shows stale rows; no silent browser write queue.

Cookie/CSRF/origin/backend-key and wrong-frame denial passed. Initial one-time
session provisioning still trusts the allowed source IP; it is demo-only, not
cryptographic hardware identity. Cookie lifetime is 24 hours; expiry can require
local reprovisioning. The replacement is prepared/tested in source but not activated;
physical acceptance remains a gate before personal reminders. Recurring task
completion is blocked on frame pending real occurrence-semantics tests; complete recurring reminders on iPhone for now.

## Validation and remaining work

- Autonomous source checkpoint: **180 tests passed** — 62 dashboard, 48 proxy/TLS,
  5 demo-proxy routing tests, 52 Reminders Python fixtures (5 original bridge,
  15 device proof, 6 HTTP auth boundary, 6 registry, 18 recovery, 2 discovery),
  3 SSH configuration and 10 inactive iCloud tests. Final strict-registry changes
  also passed the relevant 21-test Mint rerun. Native URL policy: **21 cases passed**.
  Ordinary desk/demo builds and candidate APK signature verification passed.
- Isolated Mint cold/renewal HTTP auth exchanges: **0.295 / 0.265 seconds**,
  fixture-process peak RSS about 30 MiB; this is not a long-term load measurement.
  Real bridge/Radicale remained ~17/~23 MiB with zero service restarts. Units active
  and enabled, dashboard health zero upstream errors, Jellyfin healthy; private
  Serve validated TLS and unauthenticated collection PROPFIND returned 401.
- Physical separate-UID browser probe: native HttpOnly cookie accepted/present,
  hidden from JavaScript; origin-aware message/reply round trip passed and channel
  absent on a different origin. These used invented cookies and in-memory pages,
  not the live authentication flow. Probe is stopped; working kiosk is foreground.
- Fresh live-demo FPS samples: **57.3–60.2 FPS**, no sampled gap over 50 ms, six
  five-second Home/Tasks/Calendar/theme samples. Original light theme/Home view
  restored, automatic preference unchanged; debugging and USB forwarding off.
  This measures the unchanged deployment, **not** candidate runtime performance.
- Current checkpoint secret checks: Gitleaks 8.30.1 staged diff **and entire staged
  index** (260 files), with allow-comments ignored: zero findings. Supplemental
  private-key/header/JWT and sensitive-artifact checks also passed. Build outputs,
  runtime settings, credentials, databases and physical diagnostics are excluded.
- Mac free space remained ~13 GiB; Mint ~846 GiB. Retained Android dependencies
  were used offline; no large downloads or server/OS restart occurred.
- Original deployment checkpoint rerun: **118 tests passed** (50 dashboard, 48 proxy/TLS, 5 bridge,
  2 redirect-origin, 3 SSH configuration and 10 inactive iCloud tests). Both demo
  and ordinary desk production builds passed. Read-only runtime inspection confirmed
  active services, startup enablement and private Serve; a full Linux reboot is
  still untested. Physical evidence is ignored under
  `diagnostics/pf1007l/reminders/` and `/private/tmp/pf1007l-*`.
- At deployment checkpoint `3a74a35`, deployed adapter/proxy/final demo UI hashes
  matched that source/build. The new candidate deliberately differs and is not
  deployed. Its earlier staged-diff/full-index scans found no secrets;
  supplemental private-key/JWT/header and sensitive-artifact checks also passed.
  Reports stay ignored. Runtime passwords, bridge/session values, databases,
  private keys, SSH client files and diagnostic payloads are not committed.
- Original deployment-checkpoint frame Home/Tasks/Calendar: **59.95–60.15 FPS**, no sampled
  gaps over 50 ms. Task-only simulated 503 retained data/disabled completion and
  recovered. Live conflict returned 409 without overwriting an edit; adapter restart
  preserved IDs and session. A UI poll race was removed after an overly short
  five-second assertion; final server/UI/phone state was confirmed.
- Still test Mac-off Wi-Fi/cellular, locked-app/background fetch delays, reconnects,
  native timed reminders/DST, recurrence, multiple lists, long-running idempotent
  recovery, retention/backup restore and session renewal. Do not call it ready for
  personal everyday tasks or migrate iCloud lists based on this small demo.
- Owner-approved private iCloud Calendar remains the separate **read-only** plan;
  no Apple credentials collected and no account access activated. Continue from
  [calendar proposal](pf1007l-private-icloud-plan.md) when specifically authorized.
  Spotify Now Playing and Bambu A1 Mini remain later, separately authorized stages.
  Todoist is superseded and must not be activated.

## Preserved HTTPS/weather and recovery

ZeroSSL dashboard certificate/renewal/monitoring remain in place; dashboard cert
expires 2027-02-12 23:59:59 UTC. Tailscale's separate verified TLS 1.3 certificate
expires 2027-02-12 13:30:19 UTC. Certificate timers remain scheduled. No router DNS,
trusted-root changes, launchers, Jellyfin, media mounts or unrelated Cloudflare
resources were changed. Existing Linux-only routing still avoids gateway DNS issues.

A caught demo deployment error temporarily set the non-secret HTTPS config to 0600;
its original 0644 mode was restored, and HTTPS health verified before proceeding.
Credentials stayed private. Rollback source and saved original config/code are
prepared; do not repeat that deployment mistake or loosen credential permissions.

[Rollback instructions](pf1007l-reminders-integration.md) disable only the new bridge
and restore original proxy code/config while retaining the current verified frame
IP. Preserve Radicale data/credentials/Serve. To return just the kiosk URL to the
original dashboard:

```sh
adb -d shell am start -n com.huntsyea.frame/.MainActivity -d https://beestr0.duckdns.org:8789/ --ez debug false
```

HTTP 8788 is still synthetic but retains the previous .247 client rule; do not
promise it as a working fallback for today's .76 frame without reviewing that
specific rule. Future DHCP changes fail closed; no reservation was added.

HomeHQ remains available via `adb -d shell am start -n com.wesbos.homehq/.MainActivity`.
Never clear app data, uninstall HomeHQ, change the default launcher, reset Serve,
flush firewalls, delete reminders or revoke credentials as an automatic recovery.

Other references: [HTTPS services](pf1007l-https-installation.md),
[weather](pf1007l-weather.md), [cost limits](pf1007l-https-costs.md),
[APK/permanent URL](pf1007l-permanent-https.md). Private backups/tooling remain ignored.
