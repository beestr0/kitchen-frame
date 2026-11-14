# PF1007L local compatibility assessment

Read-only USB inspection on 2026-11-13, against local merged commit `af28130`.
No applications, Android settings, firmware, launcher defaults or Cloudflare resources were changed.

## Observed device

| Item | Result |
| --- | --- |
| Reported identity | AEEZO / YHK, board `exdroid`, hardware `sun8i` |
| CPU / GPU | ARMv7, four CPU indices (0–3), Mali-400 MP / OpenGL ES 2.0 |
| Android | 6.0.1, API 23, security patch 2016-07-05 |
| RAM | 1,026,980 kB total (about 0.98 GiB) |
| Data storage | 12.3 GB total, 11.8 GB free at inspection |
| Display | 1280×800 landscape, 160 dpi, approximately 60 Hz |
| Installed WebView | `com.android.webview`, 106.0.5249.126, `/system/app/webview` |
| Clock | Correct local date/time at inspection; America/Indiana/Indianapolis |
| RTC | `/dev/rtc0` exists; power-loss time retention untested |
| Foreground app | Rootless Launcher (`amirz.rootless.nexuslauncher`) |
| Installed kiosk | Home HQ (`com.wesbos.homehq`), 1.4.3, version code 11 |

The sun8i/Mali-400 hardware is consistent with the expected Allwinner family; the
exact A33 silicon designation was not independently established. Android 6 supplied
no useful `dumpsys webviewupdate` output; this inspection verifies the installed
system WebView package, not the engine of a running HomeHQ page.

## Compatibility and validation

The device meets the source-defined baseline: kiosk minimum API 23, dashboard JS
target Chrome 106, CSS target Chrome 61, and a fixed 1280-pixel viewport matching
the panel. The repository kiosk contains Java code without a native ABI dependency.
No hardware or engine upgrade is indicated by these checks.

Six local focus/theme unit tests passed. Dashboard dependencies are absent locally;
a production build and the browser suite were not run. Android rendering, actual
CSS viewport/DPR, keyboard resizing, touch accuracy, GPU performance, HTTPS trust,
offline recovery and sustained operation remain unverified. The old security patch
and WebView limit make a trusted, narrowly scoped dashboard appropriate; they do
not justify changing the working OS during this assessment.

The diagnostic initially failed under macOS Bash's empty-array handling with
`set -u` (`args[@]: unbound variable`). It completed successfully when rerun with
the detected device selected through `ANDROID_SERIAL`. No script change was made.

## Preserve the existing setup

HomeHQ is distinct from repository kiosk `com.huntsyea.frame`, which is not installed.
Its APK contains a bundled site. Do not replace it with the repository APK or assume
that changing its URL is harmless to its existing configuration.

The installed APK was copied read-only to
`/private/tmp/pf1007l-homehq-1.4.3.apk`. This is temporary storage, not a durable backup.

- APK SHA-256: `2a69199b5ea3eb1c4a0fe2c6b400bc74beb8473e432530f872da66d2ce8c35ea`
- APK signature verification passed.
- Signing certificate SHA-256: `fc10154a66d268e9ed36313866df7adc88ac07e3c90b59926f80e9d36bd88784`
- Installed private data directory: `/data/user/0/com.wesbos.homehq`.
- Package permits Android backup (`ALLOW_BACKUP`), but is not debuggable; `run-as`
  cannot read its private files. No private data was extracted.

Before touching HomeHQ, preserve its configuration through an app-provided export
if available. Android 6 ADB backup is a possible fallback, requiring on-frame consent
and verification of the resulting archive. The backup flag alone does not prove
that every preference, WebView database or external integration will be recoverable.
Neither export nor Android backup was initiated. Keep any eventual backup encrypted
and outside version control. Do not uninstall, clear data, or bypass a signing mismatch.
Launcher preferences, Etar and ICSdroid should also remain untouched.

## Proposed installation and physical test — approval required

1. Prepare dashboard dependencies and run the full tests and production build locally.
   Use a local Worker with invented integration data and no production secrets; do
   not deploy. Build the kiosk with the available Android SDK, verify its signature
   and retain the signing key for future upgrades. The build script can create a
   debug keystore, so inspect key availability before running it.
2. Before installation, reconfirm `com.huntsyea.frame` is absent and review the exact
   APK and test URL. Install that separate package only after explicit approval.
   Leave HomeHQ and the current launcher/default Home selection intact. Launch the
   test activity explicitly; do not set it as Home or disable any package.
3. For a USB-local test, request approval for a temporary ADB reverse mapping to the
   local server. Bind the server to loopback, load only the trusted local dashboard,
   and use demo data before any task mutations. Cleartext local transport, if used,
   does not establish production HTTPS compatibility. Do not put a production key
   into a command, log or screenshot. No ADB mapping has been created yet.
4. On the frame, test Home, Calendar, Tasks and Focus; demo task add/complete/retry;
   week/month navigation; Settings scrolling and keyboard; light/dark/automatic
   themes; focus pause/resume/reload; and local data persistence. Use `?diag` to
   record viewport, heap, DOM count and frame timing, then observe extended use.
   Separately test an authorized HTTPS origin and network recovery. Sleep, reboot,
   power-loss and network-setting changes require agreement before executing them.
5. Confirm the two-finger escape menu and return to the existing launcher/HomeHQ.
   If testing fails, stop using the new kiosk and resume the old app; its package
   and data remain intact. Remove any temporary USB mapping afterward with approval.
   Uninstalling the test package or changing the default launcher requires separate
   explicit approval. Promote the new kiosk to daily use only after successful
   physical testing and an agreed rollback path.

The next safe step is local build preparation, followed by approval of a separate
test-kiosk installation. There is no demonstrated need to modify HomeHQ, WebView,
firmware, density, timezone, package enablement or launcher defaults.

## Local build preparation completed — 2026-11-13

Installed dashboard dependencies using `npm ci --no-audit --no-fund` and the existing
unchanged lockfile. The sandboxed attempt failed with registry DNS `ENOTFOUND`; the
authorized network-enabled retry succeeded (77 packages). npm 11 reported unapproved
install scripts for esbuild, fsevents and workerd; no broad script approval was made.
The build and static browser tests nevertheless succeeded. The local Worker runtime
was not started, so its runtime availability is not established by this test.

- Environment: Node 26.13.1, npm 11.20.0, existing Homebrew JDK 17.0.21,
  Android build-tools 34.0.0 and android-34 platform. No additional JDK/SDK install needed.
- `npm test`: **31 passed, zero failures**. The logged calendar HTTP 503 is an
  intentional failure-retention test.
- `npm run build`: **passed**, producing `dashboard/dist/client/` and
  `dashboard/dist/photo_frame_dashboard/`. Reran with
  `WRANGLER_LOG_PATH=/private/tmp/pf1007l-build.log WRANGLER_SEND_METRICS=false`
  to avoid a sandbox-denied preferences log write. Svelte's default-config notices
  are informational. No deployment ran.
- Optional `scripts/desk-smoke.mjs`: **passed**, using installed desktop Chrome,
  Playwright installed separately in `/private/tmp/pf1007l-browser-tools`, and built
  assets served only on Mac loopback. Touch navigation, calendar, task add/complete
  and failure retry, focus persistence, settings and solar transitions passed with
  no page errors. APIs were mocked/invented; this does not prove live integrations
  or Android WebView behavior. The temporary HTTP server was stopped.

### Prepared APK

The standard APK built successfully. For the first physical test, the final artifact
is **`kiosk/build/frame-test.apk`**, approximately 16 KiB. Added opt-in
`KIOSK_LAUNCHER_ONLY=1` support to `kiosk/build.sh`, removing only the HOME category
from a generated manifest. Default builds retain their previous behavior. The build
directory is recreated by the script, so a later build replaces these artifacts.

| Property | Verified result |
| --- | --- |
| Package | `com.huntsyea.frame` |
| Version | 1.3, code 4 |
| Minimum / target API | 23 / 27 |
| Entry activity | `com.huntsyea.frame/.MainActivity` |
| Test manifest | LAUNCHER present, HOME absent |
| Permissions | INTERNET, ACCESS_NETWORK_STATE |
| Native libraries | None; DEX compiled with minimum API 23 |
| Signing | Existing `~/.android/debug.keystore`, alias `androiddebugkey`, RSA 2048 |
| Certificate SHA-256 | `fc10154a66d268e9ed36313866df7adc88ac07e3c90b59926f80e9d36bd88784` |
| APK SHA-256 | `688b94df2742f5feeee8da5cbc424c5fe01776e88abf4a2d4b5cc009af0777f8` |
| Verification | API-23 signature verification passed; v1/v2/v3 signatures; ZIP alignment passed |

The signing certificate matches the saved HomeHQ APK, but the package names differ
and there is no shared-user declaration. Installing this artifact creates a separate
application rather than replacing HomeHQ. The API-23 signature and manifest checks
are static verification, not an actual installation test.

Source review found no confirmed Android 6 blocker. API-23 error callbacks, DOM
storage, JavaScript and hardware acceleration are enabled; SSL failures are cancelled
and retried rather than bypassed. The URL is saved in this kiosk's private preferences.
This APK is a WebView wrapper and does not bundle the customized dashboard: its URL
must reach a server. Back is deliberately ignored and the escape menu offers reload
and Android settings, not a launcher button; keep USB ADB available for return.
The fixed viewport, `adjustPan` keyboard behavior, brightness bridge, error-recovery
heuristic and limited Mali-400 performance require physical validation. Only trusted
content should be loaded because the wrapper exposes its brightness bridge and permits
mixed content. Source comments about a missing RTC describe the other frame, not a
measurement of this unit.

### Exact proposed first test (not executed; owner approval required)

Use the launcher-only artifact above, without rebuilding it, after rechecking its hash.
Select the known frame explicitly if more than one USB Android device is attached.
The following uses `adb -d` only when this frame is the sole USB target.

1. Read-only preflight: `adb -d shell pm path com.huntsyea.frame`. Stop if the package
   exists and inspect its version/signature/data before considering any update.
   Reconfirm HomeHQ and Rootless Launcher are present.
2. Start a local, integration-free production-asset server from the repository root:
   `python3 -m http.server 5173 --bind 127.0.0.1 --directory dashboard/dist/client`.
   This initial test intentionally has no Worker credentials or live API backend.
3. Install once, **without replacement flags**:
   `adb -d install kiosk/build/frame-test.apk`.
4. Create temporary USB forwarding: `adb -d reverse tcp:5173 tcp:5173`.
5. Launch only the test activity:
   `adb -d shell am start -n com.huntsyea.frame/.MainActivity -d 'http://127.0.0.1:5173/?diag'`.
6. In the new app, choose Settings → Demo mode → On before task testing. Exercise
   the four views, settings and keyboard; record `?diag` results. Weather/solar data
   and API errors are expected to be unavailable on this static server. A later local
   Worker/fixture test is needed for those features and HTTPS needs a separate test.
7. Return through ADB to the existing launcher:
   `adb -d shell am start -n amirz.rootless.nexuslauncher/com.google.android.apps.nexuslauncher.NexusLauncherActivity`.
   If needed, stop only the test app with `adb -d shell am force-stop com.huntsyea.frame`.
8. Remove forwarding with `adb -d reverse --remove tcp:5173` and stop the Mac server.
   Leave the test package installed until removal is explicitly approved.

No install, launch, reverse mapping, reboot, package disablement, settings change,
default-launcher change or Cloudflare deployment was performed during preparation.

## Physical USB test completed — 2026-11-13

Following explicit owner approval, the prepared APK hash and API-23 signature were
reverified. `com.huntsyea.frame` was absent; HomeHQ and Rootless Launcher were present.
Installed `kiosk/build/frame-test.apk` without replacement flags: **Success**.
The launcher-only manifest has no HOME category. No existing app was replaced.

The production assets were served on Mac loopback port 5173 and reached through
`adb -d reverse tcp:5173 tcp:5173`. No Worker, credentials or Cloudflare deployment
were involved. Enabled the test app's demo mode and set its idle clock to Never so
Home remains available for inspection. Only the test app's own preferences changed.

### Results

| Check | Result |
| --- | --- |
| Actual renderer | Android WebView Chrome 106.0.5249.126 |
| CSS viewport | 1280×800, DPR 1; no horizontal page overflow |
| Home | Invented calendar and six demo tasks rendered correctly |
| Calendar | Week/month layouts, next month and return to Today passed |
| Tasks | Added and completed a uniquely named invented task; six original demo tasks retained |
| Native keyboard | Appeared; input and Add controls remained visible above keyboard; text entry/submission worked |
| Focus | Countdown advanced, pause held, paused 24:57 survived page reload; reset to 25 minutes afterward |
| Settings | Native modal rendered; demo, idle preference and theme controls responded |
| Themes | Light and dark Home and Settings rendered; dark preference survived reload |
| Reload persistence | Demo mode, dark theme and paused focus retained |
| Errors | No captured test-app crash; two startup EGL errors, detailed below |

Controls were exercised with injected Android input and DevTools touch events on
the real device. This validates those input paths and actual WebView rendering;
physical finger accuracy, subjective touch feel and keyboard typing still benefit
from the owner's inspection. No sleep, reboot, power interruption or long-duration
soak test was performed. HTTPS, live weather, solar transitions from a real feed,
integration failures and live provider operations were outside this static-server test.

### Performance and rendering observations

After allowing each view to settle, six-second requestAnimationFrame samples were:

| View | Frames/second | Gaps over 50 ms | Maximum gap |
| --- | ---: | ---: | ---: |
| Home | 59.5 | 1 | 66.5 ms |
| Calendar (week) | 59.8 | 0 | 33.2 ms |
| Tasks | 60.0 | 0 | 29.8 ms |
| Focus (paused) | 59.3 | 0 | 33.8 ms |

These are short rendering-loop samples with diagnostics and debugging active, not
proof that every display frame presents or that transitions stay at 60 fps. Overlay
snapshots during interaction dropped as low as 19–36 fps and accumulated long frames;
brief transition jank is present. Screenshots of Home, month/week calendar, Tasks,
Focus and Settings showed no obvious clipping or missing styles. The native keyboard
covers the lower task list while the input/Add row remains accessible, consistent
with the kiosk's `adjustPan` configuration.

Android `dumpsys meminfo` reported 70,434 kB total PSS during testing and 69,063 kB
at the end (about 69 and 67 MiB). DevTools JS heap was approximately 2.6–2.7 MiB
in settled samples. The overlay's coarsely reported 10 MB heap should not be treated
as the precise measurement. No swap was attributed to the app in those snapshots.

The test process logged two startup errors:
`eglChooseConfig failed with error EGL_BAD_ATTRIBUTE`, followed by `loaded Frame`.
Rendering subsequently succeeded; these remain GPU compatibility warnings to watch
during extended use. No further test-process errors or crashes appeared in the
captured selected-tag log. Static `/api/*` HTTP 404s and unsuccessful message WebSocket
connections are expected without a backend; weather displays “isn’t set up yet.”

Local screenshots, raw memory snapshots and performance samples are retained in the
gitignored `diagnostics/pf1007l/` directory. Playwright could not attach to this older
WebView's browser context API, so testing used the page's direct DevTools protocol
connection. This was a tooling limitation, not a dashboard failure.

### State left for owner inspection

Per the latest instruction, the test app remains foreground on **Home, light theme,
demo mode On, idle clock Never**, with its diagnostic overlay visible and timer reset.
The Mac loopback HTTP server and USB reverse mapping remain active deliberately.
Keep the Mac awake and USB connected; disconnecting USB, stopping the server or
restarting the Mac can prevent reloads and asset requests. This is a tethered test,
not a standalone or persistent production setup.

Temporary WebView debugging was disabled by a normal launch, its debugging socket
was confirmed closed, and the port-9223 debugging forward was removed. HomeHQ 1.4.3
and Rootless Launcher 3.9.1 retain their previous package update times and remain
installed. No HomeHQ settings or data were accessed or changed, and no launcher
default, Android setting, WebView package or firmware was altered.

To return directly to the existing HomeHQ app without changing launcher defaults:

```sh
adb -d shell am start -n com.wesbos.homehq/.MainActivity
```

Alternatively return to Rootless Launcher and open Home HQ there:

```sh
adb -d shell am start -n amirz.rootless.nexuslauncher/com.google.android.apps.nexuslauncher.NexusLauncherActivity
```

After inspection, remove only this test's USB mapping with:

```sh
adb -d reverse --remove tcp:5173
```

Then stop the Mac server. If necessary, stop only the test app with
`adb -d shell am force-stop com.huntsyea.frame`. No uninstall is needed to use
HomeHQ. These fallback/cleanup commands are documented, not executed at completion,
so the dashboard stays available as requested.
