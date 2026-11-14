# Device-auth security review and controlled acceptance

Status: owner approved the software-backed/physical-access tradeoff and controlled
activation. The actual device is enrolled and device-v1 is active. Native renewal,
phone round trip, app/backend restart, expiry/network recovery and revocation
acceptance all passed. See [live activation status](pf1007l-device-auth-activation.md).
This remains disposable-demo-only. Source checkpoint: `8aade81`.
This review does not authorize production tasks, personal lists or any migration.

## Recommendation and actual device posture

Software-backed Android Keystore is a reasonable component for this **non-sensitive,
disposable demonstration**, provided the owner accepts that physical/USB access or
OS compromise can take over the frame. The protocol improves remote authentication
and revocation; it cannot turn this device into a secure storage appliance.

Read-only checks on this particular frame found:

| Check | Observation | Consequence |
| --- | --- | --- |
| Keystore probe | `hardwareBacked=false` | No hardware isolation/attestation for the tested key |
| Storage | `ro.crypto.state=unencrypted` | No whole-device encryption protection established |
| ADB shell | UID 0/root | Debug access provides system control |
| ADB authentication | `ro.adb.secure=0` | Do not rely on a trusted-computer authorization prompt for USB access |
| OS policy | SELinux Disabled, `ro.secure=0`, `ro.debuggable=1` | App isolation cannot be relied on against a system attacker |
| Patch property | 2016-07-05 | Very old platform security baseline |
| Listener snapshot | Only `127.0.0.1:5037` visible; TCP ADB properties blank | No network ADB listener visible in this check; not a permanent guarantee |
| Verified-boot properties | Blank | Boot-lock/integrity status not established |

No setting was changed. No key files, app preferences, cookies or other app data
were inspected. The installed APK alone was copied for signing/rollback provenance.
These findings are device-specific, not claims about every Android 6 device.

Android Keystore keeps raw key material outside the app process and provides
non-exporting signing handles. Hardware backing adds protection when the OS or
storage is compromised. That extra boundary is unavailable here. See the official
[Android Keystore security model](https://developer.android.com/privacy-and-security/keystore).
Unencrypted storage does **not** prove that an individual Keystore blob is plaintext;
no extraction was attempted. Nevertheless, treat the device credential as usable
and potentially recoverable/clonable after physical/root compromise. Adding a
symmetric secret encrypted by another software-held secret would not fix this.

## Practical scope and residual risk

1. **Device identity:** a different P-256 key per enrolled application/device,
   root-reviewed public registry, no self-enrollment endpoint. Ordinary copying of
   APK/public fingerprint cannot authenticate another device. There is no remote
   hardware attestation or assurance against cloning after OS compromise.
2. **At rest:** no raw private key exported by this app; Android Keystore signing
   handle, app backups disabled, server registry/settings 0600 in a 0700 directory.
   This is protection under an honest OS, not theft resistance on this rooted,
   unencrypted frame. Provider/DAV/SSH private credentials are not introduced onto
   the frame by this integration. Existing HomeHQ/dashboard data was not audited.
3. **Least privilege:** the frame API reads and completes only the fixed
   `/pf1007l-demo/pf1007l-test/` collection. No create/delete/arbitrary-edit API.
   The distinct CalDAV account has broader native Reminders capabilities within its
   own demo namespace (`owner_only` configuration, collection deletion/overwrite
   disabled). It is not a per-collection read-only DAV credential. Never add personal
   lists to that account. Root compromise of Linux is outside this boundary.
4. **Sessions:** server-enforced 900-second expiry, hash-only token storage,
   HttpOnly/Secure/SameSite cookies, renewal through native proof, bounded retries.
   A stolen cookie may be useful until expiry or revocation. A stolen **device key**
   can obtain fresh sessions indefinitely until revoked; 15-minute sessions do not
   limit a stolen key to 15 minutes.
5. **Remote/browser protection:** validated TLS, exact origin/purpose nonce proof,
   60-second nonce expiry, atomic one-use consumption, rate limits, per-session CSRF,
   main-frame/origin-aware bridge, restricted navigation and no legacy fallback in
   device mode. Backend proxy key and existing frame-IP restriction remain additional
   controls. IP restrictions are not device identity and do not stop a LAN attacker
   who can impersonate that address. XSS or control of the authorized app can use its
   session; HttpOnly is not a defense against all actions from a compromised origin.
6. **Physical access:** anyone at the unlocked kiosk can see displayed tasks and
   complete them without exploiting anything. USB/root access adds app impersonation,
   cookie/key use, other local-app data access and possible LAN attacks. The demo
   API scope does not sandbox a compromised OS or protect unrelated applications.
7. **Loss/compromise:** revoke the public device entry, restart only the bridge to
   load the new credential snapshot, and verify old cookies/proofs fail. Registry
   edits alone do not apply live revocation. Keep the server reachable restriction;
   isolate the frame from the LAN if possible. Use a clean device/new key afterward.
   Epoch rotation re-enables the same key and is **not** recovery from key theft.

Recommended operational boundaries: trusted home/LAN, physically controlled USB,
wall power/charge-only connection when diagnostics are finished, no unnecessary
apps or general browsing, and fictional/non-sensitive tasks only. Separately review
ADB hardening if desired; this plan does not disable ADB, encrypt/reset the device,
change Wi-Fi/router settings or alter HomeHQ. Do not treat this review as approval
for personal everyday reminders.

## Prepared artifacts and integrity

Private local bundle: `diagnostics/pf1007l/device-auth-activation/` (ignored by Git).
Private server review stage: `/home/hub/pf1007l-device-auth-review.yt5Otk/`.
Neither directory is a service or watched deployment path. Their verified artifacts
were frozen privately for approved deployment; actual registry enrollment and native
enablement are recorded in the live activation report.

Bundle includes source, bridge unit, credential drop-in template, demo UI archive,
candidate APK, read-only preflight/status helper and rollback APK. It contains no
settings, passwords, session values, task database or private keys.

Manifest SHA256:
`e1d119d6e96a548612e16751ee940a11e1951903873d6bca5b6956f788544f53`.

The candidate and rollback APK both use versionCode 5 and the installed app's signing
certificate SHA256 `fc10154a66d268e9ed36313866df7adc88ac07e3c90b59926f80e9d36bd88784`.
The rollback APK is built from checkpoint `3a74a35` MainActivity behavior with the retained
LAN TLS routing, no authentication controller and no HOME registration. Matching
version/signature allows `adb install -r` without relying on downgrade permission.
It has been built/verified, **not physically installed**; an install failure is a
stop condition, never a reason to uninstall/clear app data.

Reproduction: `python3 kiosk/lan-tls/build.py --auth-rollback`. The packager
`python3 deploy/reminders/prepare_device_activation.py` refuses to overwrite an
existing bundle. Keep its current manifest; rebuilding needs a new reviewed output.

## Approved activation session

The newer tested `activation_session.py` implements the controlled phases below.
Its native launcher is `python3 deploy/reminders/activate_native.py` from this repo
(or its absolute path from any native Terminal). It verifies the staged controller
before root execution, freezes the pinned bundle, creates a new private backup and
consistent SQLite snapshot, and waits for bounded actions. It preserves current
SQLite state on rollback. The session expires after two hours; `--resume` on the
launcher uses the original root-private checkpoint/backup after a fresh private
sudo authentication. A bridge-only expiry test has an independent recovery timer.
No enrollment occurs before physical fingerprint verification.

Twelve activation-controller fixture tests passed under Mint's runtime, including
the corrected readiness/rollback gates. The owner explicitly approved the dedicated
HTTPS restart and all controlled phases have passed. Refer to live results; do not
repeat completed deployment actions.

## Original read-only authorization procedure

No sudo is needed to finish this review. `sudo -n` currently requires a password.
After owner approval, run this exact command in a **new native macOS Terminal**.
It copies only the read-only helper to a root-owned location, verifies its pinned
checksum, and prints aggregate health/session metadata. It does not activate anything:

```sh
ssh -t pf1007l-mint 'sudo -v && sudo -n install -o root -g root -m 700 /home/hub/pf1007l-device-auth-review.yt5Otk/activation_preflight.py /root/pf1007l-auth-preflight-3467430d9f78.py && printf "%s  %s\n" 3467430d9f78bac2a4c3d3e6428d8a7f68eba2cfdd7769c88aea93668a26b14e /root/pf1007l-auth-preflight-3467430d9f78.py | sudo -n sha256sum -c - && sudo -n /opt/pf1007l-reminders-demo/venv/bin/python -I /root/pf1007l-auth-preflight-3467430d9f78.py'
```

`sudo -v` prompts for the Linux account password in Terminal with hidden input.
Never put it in chat or an argument. Cancellation/expiry means stop that privileged
phase and resume with a fresh TTY; no relaxed permissions or daemon changes.

The deployment itself is a separate reviewed privileged phase after this check.
Copy the whole reviewed bundle into a new root-private directory, pin-check the
manifest digest **after** the copy, then verify every file digest against that frozen
manifest. Do not execute unverified root code or imports from a hub-writable stage.
The current `integration_native.sh` only supports its old inspect/deploy/audit phases;
do not queue this activation through its legacy deployment action.

## Controlled deployment reference (completed; do not repeat without new scope)

1. Record actual services, frame IP, saved URL/theme, APK version/signature and
   current demo task IDs/completion states without exporting task contents. Confirm
   baseline working before starting. Abort on an unexpected baseline or permissions.
2. Create a new timestamped root-owned 0700 backup directory. Preserve the **current**
   bridge sources/unit/drop-ins, settings, proxy handler and complete demo UI. Make a
   consistent SQLite `Connection.backup()` snapshot (0600). Keep that snapshot on
   Linux; do not copy credentials/database into this repo. Back up introduced-file
   existence/absence too. Do not use the much older pre-demo proxy baseline.
3. Deploy compatibility phase with existing `legacy-demo` auth unchanged: install
   `device_auth.py` before `task_bridge.py`, keep public code/UI readable (0644/0755),
   install candidate bridge unit and new exact-route proxy handler/demo UI. Leave
   settings, proxy key, DAV account, Radicale/Serve, public proxy config and firewall
   unchanged. Verify unit syntax, daemon-reload, explicitly restart **only** the
   bridge and HTTPS proxy as needed. Check original HTTPS/weather and existing demo
   behavior before proceeding. `enable --now` does not reload an active bridge.
4. Install candidate from the Mac, without clearing data:

   ```sh
   adb -d install -r diagnostics/pf1007l/device-auth-activation/frame-auth-candidate.apk
   adb -d shell am start -n com.huntsyea.frame/.MainActivity
   ```

   Confirm current demo behavior and origin-aware feature support with native auth
   still off. Keep Rootless/default launcher and HomeHQ unchanged. Abort on errors.
5. Physically hold two fingers → Device enrollment (demo). Check displayed public
   SPKI/fingerprint and hardware flag. Copy **only public material** to the root-private
   review area on Linux. Enroll using the frozen `device_registry.py` tool with
   `enroll --registry /etc/pf1007l-reminders-bridge/device-registry.json
   --fingerprint VERIFIED_SHA256 --public-key-file ROOT_PRIVATE_PUBLIC_FILE`.
   Verify fingerprint again; never enroll the disposable probe's identity.
6. Install only `device-auth.conf` under the bridge unit's drop-in directory, keeping
   existing credential mounts. Atomically set `authMode=device-v1` in existing
   root-private settings; preserve every other setting, backend/identity key and
   task state. Verify the unit, daemon-reload and restart **only the bridge**.
   Physical menu → “Server enrolled; enable”. The legacy cookie must now be refused.
7. Stop on any failure and follow normal rollback below. No production list migration
   or personal reminders are part of this acceptance.

## Exact renewal/recovery acceptance

Keep the frame awake on Home, Tasks or Calendar (30-second task polling). Do not
change the Linux/Android clock or shorten the production session constant.

- **T0:** verify successful native proof; `/session` reports `mode=device-v1` and
  approximately 900 seconds remaining. Inspect only mode/expiry/CSRF-present boolean,
  never dump cookies, headers, proofs or CSRF. Record aggregate `latestIssuedUnix`
  from the read-only helper above. Check due/undated demo tasks and themes/weather.
- **T0 + about 5 min:** remaining lifetime falls; task reads still work.
- **T0 + about 12–13 min:** while polling remains active, verify a new aggregate
  session issuance timestamp and lifetime returning near 900 without reload, USB
  commands or password. Expect timing variation from polling/network delay. Observe
  at least two renewals (~26 minutes). Three retained sessions is the normal cap.
- **App restart:** close/relaunch only the kiosk, retaining app data; same public
  identity and automatic authenticated task recovery. Do not reboot either machine.
- **Expiry during outage (explicitly approved test phase):** stop only the demo
  bridge for at least 16 minutes. Leave Radicale, Tailscale, HTTPS/weather and Jellyfin
  running. Frame retains stale rows and blocks completion. Restart only the bridge;
  verify a fresh proof/session and authoritative refresh automatically, aiming for
  recovery within 90 seconds of healthy connectivity. No manual task replay.
- **Revocation:** registry tool `revoke` for the enrolled fingerprint, then restart
  only bridge. Existing session and renewal must fail; stale completion stays blocked.
  Re-enable through `rotate` only for this deliberate no-compromise test, then verify
  new proof and old-session rejection. Real compromise requires a new key/device.
- **Workflow/performance:** complete one newly named disposable reminder on frame,
  confirm same UID/due/completion on Radicale and iPhone; phone edit reflected back.
  Check original appearance, auto theme, weather, approximately 60 FPS and services.
  Disable temporary WebView debugging/remove USB forwards after measurement.

Software fixtures already cover replay, CSRF, wrong device/origin, conflicts and
ambiguous writes; no need to extract real cookies to repeat those attacks. Cellular,
recurrence, full Linux reboot and multi-day recovery remain separate acceptance.

## Normal acceptance rollback and incident response

For an ordinary candidate failure **without suspected compromise**:

1. Stop only the bridge during restoration; Radicale/iPhone syncing can continue.
2. Restore the immediately-before-activation settings, bridge code/unit/drop-ins,
   proxy handler and complete demo UI from the recorded backup. Remove only files
   introduced by this activation. Preserve the current frame-IP allowlist and all
   unrelated configuration. Restore modes/ownership; private settings stay 0600.
3. **Keep the current SQLite database and Radicale data.** Do not rewind tasks or
   operation history to the backup snapshot; new authentication tables can remain
   unused by old code. Database disaster recovery is a separate procedure.
4. Restore legacy auth deliberately, daemon-reload and restart only restored project
   units. Legacy bootstrap/session may have expired during testing: perform a separately
   reviewed local reprovisioning for the verified frame if needed, never broaden IP
   access or make an automatic fallback. Verify baseline task states before resuming.
5. Prefer physical “Rollback options” → disable native auth before restoring old app
   behavior. If the candidate app itself fails, install the prepared same-version
   rollback APK, preserving data:

   ```sh
   adb -d install -r diagnostics/pf1007l/device-auth-activation/frame-auth-rollback.apk
   adb -d shell am start -n com.huntsyea.frame/.MainActivity
   ```

   Never uninstall, clear app data, change launcher, or reset HomeHQ. Verify saved
   URL/theme, weather, tasks, all services and private Serve again.

Do **not** run `rollback_bridge.py` for this purpose: it disables the entire demo
and restores an older pre-demo baseline, rather than this checkpoint's working demo.

For loss/suspected compromise, do **not** downgrade to IP/legacy authentication.
Revoke and restart the bridge; if prompt revocation cannot be verified, stop only
the bridge to fail closed while the normal weather/dashboard and Radicale remain.
Remove/isolate the compromised frame from its network separately. Keep it revoked,
review demo changes and separately assess any other credentials/apps accessible on
that OS. No iPhone CalDAV password reset is necessary solely because a frame key was
lost; rotate other credentials if evidence shows they were exposed. Re-enroll a
clean device/new key, not the stolen key. No reset/reimage is performed automatically.
