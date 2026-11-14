# PF1007L — next session

November 14, 2026: **persistent device authentication activated and demo acceptance
passed**. Branch `feat/pf1007l-https-weather-handoff`; reviewed core checkpoint
`8aade81` supplies the deployed core. The following Git checkpoint records the
verified activation tooling, recovery tests and documentation. Use `git log -1`
and the branch upstream to identify its final commit; no deployment is required
to restore this source checkpoint. No production/personal migration is authorized.

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

4. **Next implementation priority: controlled cellular/Tailscale reconnection and
   background-fetch acceptance**, using disposable tasks only. Then actual recurring
   reminder semantics, multi-day reliability/restore and a separately approved full
   Linux reboot. Do not start another provider or migrate personal lists.
5. The scoped native root session was deliberately **finished**. No password is
   needed for ordinary runtime authentication. Do not assume an old Terminal or
   temporary SSH socket still holds authorization. If a new approved privileged
   phase is needed, use a NEW native Terminal and
   `python3 /Users/beestrother/Projects/kitchen-frame/deploy/reminders/activate_native.py --resume`.
   It privately prompts, pins the controller and resumes the existing root-private
   checkpoint/backup. `--recover` expects a restored legacy baseline and is wrong
   for this active device-v1 deployment. Do not queue old deploy/finish actions.
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
