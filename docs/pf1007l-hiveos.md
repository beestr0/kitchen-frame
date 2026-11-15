# HiveOS / black-screen recovery — November 14, 2026

## Confirmed cause and restored baseline

Wall-mounted device could launch Frame but only showed black. No ADB transport was
initially connected; wireless ADB was not listening. USB data access was supplied
without requesting a reboot. Do not enable unauthenticated network ADB as a shortcut.

- Correct installed package `com.huntsyea.frame`, versionCode5 / `1.4-auth-candidate`,
  UID10026; launcher `com.huntsyea.frame.MainActivity`. APK bytes exactly match the
  previously physically verified device-auth candidate. Saved URL remains
  `https://beestr0.duckdns.org:8789/__reminders-demo/`, native auth flag true.
- Signing certificate SHA256
  `fc10154a66d268e9ed36313866df7adc88ac07e3c90b59926f80e9d36bd88784` unchanged.
- Wi-Fi DHCP changed from **10.157.1.76 to10.157.1.146**. HTTPS allowlist, isolated
  firewall and bridge frameIP still required .76, dropping the new frame connection.
  App logged ERR_TIMED_OUT. This is not an expired enrollment or APK/backend mismatch.
- A reset clock was also observed before Wi-Fi time synchronization, then recovered
  automatically with auto_time enabled. TLS verification was never bypassed.
- Read-only PackageManager inspection resolves exactly one Frame-labeled launcher
  component, the package above. There are not two installed versions of this kiosk.
  Launcher cache likewise has one Frame component. Do not uninstall either icon.
  HomeHQ is separate `com.wesbos.homehq` v11/1.4.3, label Home HQ, unchanged. Separate
  auth probe v1 has no launcher entry and is not the production enrolled app.

Owner explicitly approved the exact-address repair and brief bridge/HTTPS restarts.
`deploy/hiveos/repair_network.py` atomically replaces only .76 with USB-verified .146
in the three project guards, never expands to a subnet, and preserves other private
settings/keys. Four focused tests passed. Private native sudo was used; no Apple
credentials entered. Original project files, isolated live nft table and consistent
SQLite snapshot are preserved under
`/var/backups/pf1007l-network/repair-20261115T003609Z-4c550191` (root-private).
No unrelated nft/Tailscale tables, HTTP fallback, Jellyfin, HomeHQ or app data changed.

Actual restored v5 frame: Calendar109 events/two calendars/fresh, Reminders10 records/
fresh, device-v1 session200, weather/Home visible. Unauthorized Calendar401,
query400,write405. Home dark/auto **59.9525FPS**,zero >50ms,maxgap33.249ms.
No calendar titles, private payloads or credentials returned by diagnostics. Debugging
off and USB forwarding removed afterward. No physical reboot was performed.

## Active HiveOS v6 — approved in-place installation

Native version6/`1.5-hiveos`, same package, signer and UID on upgrade:

- Lightweight native hexagon, “HiveOS”, “Your day, connected.” with clock-based
  light/dark styling. No bitmap/download/animation loop. A160ms fade occurs only
  when the dashboard DOM actually mounts; no deliberate startup hold.
- Wait/retry UI for Wi-Fi/reset clock, main-frame HTTP/SSL/load errors and missing
  JS render. TLS checks remain intact. Retry and Android Settings buttons plus
  the existing two-finger escape remain available.
- BOOT_COMPLETED receiver launches only this activity; generated manifest has **no
  HOME category**, so system/default launcher and protected components are unchanged.
  Wi-Fi/time initialization delays are handled in the app. Ordinary background
  data polls never show the splash.
- Existing device-auth controller, URL policy, KeyStore alias and settings preserved.
  No enrollment, cookie export, credential reset or Apple account change.

Builds use retained libraries only:

```sh
python3 kiosk/lan-tls/build.py --hiveos
python3 kiosk/lan-tls/build.py --hiveos-rollback
```

Verified artifacts (ignored, never Git):

| APK | SHA256 |
| --- | --- |
| kiosk/build-hiveos/hiveos.apk | 1829cb4ead395717276a973f7fbb9fad18f655eaa9bc339bab987b1a4826f6a9 |
| kiosk/build-hiveos-rollback/hiveos-rollback.apk | b4dd0f240cec828ea1ac3283d820a62bc2a23c246bd619e965eb8daef843e07a |

Both version6, original signer, no HOME intent. Rollback is pinned to94ccb0d native
behavior with existing LAN TLS/device auth, same version/signature, so no uninstall
or version downgrade is needed. Original installed v5 APK copy also retained privately.
Startup policy fixtures cover missing URL/offline/reset-clock/ready; existing native
URL policy21 cases passed. Both full APKs compile and signatures verify.

Owner approved installation and a brief kiosk-only restart. `adb install -r`
succeeded; installed version6/1.5-hiveos retains UID10026. The entire native settings
file hash is identical before and after installation and recovery testing: saved URL,
device-auth setting and existing key remain intact. No uninstall, data clearing,
re-enrollment, server restart or physical reboot was needed for the APK update.

Actual v6 frame: Calendar109 events/two selected calendars/fresh; Reminders10/fresh;
device-v1 session200; weather/Home visible, auto dark theme. Calendar unauthorized401,
query400/write405; no private calendar localStorage cache. Five-second frame sample
**60.1627FPS**, zero gaps over50ms, maximum16.622ms. Pre-install v5 also passed.

A USB-local WebView-only offline simulation displayed native HiveOS branding,
subtitle, generic error, Retry and Android Settings controls. Restoring connectivity
recovered the live dashboard automatically in **9.287 seconds**, without manual
reload. No network, TLS, task or calendar data was changed. Debugging was disabled
and temporary USB forwarding removed; the kiosk was left foreground.

BOOT_COMPLETED receiver registration and granted permission are verified; generated
APK has no HOME category. Synthetic broadcasts did not establish reliable foreground
autolaunch on this firmware. Actual boot behavior remains unverified until the
separately approved controlled power cycle; do not claim it passed or alter the
system launcher to bypass this gap. All seven checked Linux services remain active:
Calendar, Radicale demo, bridge, HTTP/HTTPS proxies, Jellyfin and Tailscale.

Rollback if a critical APK regression occurs (USB connected):

```sh
adb -d install -r kiosk/build-hiveos-rollback/hiveos-rollback.apk
adb -d shell 'am force-stop com.huntsyea.frame'
adb -d shell 'am start -n com.huntsyea.frame/.MainActivity --ez debug false'
```

This restores v5 native behavior at version6 with the same signer and application
data. It does not reverse the successful exact-IP server repair. Never uninstall or
clear data. Use the existing signed artifacts above; do not use `kiosk/build.sh`.

## Acceptance and remaining limits

Shortest physical check after update: open HiveOS, observe brief branding then live
Calendar/weather/tasks; confirm touch controls and two-finger Settings access. No
new reminder/Siri/calendar-edit round trip is needed for unchanged backend logic.
Boot receiver can be checked through a scoped simulated broadcast; a full physical
power cycle requires separate owner permission and is not claimed before performed.
Manufacturer “LOVE IS SHARING” splash, firmware and boot partitions remain untouched.

IP stability is separate: this repair deliberately retains exact-IP/network guards.
A router DHCP reservation for the verified frame is the practical durable option;
no router changes were authorized or made. A future address change still fails
closed and should show useful HiveOS retry/error UI rather than indefinite black.
Do not broaden LAN exposure or weaken device authentication to avoid this guard.


## DHCP reservation and one controlled power-cycle test

Recommended durable fix: reserve **10.157.1.146** for the frame's Wi-Fi MAC in the
router's DHCP/address reservation settings. Keep Android on DHCP. The verified MAC
and gateway are recorded only in ignored private
`diagnostics/pf1007l/hiveos/dhcp-reservation.json`; no router configuration was changed.
Do not select a static address inside an unreserved DHCP pool, expand the allowlist,
or change Tailscale rules. Router administration requires a separate authorized step.

After reservation and explicit approval for one power cycle:

1. Note the currently working screen and retain USB recovery access. Power down
   normally, remove all power including USB, then reconnect power once.
2. Observe manufacturer splash (unchanged), Android initialization, then whether
   HiveOS starts automatically. Allow Wi-Fi and network time to settle; never
   bypass TLS if the reset clock initially causes a connection failure.
3. In one acceptance batch confirm the address remains .146, branding transitions
   to live Calendar/Tasks/weather, touch controls and two-finger Settings work.
4. If autostart fails, manually launch HiveOS and record that specific boot gap.
   If the page fails, use Retry/Settings and USB diagnostics. Do not clear data,
   reset keys, repeat power cycles or change launcher/firmware without approval.

No physical power cycle has been performed in this update. Recurring Reminder
completion and production/personal Reminders migration remain outside this work.


## Supervised cold-boot result — failed, November 14, 2026

Owner confirmed router reservation for the previously observed Wi-Fi MAC at .146;
separate older .152 reservation was explicitly left untouched. One authorized cold
boot completed. Android booted, but HiveOS did not auto-launch. Manual launch showed
the generic reachability/retry error. No further reboot was performed.

USB diagnostics established two independent causes:

- Firmware presented a different wlan0 MAC after cold boot and received
  **10.157.1.25**, despite the reservation for the pre-boot MAC. Clock was correct,
  Wi-Fi enabled, installed v6 and enrolled application data intact. Exact-IP guards
  remained narrow; load failed with ERR_TIMED_OUT. A MAC-only reservation is not
  sufficient on this firmware. Do not repeatedly rewrite the server allowlist.
- Manufacturer BackgroundManagerService logged `prevent from boot complete
  broadcast: com.huntsyea.frame` and `package not in whitelist`. BOOT_COMPLETED
  permission remains granted; user background whitelist is empty. This is explicit
  vendor suppression, not evidence of lost APK registration.

Calendar, Radicale, bridge, HTTPS and Tailscale services checked active. No router,
launcher, firmware, server guard, app data or credentials changed during diagnosis.
Proposed next steps: supported Android Wi-Fi static IPv4 configuration using the
reserved .146 (after confirming router exclusion), and a supported vendor per-app
autostart/background permission if available. Neither is applied yet. Boot acceptance
and the final successful-setup checkpoint remain pending; do not report a pass.


## Bounded follow-up: stable manual use first

Android 6.0.1 installed Settings resources explicitly include Wi-Fi IP settings,
static/DHCP selection and IP/gateway/prefix/DNS validation. No per-network
randomized/device-MAC selector or vendor startup/allowlist UI was found in the
inspected Settings resources/activities. This is not a claim that undocumented
firmware controls cannot exist. No protected files or services were modified.

Recommended supported network fix: change only the existing Android Wi-Fi profile
to Static, IP10.157.1.146, gateway10.157.1.1, prefix24, DNS10.157.1.1. Owner has
reserved .146 at the router; keep it excluded from other DHCP allocation. Do not
forget the network or alter credentials. This avoids dependence on the changing
MAC and preserves exact-IP plus device-key authentication. Static settings should
persist as part of the saved network profile; survival of cold boot is still
unverified. Revert the profile to DHCP to undo it, with expected dashboard denial
if the assigned address differs. No static configuration was applied by Codex.

Read-only reflection of installed android.aw.BackgroundManager/IBackgroundManager
found managerPackage(String,long), allowBackgroundTask and internal lifecycle
methods, but no explicit public user-allowlist setter. None were invoked. Persistence
and security meaning of managerPackage are unknown; do not experiment with it,
edit vendor whitelists, disable BackgroundManagerService or change the launcher.
Android battery-optimization exemption has not been shown to override this vendor
boot block and is not presented as a fix.

Practical fallback: keep manual HiveOS launch after an outage, after fixing static
networking. Automatic launch remains an optional blocked requirement pending a
supported manufacturer control. No further reboot is needed to restore manual use.
Next user action is one saved Wi-Fi edit and manual launch; only after that succeeds
consider a separately agreed cold boot to validate network-profile persistence.


## Final end-of-day state — owner confirmed static Wi-Fi works

This section supersedes earlier pending static-configuration and launch-test steps.
Owner saved Static IP10.157.1.146, gateway10.157.1.1, prefix24, DNS10.157.1.1 on the
frame and confirmed HiveOS is connected and working. Existing router reservation,
older .152 reservation and server guards remain unchanged. Manual HiveOS launch
after a full reboot is the accepted workaround for manufacturer startup blocking;
autostart is currently unsupported. Static-profile persistence across another cold
boot is not yet verified; no additional reboot/test performed or required tonight.

End-of-day read-only check: Calendar, Radicale, bridge, HTTP/HTTPS proxies, Jellyfin
and Tailscale active and enabled; HTTPS health successful, upstreamErrors0. The
Linux/frame deployment has no MacBook/Codex/Terminal/USB runtime dependency. No
services restarted or other changes made. Development stopped; next-session summary
and exact resume command are in NEXT_SESSION.md. Personal data/migration scope and
all existing recovery safeguards remain unchanged.
