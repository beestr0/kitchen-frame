# Private Apple Calendar — implemented candidate, account authorization pending

November 14, 2026. **No Apple account accessed, credential collected, calendar
selected, service installed, or physical frame changed.** The existing dashboard,
Reminders/Siri/auth/weather/HTTPS deployment remains active. This is the primary
feature; no further Reminders investigation or soak is a prerequisite.

## Implemented

- Linux-only CalDAV reader uses PROPFIND metadata discovery and REPORT on explicitly
  selected VEVENT collections. HTTPS certificate/hostname validation remains on;
  unapproved hosts/redirects, write methods and incomplete multistatus fail closed.
- Per-calendar SQLite last-good normalized cache, 31-day past/180-day future window,
  five-minute upstream refresh, bounded exponential retry and authorization latch.
  Failed calendars retain stale events; successful empty calendars clear old events.
  Removed selections are purged locally, never deleted on Apple. Restart restores
  cache; changed endpoint binding cannot expose the previous selection's cache.
- Existing `ical.js` parser reused on Linux for all-day exclusive dates, timezone/
  floating times, recurring appointments, exceptions and cancellations. Private
  wrapper bounds resources/output and rejects unsupported dense recurrence rules
  instead of silently dropping events. No recurrence parsing on Android.
- Only title/start/end/all-day/opaque UID/calendar identity/name/color are published.
  Notes, location, attendees, raw ICS, account/DAV URLs and secrets are excluded.
- New GET `/__reminders-demo/calendar` reuses persistent device authentication and
  renewal. Legacy-cookie clients cannot read it. Proxy is HTTPS-only, fixed local
  backend, no query/DAV passthrough. HTTP/cloud paths do not deliver private events.
- Home/Month/Week and new Day view share the real calendar source plus reminder due
  markers. Calendar names/colors survive beyond the old four-color palette;
  reminder circles/“Due” remain distinct. Fictional appointments disappear when
  the private source is configured, including cold failures (not replaced by fake
  appointments). Loading/error/stale states, update age, legends and unavailable
  date-window notices are implemented. Private events stay in frame memory, not
  localStorage. Unchanged event arrays preserve the day index.
- Separate collector unit, systemd credential mounts and bridge drop-in prepared.
  Apple password is held only by collector; bridge receives a separate local key.
  No APK change, public listener, new package download or Mac runtime dependency.

## Verification

- 72 dashboard/normalizer/projection/parser/auth regression tests passed.
- 20 private CalDAV/collector/selection/native-launcher tests passed.
- 6 HTTPS relay tests passed, including calendar fixed-GET/read-only forwarding.
- 13 relevant Mint bridge tests passed (new device-auth calendar boundary, relay
  denial/failure checks and existing bridge/recurrence preservation regressions).
- Candidate UI build passed (132.25 kB JS, gzip45.55 kB). This is build evidence,
  not a new physical FPS measurement; prior ~60 FPS baseline remains unchanged.
- Full assembled Python → existing Linux Node → parser → recurring JSON pipeline
  passed with three invented events and **zero Apple requests**. Eighteen frozen
  files checksum-verified. First candidate assumed `/usr/bin/node`; isolated test
  caught that absence. Corrected candidate reuses `/opt/pf1007l-proxy/node/bin/node`.
  No failure was bypassed; no live service was touched.

Frozen local candidate (ignored): `diagnostics/pf1007l/calendar-candidate-v3`.
Server review stage: `/home/hub/pf1007l-calendar-candidate-v3-review` (not a service).
Manifest SHA256:
`b392c9f1babe4028ac7dd3a6ecca60693bc79a64f801d8f8dfc1b699b830c1ef`.
Original failed candidate is retained separately; do not deploy v1.

## Essential account choice — owner approval required before proceeding

**Preferred least privilege:** a separate Apple Account used only as a calendar
reader. Privately invite that account to each calendar you own and want displayed,
turn **Allow Editing off**, and accept the invitations as the reader on iCloud.com.
Keep Public Calendar off. The reader needs iCloud Calendar and two-factor
security/app-specific-password eligibility. Other owners must grant the reader
access to calendars you cannot share yourself; do not assume every delegated or
non-iCloud calendar is available. No phone primary-account change is needed.
[Apple private sharing](https://support.apple.com/en-gb/guide/icloud/mm6b1a9479/icloud)

**Simpler alternative:** your existing Apple Account with a newly generated dedicated
app-specific password. Our collector is read-only and selects calendars, but the
credential itself is **not calendar-scoped or read-only**. Compromise could reach
other account data/services it authorizes, including write access beyond this code.
The isolated reader limits this risk better. Neither approach sends the Apple
credential to Android, browser, Cloudflare, Git or logs.

The rooted/software-Keystore frame can expose displayed private events to someone
with physical/root access. Device authentication controls remote clients, not that
physical access. Minimal private event data is retained on Linux; no claim of disk
or hardware-backed protection is made. Confirm this scope before real display.

### Exact owner setup, after choosing/authorizing the method

1. For the reader method, complete private view-only invitations and acceptance.
   Use your existing account instead only if you explicitly accept broader scope.
2. In a private browser session for the **chosen account**, open
   [account.apple.com](https://account.apple.com/) → **Sign-In and Security →
   App-Specific Passwords → Generate**; label it `PF1007L Calendar`. Two-factor
   authentication is required. Do not send the password, primary password or 2FA
   codes in chat. [Apple instructions](https://support.apple.com/en-us/102654)
3. After authorization, use a new native Terminal and run:

   ```sh
   python3 /Users/beestrother/Projects/kitchen-frame/deploy/icloud-calendar/start_authorization.py
   ```

   It uses `pf1007l-mint`, verifies/copies the three pinned helper files to a
   root-private directory before executing, and privately prompts for Linux sudo
   and the chosen account email/app password. No tee/recording/history export.
4. Metadata-only discovery lists calendar names/colors **only in that Terminal**.
   Choose numbers separated by commas, then type `SELECT` to save selected scope.
   The helper refuses credential/config overwrite, does not fetch events or start
   services. Return only completion status/counts to chat, not names/IDs/secrets.
5. Only after approved selected-event access: verify fresh private backup, deploy
   candidate, first read-only fetch and source activation as below. No public feed
   or primary-password fallback if discovery/authentication fails.

## Controlled deployment sequence after account/scope approval

1. Freeze verified v3 under a root-private artifact directory; verify manifest digest
   and every file after copy. Back up current bridge/proxy handler/UI/unit drop-ins
   and make a consistent SQLite backup. Retain all existing Reminders history.
2. Install collector source tree at `/opt/pf1007l-calendar` matching frozen relative
   paths, including only the existing ical.js runtime files; source/dirs 0644/0755.
   Credentials/config/local bridge-key stay root0600 under `/etc/pf1007l-calendar`
   (0700), and collector state uses DynamicUser StateDirectory0700/UMask0077.
3. Install `pf1007l-calendar.service` without replacing unrelated units. Verify unit
   and runtime paths and unused loopback5241. Start the calendar service only after
   selected-event authorization. Verify authenticated loopback snapshot has an
   update timestamp, all selected calendars loaded, bounded count, correct source;
   print counts/states only. No raw event/account contents in tooling outputs.
4. Install bridge candidate and `bridge-calendar.conf` drop-in, retaining settings,
   device registry and all existing credential mounts. Restart **bridge only**;
   check existing session/auth data and task health. It now reads fixed loopback5241
   with the dedicated calendar key; Apple credentials never enter the bridge.
5. Install candidate HTTPS handler and perform only its necessary proxy restart
   with bounded readiness polling. Confirm original dashboard/weather/task health,
   credential-free calendar denial and HTTP demo isolation before UI activation.
6. Atomically overlay frozen demo UI, index last, preserving old assets/backup.
   Reload only kiosk page (no reinstall/data clearing). Calendar endpoint is GET-only
   and device-authenticated. Enable collector service for boot after healthy first
   fetch; automatic collection then runs without Mac/USB/native Terminal.
7. Complete the consolidated physical checklist. No new auth-lifetime wait, cellular
   retest, unrelated-service restart or Linux reboot is needed for this feature.

Rollback: stop/disable only new calendar service; restore backed-up bridge/proxy
handler/UI and remove only introduced calendar drop-in/unit. Restart only affected
bridge/HTTPS services with readiness checks. Keep current task SQLite/Radicale data;
never overwrite completion history with backup. No credential revocation, private
cache deletion or personal-account sharing changes occur automatically. Root-private
calendar state can remain inactive for diagnosis until owner decides retention.

## One short physical acceptance session after live deployment

1. Owner creates one uniquely named non-sensitive test event **in Apple Calendar**,
   today, in selected calendar A; waits for automatic refresh. Verify Home/Day/Week/
   Month (select today), identity/color and absence of fictional appointments.
2. Owner moves/renames that same event and cancels it afterward; verify update then
   disappearance, no duplicate. Assistant/collector never writes Apple events.
3. Owner adds an all-day or recurring synthetic appointment in selected calendar B
   if available. Verify calendar identity/color and next occurrence/date; existing
   due reminders remain distinguishable and frame appearance/weather unchanged.
4. End Mac observation/turn Mac off and verify a later phone change still arrives
   through the Linux collector. Record this once; no prolonged soak is required.

Actual Apple compatibility, live display, physical performance and these acceptance
criteria remain unverified until account authorization and deployment. They are not
claimed complete by offline fixture success. Dense secondly/minutely/hourly event
rules and extremely large collections fail closed with last-good/stale state; expand
support only if actual selected-calendar data demonstrates a need.
