# Permanent PF1007L HTTPS kiosk

Completed November 14, 2026 UTC after explicit owner approval.

## Result

The separate `com.huntsyea.frame` kiosk now saves
**https://beestr0.duckdns.org:8789/**, without the diagnostics query string.
Only its URL preference changed; other saved preference entries were compared
and remain identical. HomeHQ, the default launcher, trusted certificates, Android
DNS/Wi-Fi settings and boot behavior were not changed. The HTTPS Home screen is
left visible in demonstration mode. Debugging and all ADB forward/reverse mappings
are removed. The Mac/local development server is unnecessary for runtime.

Two successful cold starts loaded HTTPS from the saved configuration without an
intent URL or USB dashboard forwarding. Home, Calendar, Tasks, Focus and Settings
touch navigation passed. Same-origin demo API returned 200 and the authenticated
cloud WebSocket diagnostic returned `pong` without live/private messages.
Three captured document responses were 200, `securityState=secure`, TLS 1.3,
subject `beestr0.duckdns.org`, issuer `ZeroSSL RSA DV SSL CA 2`, and remote
`10.157.1.115`. Normal chain and hostname validation remain enabled.

## Recovery correction and test boundary

A stronger offline/reload test reproduced a native retry bug: the WebView error
page briefly retained the previous title, so `onPageFinished` cancelled the retry.
The kiosk now tracks main-frame load failures and cannot treat an error-page
completion as successful. SSL failures still call `sslHandler.cancel()` and retry;
no trust bypass was introduced. The same-signature test APK was rebuilt, verified
and updated in place without uninstalling or clearing data.

After the correction, a ten-second app-scoped connection interruption and failed
full reload recovered automatically: native retry fired at ten seconds and the
verified page loaded about 0.7 seconds later. A further cold start passed. The
complete initial failure output and successful repeat are retained in ignored
`diagnostics/pf1007l/https-permanent/`.

This test simulated connectivity loss through the test WebView's debugging API;
it did **not** turn the Wi-Fi radio off, disconnect the access point or renew DHCP.
Physical radio/AP reassociation remains untested. No claim is made that a new DHCP
address will pass the firewall: the frame must retain its allowed `10.157.1.247`
address. The application retries temporary load failures; infrastructure changes
need a separate scoped review. Prior physical HTTPS tests measured 59–60 FPS;
this promotion focused on saved-URL, restart and failure recovery.

## Artifact and private backups

- Installed APK: `kiosk/build-lan-tls/frame-test-lan-tls.apk`.
- Package/version: `com.huntsyea.frame`, versionCode 4, versionName `1.3-lan-tls`.
- APK SHA-256: `b311109a40d1d26f03273fbcdbed66877b4d504d37010a5968f4f90eaa181448`.
- Signer SHA-256: `fc10154a66d268e9ed36313866df7adc88ac07e3c90b59926f80e9d36bd88784`.
- Pre-promotion preferences: ignored `backups/pf1007l-desk/https-permanent/kiosk-before.xml`.
- Prior routing APK: ignored `backups/pf1007l-desk/https-permanent/routing-before-recovery-fix.apk`.
- Original pre-routing APK/preferences: ignored `backups/pf1007l-desk/https-kiosk-update/`.

Backup directories are mode 0700 and their files 0600. No secrets were printed,
committed, moved into browser storage or supplied to integrations.

## HTTP fallback and rollback — run only when needed

The original Linux HTTP service on **8788** remains active and demo-only. To save
it as the kiosk's fallback instead of HTTPS:

```sh
adb -d shell am start -n com.huntsyea.frame/.MainActivity -d 'http://10.157.1.115:8788/'
```

This deliberately changes only the kiosk URL. To restore the original pre-promotion
USB configuration, read its URL locally from the protected preferences backup and
use the same `am start ... -d` form; do not overwrite the whole preference file or
clear data. The old USB URL additionally requires the previous Mac development
server and `adb reverse tcp:5173 tcp:5173`; those are not required by Linux HTTP or
HTTPS. Future temporary debugging mappings can be removed with
`adb -d forward --remove tcp:9223` and the old USB dashboard mapping with
`adb -d reverse --remove tcp:5173` if present.

To return to HomeHQ without changing defaults:

```sh
adb -d shell am start -n com.wesbos.homehq/.MainActivity
```

If an APK rollback is necessary, `adb -d install -r` the backed-up same-signature
APK, never uninstall. Retaining the recovery fix is preferable to reverting it.
Changing the APK alone does not restore the old URL. Linux HTTPS rollback and
certificate renewal/monitoring details remain in
[the HTTPS installation report](pf1007l-https-installation.md); keep HTTP services
and all unrelated firewall tables untouched.

## Next approval

Review [the personal integration proposal](pf1007l-personal-integrations-plan.md).
Weather, Calendar and Todoist code exists but is not enabled. Spotify and Bambu
need new isolated modules and eligibility/security checks. No automatic launch
at device boot or default-launcher change was enabled by this promotion.
