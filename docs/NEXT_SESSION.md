# PF1007L — next session

Checkpoint: November 13 evening / November 14, 2026 UTC.
Branch: `feat/pf1007l-https-weather-handoff`. No PR or merge requested.

## Completed

- Separate kiosk `com.huntsyea.frame`; HomeHQ and Rootless/default launcher preserved.
- Isolated Cloudflare Pages/private Worker/KV deployment; unrelated resources untouched.
- Permanent Linux HTTPS, compatible ZeroSSL chain, automatic renewal/monitoring.
- Single-host app-only routing fixes home gateway private-DNS filtering while retaining
  normal TLS/SNI/hostname validation. No router/system DNS or trusted-root changes.
- Saved kiosk URL: **https://beestr0.duckdns.org:8789/**. Cold starts/recovery passed;
  fixed native error-page title handling so failed loads keep retrying.
- Live Indianapolis weather: Fahrenheit, `America/Indiana/Indianapolis`, current
  conditions/high-low/four-day forecast, backend KV cache and weather-only 15-minute
  cron. Last-good forecast and Outdated indicator tested. Physical samples 59–60 FPS.
- Private CalDAV investigation and inactive read-only preparation; **no Apple account
  accessed, no Apple credentials collected, no private calendar syncing activated**.

## Current state / safe shutdown

- Mint server: `hub@10.157.1.115` over SSH; frame allowlisted at `10.157.1.247`.
- Linux HTTP 8788 remains demo-only fallback; HTTPS 8789 allows only live weather.
  CONNECT 8790 is restricted to the single HTTPS hostname/port and allowed frame.
- Final frame check: Home visible, automatic themes, secure HTTPS, fresh live weather,
  five forecast days, calendar/tasks demo, no browser backend key or USB forwarding.
  Temporary app debugging and the performance overlay are off.
- Proxy services/guards active; HTTPS and renewal/monitor timers enabled. Jellyfin
  and Tailscale active and preserved. NordVPN was absent/inactive at prior assessment;
  it was not installed, enabled or modified. Storage mounts unchanged.
- Certificate: ZeroSSL RSA DV SSL CA 2 → Sectigo R46 cross-sign → USERTrust RSA;
  expires **2027-02-12 23:59:59 UTC**. Normal reload/renewal check and crash recovery passed.
- Renewal checks: 03:00/15:00 server-local plus up to 30-minute jitter; monitor ~5 min.
  Local alerts only; no external renewal notification delivery configured.
- No Android boot auto-launch/default-launcher change. Closing Codex, unplugging USB
  and turning off the Mac do not stop the Linux dashboard or weather.

Read-only health checks for tomorrow (execute via the existing SSH connection):

```sh
systemctl is-active pf1007l-proxy.service pf1007l-proxy-https.service jellyfin tailscaled
systemctl list-timers --all pf1007l-cert-renew.timer pf1007l-tls-monitor.timer
curl --fail --silent --resolve beestr0.duckdns.org:8789:10.157.1.115 https://beestr0.duckdns.org:8789/__proxy_health
```

## Known limits

- Frame DHCP address changes fail closed; no router reservation was added.
- App-scoped connection loss and restart recovery passed; actual Wi-Fi radio/AP
  reassociation and a full Linux reboot were not performed.
- Legacy Android/WebView remains unsupported despite working HTTPS. Initial assets
  require Cloudflare/internet; this is not a fully offline asset mirror.
- Stronger kiosk authorization/navigation/bridge controls need review before private
  events. IP allowlisting alone is not cryptographic device authentication.
- App-specific Apple passwords are not read-only/per-calendar scopes; a privately
  invited view-only reader account is the stronger optional boundary.
- APK rebuilding uses the Mac’s retained SDK/JDK, original signing key and ignored
  Maven/R8 cache; these private/local artifacts are intentionally not in Git.
- Existing frontend demo toggle is global, and calendar colors repeat after four;
  calendar-only activation and stable selected-calendar colors must be implemented.
- Cloudflare aggregate billing visibility remains incomplete; no paid upgrade or
  new subscription was enabled. See the cost assessment.

## Exact next steps — require owner approval before account access

1. Stay on this branch; inspect `git status`/latest commit. Read
   [private iCloud proposal](pf1007l-private-icloud-plan.md) and
   [integration plan](pf1007l-personal-integrations-plan.md). Recheck runtime health.
2. Ask owner to approve Linux-local private CalDAV and choose primary-account app
   password versus a separate privately invited view-only reader account. Do not
   enable Public Calendar or use the main Apple password/browser-session scraping.
3. After approval, owner generates a dedicated `PF1007L Calendar` app-specific
   password in Apple's browser account settings (2FA required). Open secure native
   SSH/sudo Terminal entry on Linux; stage/review the prepared credential helper.
   Credentials stay root-private on Linux, never chat/args/logs/frontend/Cloudflare.
4. With separate discovery authorization, list calendar names/IDs/colors only in
   the secure Terminal. Owner selects collections; do not fetch events yet by default.
5. Complete the isolated collector, recurrence/DST parser fixture validation,
   atomic per-calendar snapshots, stale/partial-failure handling and local delivery.
   Resolve kiosk authorization and frame cache/privacy requirements first.
6. After selected scope and activation approval, enable only the HTTPS calendar
   route and calendar-specific UI state/timer. Keep HTTP synthetic, weather live,
   tasks/other integrations disabled. No private event data in Cloudflare KV.
7. Test Home/Week/Month, colors, outages, restart, timezone, HTTPS and 59–60 FPS;
   redact personal event screenshots/logs. Then propose Todoist, followed by Spotify
   Now Playing and Bambu A1 Mini monitoring as separately approved stages.

## Validation, source control and recovery

Final local checks: **43 dashboard + 48 proxy/TLS + 10 inactive CalDAV tests passed**;
production build passed. Credential scan applies to the exact staged repository
snapshot: **zero credential findings**. Private backups/diagnostics, credentials, APKs and downloaded tooling stay
ignored. Test evidence is local under ignored `diagnostics/pf1007l/session-close/`.

- [Permanent URL / APK and HTTP fallback rollback](pf1007l-permanent-https.md)
- [HTTPS services, certificate and monitoring](pf1007l-https-installation.md)
- [Live weather configuration / rollback](pf1007l-weather.md)
- [Cost assessment / unverified billing](pf1007l-https-costs.md)

Do not reinstall/recreate working components. Existing APK/preferences backups
remain private under ignored `backups/pf1007l-desk/`. Immediate HTTP fallback is
`http://10.157.1.115:8788/`; saving it intentionally changes only the kiosk URL.
HomeHQ remains available explicitly via
`adb -d shell am start -n com.wesbos.homehq/.MainActivity`. Do not clear data,
uninstall apps, change launchers, flush firewalls or modify unrelated services.
