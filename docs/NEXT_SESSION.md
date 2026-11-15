# PF1007L — next session

## Completion sprint — November 15, 2026 (current state)

**The approved sprint is deployed. This section supersedes historical manual-start,
two-calendar and hard-coded task-name statements below.** Remain on
`feat/pf1007l-https-weather-handoff`; use `git log -3` for the final checkpoints.
No new pages, tabs or integrations were introduced. Home layout/styles are unchanged.

- Linux server verified `hub@10.157.1.115`; workshop laptop `.141`; USB frame `.146`.
  The old `pf1007l-mint` SSH alias is absent on this laptop: use the existing verified
  `hub@10.157.1.115` host entry. Strict host verification was not weakened.
- **Four live calendars**: original two identities retained, Work now **School**;
  **General** and **Appointments** added by exact iCloud collection identity using
  existing credentials. Existing colors preserved/refreshed from provider metadata.
  Frame112 occurrences,112 distinct UID/start/end keys, fresh. No Apple writes.
- **Do It** comes from the existing fixed Radicale collection displayname, not a new
  collection or migration. Six current task records/fresh. Deployment compared
  task identities, versions, completion/due state before/after and found no changes.
  Actual task completion was not repeated; existing bidirectional code/recurring
  safeguards retained and fixture regressions passed.
- Calendar now reads selected-collection name/color metadata each normal upstream
  refresh (~5min). Task name is refreshed every5min on normal successful polling.
  Last-good metadata survives offline/restart. Dashboard labels consume metadata
  rather than hard-coded names; collection and task IDs never depend on names.
- **Automatic startup passed one real warm reboot** through supported default HOME
  selection. HiveOS was already foreground before any manual launch; static `.146`
  reconnected, enrolled device-v1/authenticated data recovered. Vendor boot-receiver
  blocking was left intact. A physical unplugged cold-power test was not performed.
- New original fine-line vector bee and exact **get shit done.** installed in the
  native startup overlay; light/dark palette, useful loading/error/retry controls,
  prompt ready transition retained. Native label presence verified during an
  offline WebView reload; automatic recovery returned Home. An attempted splash
  screenshot caught recovered Home and was deleted locally/on-device.
- Same package, original signer, version6, UID10026, saved native preferences hash
  unchanged. No uninstall/data clear, credential reset or new enrollment.
- Etar, ICSdroid and the unenrolled auth probe disabled reversibly with data intact.
  Rootless, HomeHQ and all34 system packages preserved; three previously disabled
  manufacturer packages were left as found. See package restoration table in runbook.
- Seven services active/enabled; HTTPS upstreamErrors0. Installed collector, CalDAV
  reader, bridge and UI index SHA256s match reviewed local source/build. Linux/frame
  runtime still has no laptop, USB, terminal or Codex dependency. No Jellyfin,
  Tailscale, router or Linux reboot/config change.
- Post-reboot Home60.1822FPS over5s, no >50ms gaps,max16.617ms. Calendar/Tasks/session
  200, device-v1; unauthorized401/query400/write405; no private task/calendar storage
  keys in localStorage. Temporary debugging/USB forwarding off; left on normal Home.

### Checks and bounded limitations

Dashboard73 tests; Calendar30 tests; server Reminders78 tests plus3 new fixed-list
metadata boundary tests passed. Native startup gates and21 URL-policy cases passed;
production web build and original-signer APK build/verification passed. Initial
local Reminders run lacked vobject, so the existing server venv ran the source-only
fixtures instead. One dashboard subprocess check failed inside sandbox with missing
stderr; all73 passed outside sandbox. Complete initial logs remain in `/tmp/hiveos-*`
on the workshop laptop; server fixture log is
`/home/hub/hiveos-sprint-20261115/reminders-tests.log` (no live data).

Bounded review of reported spontaneous Calendar date changes found offsets changed
only by explicit button handlers, no timer/key/swipe navigation path. Cause was not
established; no speculative fix or prolonged ghost-touch investigation. Future
reproduction should distinguish trusted touch/external input from automation;
never log personal calendar contents. No phone edit/completion roundtrip, new
physical finger-hold check, power-unplug test or multi-day soak was repeated.

### Deployment and recovery

Owner ran the staged verified root helper after privately entering sudo; returned
DEPLOYED/healthy, independently corroborated by live frame checks and code hashes.
`deploy/hiveos/finish_sprint.py` is the bounded source helper; **do not rerun it just
to inspect health**. Frozen source-only bundle SHA256
`df199ffa101599cd0d36ffdcb8df8c590d1870a415d0533a52999fe395b9b7ca`.
Private frozen copy `/root/hiveos-sprint-20261115`; original stage
`/home/hub/hiveos-sprint-20261115/release.tar`. No credentials in these bundles.
Root-private backup under `/var/backups/pf1007l-sprint/<UTC timestamp>/` includes
prior config/source/UI and consistent task SQLite. Find the exact directory from
root and read its `rollback.txt`. Restore only previous code/config/UI and restart
Calendar/bridge; **never rewind current task SQLite/operations or Radicale data**
for normal rollback. Credentials, registry, exact-IP guards and auth remain intact.

[HiveOS runbook](pf1007l-hiveos.md#november-15-completion-sprint--supported-home-startup-verified)
has APK hashes, signed known-good v6 location, default-Home reversal, Android Settings
escape, and three package restore commands. Hold two fingers2s → Home app settings
(or Android settings → Home) → select Rootless radio to reverse the default.
Settings and HomeHQ launches were verified before changing Home. Existing physical
escape gesture implementation is unchanged. Prefer normal use now; no additional
features or excluded integrations are pending from this sprint.

## Historical handoff (retain for evidence; current summary above takes precedence)

## End-of-day handoff — November 14, 2026

**Owner confirmed static Wi-Fi is saved and HiveOS is connected and working.**
Development is stopped for tonight. Branch `feat/pf1007l-https-weather-handoff`.
Read this handoff before doing anything; do not repeat setup, installation or passed
Calendar/Reminders/authentication tests. No production/personal Reminders migration
is authorized. Use `git log -1` and upstream to identify the final handoff commit.

Current working configuration:

- PF1007L saved Wi-Fi profile: **Static IP10.157.1.146**, gateway10.157.1.1,
  network prefix24, DNS10.157.1.1. Applied and confirmed working by owner, not Codex.
- Router reservation at .146 and server exact-IP guards unchanged. Separate older
  HiveOS reservation at .152 with another MAC must remain untouched.
- HiveOS v6/1.5-hiveos, package com.huntsyea.frame, activity .MainActivity, UID10026,
  original signer, saved URL and enrolled key preserved. No uninstall/data clearing.
- Live selected read-only Apple Calendar, demo Reminders, Siri, persistent device
  authentication, weather, auto themes and existing controls remain the working
  deployment. Last measured v6 performance60.1627FPS predates the cold-boot test;
  no new performance or integration test was requested tonight.
- Linux Calendar collector, Radicale demo, auth/Reminders bridge, HTTP weather proxy,
  HTTPS dashboard proxy, Jellyfin and Tailscale all **active and enabled** in final
  read-only check. HTTPS health returned successfully with upstreamErrors0.
- Collectors, weather proxy, credential storage, session renewal and private Serve
  run on Linux/frame, independent of MacBook, Codex, USB or interactive Terminal.
  Keep Linux server/router/frame powered and network available. No service restarts,
  network edits, installs or additional physical tests performed during handoff.

### Accepted boot limitation and recovery

One supervised cold boot exposed vendor changing Wi-Fi MAC (DHCP assigned .25) and
BackgroundManagerService blocking HiveOS BOOT_COMPLETED. Static profile now restores
manual use without changing the allowlist. **Automatic launch after full reboot is
currently unsupported on this firmware; manual HiveOS launch is the accepted
workaround.** No supported startup settings/explicit allowlist setter found. Do not
modify protected vendor policy, replace the launcher or claim boot autostart works.
Static-profile persistence across a subsequent cold boot remains unverified; no new
reboot is authorized by this handoff. Retry/error screen and Android Settings remain
available; default launcher, HomeHQ and manufacturer splash are unchanged.

See [HiveOS runbook and signed rollback](pf1007l-hiveos.md). Private network/config
backup and consistent task SQLite snapshot:
`/var/backups/pf1007l-network/repair-20261115T003609Z-4c550191`.
Same-version/same-signer rollback APK is retained privately. Do not deploy rollback,
reset credentials, clear application data or repeat network repair without cause.
WebView debugging was disabled and temporary USB forwarding removed after v6 tests.

### Remaining limits and next priorities — no work started

1. Use the wall-mounted dashboard normally; manual launch after power loss accepted.
2. Only if requested, verify saved static profile across one agreed future cold boot.
   No further autostart investigation unless a supported manufacturer option emerges.
3. Recurring Reminder completion remains disabled; use disposable automated fixtures
   before considering support. No migration or production sync without approval.
4. Background iPhone timing has no guaranteed SLA. Existing Calendar refresh is
   five-minute upstream plus up to one-minute frame polling. Preserve read-only scope.

Resume tomorrow from a native Terminal:

```sh
cd /Users/beestrother/Projects/kitchen-frame && codex "Read docs/NEXT_SESSION.md and docs/pf1007l-hiveos.md. Review Git status. Preserve the working static-IP HiveOS deployment and accepted manual-launch workaround. Summarize the handoff before making changes."
```

For Linux inspection use persistent `ssh pf1007l-mint`; no temporary control socket.
No sudo/observer Terminal is required for ongoing dashboard operation. Closing
Codex/Terminal or sleeping/shutting down the MacBook does not stop these services.

## Earlier verified integration details (historical observations)

## Live Apple Calendar activated and physically accepted

Owner authorized Option B (existing Apple Account, dedicated app-specific password),
calendar-only discovery, selected-event retrieval/cache/display and automatic Linux
refresh. Secure native credential/selection setup completed. **Two calendars are
selected; latest snapshot110 events, fresh.** No Apple write operations, unrelated iCloud
access, Reminders migration or public exposure occurred.

Tested candidate from `5687b90` is now deployed: separate `pf1007l-calendar.service`
active/enabled, collector/SQLite on Linux, existing device-authenticated calendar
route, Home/Month/Week/new Day views. Existing dashboard/Reminders/auth/weather
remain healthy; private Serve unchanged. Code hashes match frozen v3 manifest.
Automatic refresh advanced from 23:20:47.494155Z to 23:25:51.613033Z without manual
refresh. No Mac runtime dependency or APK replacement; only the page was reloaded.

Actual frame checks: calendar/session/tasks200, private source109 events/2 calendars,
fresh; colors valid and events restricted to selected calendars; no private event
cache in localStorage; unauthorized calendar401, query400, write405. Reminders11
records/fresh, weather visible. Home dark/auto sample **60.1559 FPS**, zero >50ms,
max gap16.624ms. Debugging OFF and USB forwarding removed afterward. Do not capture
personal screenshots/DOM/titles or return calendar names/account details to chat.

Owner completed the consolidated acceptance batch: familiar appointments in the
requested Home/Day/Week/Month views confirmed; a check event created on iPhone
appeared after approximately5 minutes and an edit appeared approximately6 minutes
later. These are owner-reported approximate observations, not precise latency/SLA.
No repeated physical tests are needed. No Apple event writes were issued by code.
Automatic refresh is five-minute upstream plus up to one-minute frame polling.
Final aggregate check:110 events/two calendars,stale=false,updated23:46:01.290225Z,
all services healthy. The scoped root session was deliberately **finished** at
Unix1794700179.1735399. WebView debugging OFF, USB forwarding removed. Native
Terminal can close; collector/device authentication do not depend on it or the Mac.
No physical Mac-off/reboot or live cancellation test was performed; read-only code,
fixtures and systemd independent operation are verified. These are documented limits,
not another interactive gate. Recurring task completion remains disabled.

Original restorable backup/consistent task SQLite:
`/var/backups/pf1007l-calendar/activation-20261114T231606Z-0b2c3d0c/backup`.
Initial attempt failed CHDIR/200 because installer left public code root0700 under
umask077. It stopped and rolled back before bridge/proxy/UI activation. Corrected
recovery verified original backup and installed files, set public code directories
0755 (private credentials/state remain0700/0600), reset only new collector's failure
limit, and successfully resumed. No task DB rewind or Apple credential reset.
Controller SHA256 `02954c789d4271db4e67b56f17a7b29d9dd0a6378b1f00ba6f531511758c14dc`.
27 focused Calendar/setup/recovery tests passed; original candidate111 relevant
checks/build/Linux pipeline also passed. Root control/retry code and final acceptance documentation are checkpointed on
the existing feature branch; use `git log -1` for the final activation commit. No further reader-account creation attempts.

Read [implementation/deployment/rollback runbook](pf1007l-calendar-integration.md).
Frozen v3 manifest: `b392c9f1babe4028ac7dd3a6ecca60693bc79a64f801d8f8dfc1b699b830c1ef`.
Local ignored artifacts `diagnostics/pf1007l/calendar-candidate-v3`, Mint stage
`/home/hub/pf1007l-calendar-candidate-v3-review`. Credentials exist only root-private
under `/etc/pf1007l-calendar`; state DynamicUser0700 under `/var/lib/pf1007l-calendar`.
No real calendar titles/credentials/runtime cache in Git. For rollback restore
bridge/proxy/UI code and remove only introduced calendar unit/drop-in, stop only
calendar, preserve current task SQLite/Radicale and private credentials/data. Do not
use the old whole-demo rollback script or restore task history from old snapshots.

## Cellular/Tailscale milestone closed — November 14

Read [the timestamped report](pf1007l-cellular-testing.md). Owner-confirmed home
Wi-Fi baseline, cellular creation/return completion, Siri phone/frame visibility,
offline creation/reconnect recovery, completion visible at unlock and Wi-Fi-return
reconciliation passed. All five synthetic reminders appear once with expected
states; Tailscale connected, no account warnings. Observed return delays: 100 s
foreground, approx. 55 s at unlock; reconnection recovered by approx. 48 s. Two
current automatic renewals observed; all services healthy, no restart/redeployment.

**Exact background fetch and long-term cellular reliability are not fully verified.**
Siri transcription variant lacks direct server UID/timing because of the exact-title
observer filter. No Calendar-view recheck, Mac-off run or new FPS measurement was
performed. Next feature: live private Apple/iCloud Calendar after detailed requirements.
Longer background timing/soak are separate nonblocking work, not another interactive gate.
Read-only observer remains bounded to one hour from about 21:37 UTC; it may exit
naturally or owner can Ctrl+C its native Terminal. Do not assume it is still alive.
Its private JSONL remains on Mint; no credential/runtime evidence belongs in Git.
Observer source/tests and result docs are included in the cellular checkpoint. Deployment controller
stays finished; no service or personal-account configuration changed.

## Streamlined workflow — owner instruction

Prefer focused automated unit/integration/disposable CalDAV tests. Reuse passing
regressions; retest only behavior affected by changes. Use controlled fixture clocks
for session expiry; do not wait through real 15-minute lifetimes again. Run long
soaks separately from feature work. Complete implementation and automated checks
before presenting one short consolidated hardware test list; collect results
in a batch. Hardware checks are only for genuinely new hardware-dependent behavior.
Time-box noncritical diagnosis, document limitations and continue independent work.
Do not bypass critical failed gates. Preserve security, current deployment, default
lists and personal iCloud data. No production or personal migration is authorized.

## Exact resume procedure

1. `git status --short --branch` and `git log -1 --oneline`. Preserve local work and
   remain on the existing feature branch. Do not repeat setup, discovery or enrollment.
2. Read [verified activation report](pf1007l-device-auth-activation.md),
   [security/rollback plan](pf1007l-auth-security-review.md), then
   [remaining hardening priorities](pf1007l-reminders-hardening.md).
3. Read-only health through **`ssh -o BatchMode=yes pf1007l-mint`**:

   ```sh
   systemctl is-active pf1007l-reminders-demo.service pf1007l-reminders-bridge.service pf1007l-proxy.service pf1007l-proxy-https.service jellyfin tailscaled
   systemctl is-enabled pf1007l-reminders-demo.service pf1007l-reminders-bridge.service pf1007l-proxy-https.service
   tailscale serve status --json
   curl --fail --silent --max-time 8 --resolve beestr0.duckdns.org:8789:10.157.1.115 https://beestr0.duckdns.org:8789/__proxy_health
   ```

4. **Next priority: account-scope approval and live Apple Calendar activation**,
   using the already implemented/tested candidate and consolidated runbook.
   Keep recurring completion blocked until proven correct. Do not repeat completed
   physical cellular/auth tests. Personal-account access requires separate approval.
5. All scoped native root sessions are finished. Normal operation needs neither
   sudo nor Mac/USB. Do not reuse old queues/windows/control sockets or run recovery
   helpers against this healthy deployment. Obtain a new private native session
   only for a genuinely required, scoped maintenance action; never collect passwords
   in chat or repeat calendar account setup without a diagnosed need.
6. Run only relevant tests. Dashboard `npm test`; Node proxy
   `node --test scripts/reminders-demo-proxy.test.mjs`; Python discovery under
   `deploy/reminders`, `deploy/lan-proxy/tests`, `deploy/ssh`, `deploy/icloud-calendar/tests`.
   Reminders vobject/dateutil runtime is installed on Mint; fixture stage
   `/home/hub/pf1007l-autonomous-tests.xc2ZzG` is source/test-only, not a service.
   Its files are at the directory root: run `python -m unittest discover -s .`
   there using `/opt/pf1007l-reminders-demo/venv/bin/python`. Local HTTPS listener
   tests require permission to bind loopback sockets.

## Checkpoint verification and recovery

The activation checkpoint contains only source, tests and documentation: fixed-scope
native authorization/deployment helpers, readiness/rollback regression tests,
same-signer/same-version rollback build support, and the security/activation runbooks.
Runtime settings, device credentials, cookies, private keys, APKs, task databases,
backups and physical-device diagnostics remain outside Git. The original private
Linux backup is necessary for operational rollback; GitHub is not a credential or
task-data backup. Complete tracked-history and proposed-source-tree secret scans
passed before the checkpoint was committed.

The fork is `https://github.com/beestr0/kitchen-frame`, branch
`feat/pf1007l-https-weather-handoff`. To inspect or recover source independently of
the live deployment, clone the fork into a separate directory and check out the
checkpoint commit reported in the session. Do not reset a later working tree or
run deployment helpers as an incidental Git recovery step. The checkpoint itself
requires no dashboard/service restart, enrollment or credential change.

### Checkpoint test rerun

All 195 distinct relevant tests succeeded across the checkpoint runs: dashboard 62,
proxy/TLS 48, Node demo proxy 5, SSH 3, inactive iCloud preparation 10, and Reminders
67. The initial 67-test run had one three-second loopback HTTP timeout in the old-CSRF
regression (66 passed); that unchanged test passed alone, then all six HTTP boundary
tests passed together. No timeout/security check was relaxed. Preserve this timing
flakiness as a follow-up, not an unqualified claim of a clean first run. Mint's
source-only fixture stage retains `checkpoint-tests.log` and
`checkpoint-http-retest.log`; these logs are not Git artifacts. Fixture modules and
their imported core match local source. Deployment health remained good with no
service restart/redeployment during checkpoint creation.

## Current verified result

- Actual kiosk v5 `1.4-auth-candidate` installed in place, same signer/UID and app
  data. Owner physically verified public fingerprint and enabled native mode.
- One authorized device, device-v1, signed one-use proofs, server-enforced 900-second
  sessions with automatic renewal. Legacy cookie rejected; no weaker auto fallback.
- **32-minute continuous observation passed**: 44 healthy samples, two automatic
  renewals, zero reloads/manual renewal/password. App process restart, real bridge
  restart, 90-second browser-network loss (4.023-second automatic recovery), and
  960-second actual bridge outage with natural session expiry all passed.
- Expired-session fresh proof succeeded with **debugging off**, ~5.4 seconds after
  scheduled restart; healthy recovery observed within 22.65 seconds. Independent
  recovery timer fired and was collected. No clock/session-duration manipulation.
- Revocation rejected existing reads/renewal/completion, removed sessions and disabled
  UI writes. Controlled re-enablement/new epoch recovered automatically with fresh proof.
- Owner-confirmed iPhone create/edit → same task/correct frame Calendar date → frame
  completion → iPhone completion, due date preserved. Original Siri demo still open;
  existing iCloud/default lists untouched. Native CalDAV fetch can be delayed.
- **195 tests passed**; core runtime code/unit hashes match `8aade81`.
- Settled views/themes ~59.99–60.16 FPS; final Home 59.77 FPS, no >50 ms gap.
  Earlier transition/minute-theme samples had 55.7–60.2 FPS and occasional long gaps;
  do not claim universally jank-free transitions.
- All services healthy/enabled as appropriate, HTTPS upstream errors zero, Jellyfin
  healthy, private Serve unchanged/Funnel off. Jellyfin/Tailscale/Radicale were not
  restarted. Bridge/Radicale memory ~18/~19 MB.
- Frame left on normal Home/light with auto theme preserved. **WebView debugging off,
  USB forwarding removed, temporary Mac sleep assertion stopped, root session finished.**
  Disposable auth-probe app from earlier investigation remains installed but stopped;
  it is a separate UID/key and never enrolled. HomeHQ and default launcher preserved.

## Backup, security and rollback

Private backup + consistent SQLite snapshot:
`/var/backups/pf1007l-device-auth/backup-20261114T192145Z-7aef9bbe`.
Frozen artifacts/diagnostics: matching `artifacts-20261114T192145Z-7aef9bbe`.
Status/queue stage: `/home/hub/pf1007l-device-auth-review.yt5Otk`; latest phase finished.
Controller SHA256:
`e1e0c3be7013fecc080d0e682b31eaa842e7cec31c5d2c0b3433ebcae472bc30`.

The initial immediate HTTPS check raced startup (curl exit 7), including the rollback
verification. Original files/UI/private configuration were restored and verified,
then bounded readiness waits/stale-action protection were fixed and tested before
retrying successfully. Original diagnostics and backup remain; no failed gate bypass.

**Never restore an old SQLite snapshot over current completion/operation history for
normal rollback.** Retain current Radicale data. Restore only the current demo's
backed-up code/settings/UI and prepared same-version APK if necessary, without
uninstall/clear-data or unrelated changes. Do not use the old pre-demo rollback script.
On suspected compromise revoke/fail closed; do not fall back to legacy/IP auth.
Revocation needs bridge restart because registry is a LoadCredential startup snapshot.
After real key theft use a clean new key/device, not epoch re-enablement of that key.

Owner accepted this specific demo's software Keystore/root-ADB/unencrypted-storage
risk; hardware-backed/non-extractable-under-root protection is not claimed. Keep
fictional/non-sensitive tasks only. No production authorization follows from tests.

## Stable deployment context

- Mint `hub@10.157.1.115`, frame `10.157.1.76`. Persistent Ed25519 alias and strict
  host verification retained; no expired temporary control sockets.
- Saved demo URL `https://beestr0.duckdns.org:8789/__reminders-demo/`.
  Original dashboard `https://beestr0.duckdns.org:8789/`, live weather independently.
- Radicale 3.9.1 `pf1007l-reminders-demo.service`, loopback 5238; dedicated
  `pf1007l-demo`, fixed `/pf1007l-demo/pf1007l-test/` adapter collection.
- iPhone `https://hub-inspiron-5570.tailb76e1b.ts.net:443/`, private Serve → Radicale;
  no Funnel/router opening. Existing account/credentials preserved.
- Bridge `pf1007l-reminders-bridge.service`, loopback 5240, DynamicUser. Code/UI
  `/opt/pf1007l-reminders-bridge`, config `/etc/pf1007l-reminders-bridge`, state
  `/var/lib/pf1007l-reminders-bridge/tasks.sqlite`. Private settings/registry 0600,
  directory 0700. Preserve backend/identity key values to retain opaque task IDs.
- Non-secret HTTPS proxy config remains 0644 for DynamicUser; credentials stay
  private. Existing TLS certificates, renewal/monitoring, frame-only firewall and
  app-only CONNECT route retained. No global SSH/DNS/trust/router/launcher changes.
- Native `com.huntsyea.frame`; HomeHQ `com.wesbos.homehq` installed/data intact.
- No create/delete/arbitrary-edit frame task route, no ICS expansion on frame,
  no browser task-data cache or offline write queue. Recurring completion blocked.
- Private iCloud Calendar remains inactive/read-only preparation; calendar events
  beside actual reminder markers remain synthetic. See
  [calendar plan](pf1007l-private-icloud-plan.md); separate authentication/selection
  approval needed. Todoist superseded. Spotify/Bambu remain later separate stages.
- No personal task-list migration, default-list change, production sync, public
  exposure, unrelated-service restart or computer reboot is authorized.

## Completed recovery history — do not rerun

Initial CHDIR failure, automatic rollback and corrected resume are recorded above
and in the integration report. The original backup remains untouched. Native root
sessions are finished; old window IDs/queue files are not active authorization.
Do not run `start_activation.py --resume` on the active deployment: that recovery
mode expects the restored pre-calendar baseline, not a healthy running calendar.
