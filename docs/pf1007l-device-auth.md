# Renewable device authentication — candidate, not activated

The running demo remains checkpoint `3a74a35`, including its temporary cookie.
This session prepared a replacement; it did **not** enroll the kiosk, change live
credentials, install the candidate over the working app, or restart services.
Sudo was unavailable noninteractively, so privileged deployment was skipped.

## Protocol and security boundary

The Android app creates a P-256 key in its own Android Keystore namespace. Only its
public SPKI and SHA256 fingerprint appear in the physical enrollment dialog. An
administrator checks that fingerprint on the actual frame and adds the public key
to a private Linux registry. There is no remotely accessible enrollment endpoint.

The native controller obtains a 60-second nonce over validated HTTPS and signs a
fixed message containing protocol version, exact HTTPS origin, purpose, device ID,
challenge ID and nonce. It constructs this message itself, rather than signing
arbitrary JavaScript text. Linux verifies SHA256/ECDSA using installed OpenSSL,
consumes the challenge atomically, and issues a 15-minute session. Only the session
hash is stored in SQLite. The browser receives an HttpOnly/Secure/SameSite=Strict
cookie scoped to the demo path; JavaScript receives a per-session CSRF value,
relative expiry and fixed status messages, never a private key, proof or cookie.

The UI coalesces renewal, replaces near-expiry sessions, and recovers an expired
cookie through the native controller. Only a middleware authentication rejection
may retry a completion, once, with the identical operation ID/body. Timeouts and
conflict/server responses never silently replay writes. Native failures have a
bounded retry cooldown, using a monotonic browser clock when available. Wrong
origin, wrong frame, missing proxy backend credential,
unregistered/revoked key, expired nonce/session and proof replay are rejected.
Challenge creation and proof verification are rate limited; sessions per key are
bounded. Unknown authentication modes fail closed. Device mode accepts no legacy
cookie and never silently falls back to IP provisioning.

Protected mode uses an origin-aware AndroidX WebMessageListener for the main frame,
a literal `renew` command, exact-origin resource/navigation restrictions, no mixed
content/file/content access, and no embedded frames on the demo route. The native
transport keeps platform CA/hostname checks and the existing single-host CONNECT
route. There is no certificate exception or system-wide proxy/DNS change.

## Actual legacy-device findings

A separate disposable application UID (`com.huntsyea.frame.authprobe`) tested the
actual PF1007L, without replacing `com.huntsyea.frame` or using its cookies/keys.
Android is 6.0.1/API 23. Native ECDSA signatures verified both on Android and using
the Linux verifier, wrong audiences were rejected, the identity survived a second
app launch, and native HTTPS validated the real dashboard certificate. A further
separate-UID browser probe confirmed that native-set HttpOnly cookies exist but
remain hidden from JavaScript, the main-frame message/reply channel works, and the
channel is absent on a different origin. These used invented cookies/in-memory
pages, without authentication/task requests. WEB_MESSAGE_LISTENER is supported.
**Keystore reports `hardwareBacked=false`.** The key is accessed through an app-scoped signing
handle, but this is not hardware isolation or remote attestation. Root/OS compromise
can defeat this protection on the unsupported Android version. No claim of clone
resistance against a compromised OS is made. The owner must review this limitation
before enrolling the real kiosk. No provider password is needed on the frame.

The candidate APK is built and signature-verified using retained dependencies,
without downloads, into ignored `kiosk/build-auth-candidate/`. Its native-auth flag
is off by default and can only be changed in the physical escape menu. It has **not**
been installed over the working app. Full native proof → cookie → renewal behavior
still needs controlled acceptance on that app; unit tests alone do not prove it.

## Reproducible checks

```sh
# Mac: no credential inspection or live task writes
python3 -m unittest discover -s deploy/reminders -p test_device_auth.py -v
python3 -m unittest discover -s deploy/reminders -p test_device_registry.py -v
(cd dashboard && npm test)
node --test scripts/reminders-demo-proxy.test.mjs
python3 kiosk/lan-tls/build.py --auth-candidate
/opt/homebrew/opt/openjdk@17/bin/javac -d kiosk/build-auth-tests kiosk/src/com/huntsyea/frame/DevicePolicy.java kiosk/tests/DevicePolicyTest.java
/opt/homebrew/opt/openjdk@17/bin/java -cp kiosk/build-auth-tests com.huntsyea.frame.DevicePolicyTest
```

Bridge/HTTP/recovery fixtures need the existing vobject/dateutil runtime on Mint.
An isolated source-only stage was created at
`/home/hub/pf1007l-autonomous-tests.xc2ZzG`; it is not a service or credential store:

```sh
ssh -o BatchMode=yes pf1007l-mint \
  'cd /home/hub/pf1007l-autonomous-tests.xc2ZzG && /opt/pf1007l-reminders-demo/venv/bin/python -m unittest discover -v'
```

Tests generate invented keys in private temporary directories and delete them
normally. They use ephemeral loopback HTTP listeners and fake DAV resources, not
real phone tasks. The stage contains no production settings, password or database.
The separate probe is left installed but stopped. It can be rebuilt with `python3 kiosk/auth-probe/build.py`; optional
`--webview` reuses the already-built candidate's AndroidX code, still under the probe
UID. Do not install `frame-auth-candidate.apk` as an incidental test step.

## Next controlled deployment and acceptance

1. Read this document and review the software-backed key limitation with the owner.
   Recover a new scoped native sudo session only when the owner is present. Do not
   rerun Radicale installation, account discovery or change the iPhone account.
2. Build both UI variants and candidate APK from the verified commit. Review SHA256
   manifests. Back up the **current** bridge sources/unit, proxy source/handler,
   demo assets, root-private settings and a consistent SQLite backup before changes;
   keep backups owner-private on Linux. Do not export credentials to this repo.
3. First deploy backward-compatible bridge/UI/proxy changes in `legacy-demo` mode.
   Include `device_auth.py` before `task_bridge.py`. The existing deployment helper
   refuses device-mode activation; include every dependency in its reviewed manifest.
   An already-active bridge must be explicitly restarted after source replacement;
   `enable --now` alone is not a reload. Restart only project units as reviewed.
   Verify existing phone/frame behavior and FPS before proceeding.
4. Install the candidate using the retained original signing identity **only during
   that acceptance window**, without clearing app data. The candidate must confirm
   WEB_MESSAGE_LISTENER support; no JavaScript-interface authentication fallback is
   provided. Keep original APK and server rollback artifacts available.
5. Use the two-finger escape menu → Device enrollment (demo). Verify the public
   fingerprint on the frame. Save only its public SPKI (base64) to a private file on
   Linux. With a root-private directory/file, use the reviewed offline tool:

   ```sh
   python3 /reviewed-stage/device_registry.py enroll \
     --registry /etc/pf1007l-reminders-bridge/device-registry.json \
     --fingerprint PHYSICALLY_VERIFIED_SHA256 \
     --public-key-file /root/private-review/frame-public-spki.txt
   ```

   This edits public authorization state only. It does not enable live auth or
   install anything. The tool checks fingerprint/duplicates, writes atomically with
   fsync and mode 0600, and refuses symlinks/broad permissions. Do not use the probe
   identity; it belongs to a different UID and was never enrolled.
6. Prepare an explicit systemd drop-in for **only** the bridge:

   ```ini
   [Service]
   LoadCredential=device-registry:/etc/pf1007l-reminders-bridge/device-registry.json
   ```

   Keep existing demo-account and bridge-settings mounts. Atomically change only
   `authMode` to `device-v1` in existing private settings; preserve `apiKey`, `csrf`,
   `frameIP`, all task data and operation history. Registry/settings stay root:root
   0600, parent 0700. Keep the separate public proxy config readable by DynamicUser.
   Verify the unit and restart only the bridge to load the credential snapshot.
   Do not rotate `apiKey` here; opaque task IDs currently derive from it. A later
   backend-key rotation must first retain its previous value as private `identityKey`.
7. Physically choose “Server enrolled; enable”. Verify fresh cold startup, normal
   valid session, expiry and proactive renewal, app restart, bridge restart,
   revocation/rotation, unauthorized-device denial and original weather/themes/FPS.
   Include an outage spanning expiry, returned connectivity, and server clock sync.
   The physical “Rollback options” entry never changes server authorization.
8. To revoke, run the registry tool's `revoke` action with the same registry and
   fingerprint, then restart only the bridge: LoadCredential is a startup snapshot,
   **editing the file alone does not apply revocation**. Verify denial. `rotate`
   increments the epoch and re-enables the same public key; old sessions/proofs remain
   invalid. A compromised key needs revocation and a newly generated replacement,
   not merely epoch rotation. No HTTP admin route exists.
9. Roll back with the recorded **current** artifacts/settings and bridge-only unit
   state, restoring legacy mode and removing the device-registry drop-in. Retain
   SQLite task/operation data. Use the physical rollback option or original APK
   without clearing app data. A consumed/expired legacy bootstrap needs reviewed
   local reprovisioning; do not make an automatic security fallback.

Do not activate production synchronization or migrate personal lists during this
acceptance. Cellular fetch behavior, real recurring occurrence semantics, multi-day
soak, full reboot recovery and backup restore remain separate gates.
