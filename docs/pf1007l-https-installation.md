# PF1007L HTTPS installation results

**Current update:** the owner subsequently approved saving the HTTPS URL. Promotion, restart and corrected automatic-recovery tests passed; see [permanent HTTPS results](pf1007l-permanent-https.md). Earlier unchanged-URL statements below describe the pre-promotion test.

## Current verified state — 2026-11-14 UTC

The secure Terminal session resumed the queued installation automatically after
sudo authentication. Its blank line was not an idle credential prompt: Certbot
was processing issuance. No credentials needed to be entered again.

- HTTPS listener: `https://beestr0.duckdns.org:8789/` on Linux `10.157.1.115`.
- HTTP demo fallback remains `http://10.157.1.115:8788/`.
- Certificate: CN `beestr0.duckdns.org`, issuer `ZeroSSL RSA DV SSL CA 2`.
- Validity: November 14, 2026 00:00:00 UTC to February 12, 2027 23:59:59 UTC.
- SHA-256 fingerprint: `77:E8:90:DF:25:27:2E:CB:69:E5:6A:00:03:68:4B:C5:30:05:F1:2A:38:35:61:39:F4:AB:A9:FA:8D:50:37:7A`.
- Activation validates hostname, dates, key pairing and chain against the copied
  physical frame CA roots before serving. This is not yet a physical WebView test.
- Isolated HTTPS service crash test passed: PID changed, systemd restart count
  increased from 0 to 1, validated health returned in 7.69 seconds.
- Installation and crash-test checks confirmed the HTTP fallback, unrelated
  service state and protected baseline were unchanged.
- Certificate activation hot reload passed without changing the process PID.
  Normal renewal checking passed; no forced certificate reissuance was performed.
- Monitoring passed its healthy-state and controlled-failure checks; no external
  notifications were sent or configured.
- All 48 focused local tests passed with loopback access. The first sandboxed
  attempt could not bind test sockets; its complete failure output was retained
  separately from the successful run in the ignored diagnostics directory.
- Initial HTTPS process RSS was approximately 64.5 MiB; this is an idle reading,
  not yet frame workload performance.

## Physical acceptance — passed

The owner approved the routing APK update. Installed only `com.huntsyea.frame`
version `1.3-lan-tls`, retaining versionCode 4, UID 10026 and the original signing
certificate. The original APK and preferences remain in the ignored private
`backups/pf1007l-desk/https-kiosk-update/` directory. Final preference bytes match
that backup exactly; the saved URL was never changed.

The gateway filters the hostname's private A response. AndroidX WebKit's
per-application reverse-bypass proxy override sends only HTTPS for
`beestr0.duckdns.org` to `10.157.1.115:8790`. CONNECT permits only that hostname on
8789, then tunnels encrypted bytes to the isolated TLS listener. WebView retains
the original hostname for SNI and normal hostname/chain verification. Other
hostnames bypass this proxy; no Android/router resolver or CA settings changed.

Three document loads returned 200 with WebView `securityState=secure`, TLS 1.3,
subject `beestr0.duckdns.org`, issuer `ZeroSSL RSA DV SSL CA 2` and remote address
`10.157.1.115`. The served chain is leaf → ZeroSSL RSA DV SSL CA 2 → Sectigo
Public Server Authentication Root R46 cross-signed by USERTrust RSA Certification
Authority. The installed kiosk retained `sslHandler.cancel()`; no certificate
bypass was added. Updated-kiosk logs contained zero SSL errors or fatal exceptions.

All Home, Calendar (week/month/next/today), invented task creation/completion,
Focus timer start/pause, Settings, Automatic/Light/Dark selections passed.
Same-origin demo APIs returned 200 without a frontend access key. WSS upgraded to
the private backend with server-side authentication and returned only a sanitized
heartbeat `pong`; personal/live messages are filtered from this diagnostic.
USB reverse 5173 was removed for full reload, API and real proxy interruption
recovery. These succeeded over Wi-Fi. It was restored afterward solely to retain
the earlier fallback; no USB transport serves this HTTPS dashboard.
App-scoped offline/online recovery passed without changing device networking.
Expected errors during deliberate interruption/offline and aborted navigation
were recorded; no persistent rendering error was found.

| View | Five-second animation sample |
| --- | ---: |
| Home | 59.35 FPS |
| Calendar week | 59.79 FPS |
| Tasks | 59.92 FPS |
| Focus paused | 60.15 FPS |

A further settled 15-second Home sample measured **60.08 FPS**, zero frames over
50 ms and a 33.25 ms maximum gap. One long frame occurred in the first Home
sample. Brief transition/screenshot counters are not steady-state measurements.
Touch events were dispatched to actual controls, not substituted DOM click calls.
The test app used 78,447 KiB PSS (~76.6 MiB). Linux Node RSS after testing was
approximately 69.5 MiB; CPU averaged ~0.67% of one core across the measured test
interval including waits. These are short-run observations, not a long soak test.

The HTTPS Home screen is left visible in Light theme with demonstration data.
Debugging and its temporary ADB forward were removed. HomeHQ remains available.

## Startup, renewal and monitoring

After physical success, enabled the isolated HTTPS service and firewall guard,
`pf1007l-cert-renew.timer` and `pf1007l-tls-monitor.timer`. The original HTTP
service and guard remain enabled. Renewal checks run at 03:00 and 15:00 server
local time plus up to 30 minutes jitter, with persistent catch-up. Certbot decides
when renewal is due; this test performed a normal no-op renewal check, not forced
reissuance or a future CA renewal guarantee. Activation validates new material,
atomically switches bundles, hot-reloads without restart and rolls back on failure.
Monitoring runs about every five minutes, alerts within 21 days of expiry and
flags renewal checks older than 36 hours. Bounded recovery affects only this
HTTPS service. Durable alerts are root-private and in the journal; **external
notification delivery is not configured**.

The isolated nft table `inet pf1007l_proxy_tls` permits ports 8789/8790 only from
frame `10.157.1.247` on the Ethernet interface and local health probes, dropping
other traffic to those ports. Application checks further restrict host/origin/IP
and CONNECT destination. A frame DHCP address change will fail closed and require
a scoped configuration update; no router reservation was changed. There is no
public forwarding. HTTPS may survive an internet outage while cached, but fresh
Cloudflare assets require upstream availability; no full offline asset mirror is
implemented. DNS-01 and renewal use validated outbound HTTPS/DoH without changing
system DNS. No automatic HTTP downgrade occurs.

Useful server commands (read-only unless labeled):

```sh
systemctl status pf1007l-proxy-https.service pf1007l-proxy-https-firewall.service
systemctl list-timers --all pf1007l-cert-renew.timer pf1007l-tls-monitor.timer
journalctl -u pf1007l-proxy-https.service -u pf1007l-cert-renew.service -u pf1007l-tls-monitor.service --since today
sudo python3 /opt/pf1007l-tls/monitor.py
```

Final audit found no health issues, with Jellyfin and Tailscale still running
under their original PIDs, the original HTTP PID/source/config unchanged and
`/mnt/media` still mounted. NordVPN was not active in the earlier assessment;
this work did not install, enable or modify it. No reboot was performed: startup
unit configuration and restart recovery were verified without interrupting the
server's other services.

## Secrets and preservation

DuckDNS and corrected ZeroSSL EAB configuration are preserved root-private under
`/etc/pf1007l-tls/`; certificate client state is private under
`/var/lib/pf1007l-acme/`. No credential values belong in this report or Git.
Only the dedicated DuckDNS hostname was updated; no Cloudflare resources,
Jellyfin, Tailscale, NordVPN, mounts or Android system settings were changed.

## Recovery and next steps

Use the existing HTTP fallback if needed. Stop only the new
HTTPS service to withdraw the proof; do not stop the original HTTP service or
change its firewall. Preserve certificate state to avoid unnecessary reissuance.
See the TLS README for scoped service management and rollback, and
[the cost assessment](pf1007l-https-costs.md) for remaining billing uncertainty.


To roll back only the APK, reinstall the backed-up same-signature/versionCode APK
with `adb -d install -r backups/pf1007l-desk/https-kiosk-update/original-frame.apk`.
Do not uninstall or clear data. This removes the app-only route while preserving
saved configuration. Relaunch without a data URI to use its unchanged saved URL;
the old Mac USB fallback additionally needs its previous local server/forwarding.
Temporary Linux HTTP navigation can be performed through app debugging without
saving a new URL. To return to HomeHQ explicitly:
`adb -d shell am start -n com.wesbos.homehq/.MainActivity`.

Server rollback (only if requested): stop/disable `pf1007l-tls-monitor.timer` and
`pf1007l-cert-renew.timer`, then stop/disable `pf1007l-proxy-https.service` before
`pf1007l-proxy-https-firewall.service`. Preserve private certificate state; leave
HTTP units and all unrelated firewall tables untouched. Never flush global rules.

Remaining: owner approval before persisting the HTTPS URL; optional external
renewal alerts; longer-term soak monitoring; billing visibility noted in the cost
assessment. Personal integrations remain disabled. Review authorization and keep
HTTP strictly demo-only before introducing personal data. IP restrictions are not
a replacement for application authentication on an untrusted LAN; legacy Android
and WebView remain unsupported software despite valid transport encryption.
