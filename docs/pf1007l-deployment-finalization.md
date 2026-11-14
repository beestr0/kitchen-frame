# PF1007L deployment finalization

Reviewed 2026-11-13. This review made no server configuration, Cloudflare, Android settings,
application installation, launcher, routing or firewall changes. Only local
reports and a read-only backup of the separate kiosk's preferences were saved.
No personal integrations were configured.

## Verified current state

| Check | Result |
| --- | --- |
| Linux proxy | `pf1007l-proxy.service`: enabled, active/running, success |
| Firewall guard | `pf1007l-proxy-firewall.service`: enabled, active/exited, success; expected oneshot behavior |
| Automatic restart configuration | `Restart=on-failure`, five-second delay; 20 starts per five minutes |
| Crash recovery | Verified: PID 475683 → 475842, NRestarts 0 → 1, healthy after 8.75 seconds |
| Dependency | Proxy requires and starts after the dedicated guard |
| Listener | Only `10.157.1.115:8788`, no wildcard/IPv6 listener |
| Application health | Responding; demo-only APIs; zero upstream errors in the current process |
| Non-allowlisted Mac | TCP connection times out; firewall restriction still effective |
| Allowed frame | Wi-Fi address remains `10.157.1.247` |
| Memory | About 68 MiB process RSS / 21 MiB charged cgroup memory at this review; different accounting |
| Prior physical measurements | 58–60 FPS; about 0.45% of one CPU core during active testing |
| Jellyfin / Tailscale | Active; original PIDs 459473 / 468133 unchanged |
| Storage | `/mnt/media` still mounted as ext4 |
| Saved native kiosk URL | Still the previous USB fallback; backed up privately and verified |

The controlled **stop/start** and app-scoped offline recovery previously passed.
The actual crash-recovery test also completed successfully: the journal records
SIGKILL at 19:50:12 on 2026-11-13, automatic restart at 19:50:17, and the new
listener at 19:50:20. The checker measured 8.75 seconds to healthy recovery and
verified unchanged Jellyfin/Tailscale PIDs, media mount and existing IPv4/IPv6
filter rules. The guard stayed active. A later read-only check confirmed the new
process remains running and both units remain enabled. No rerun or installer was
needed. Reboot recovery remains untested. Explicit `systemctl stop` intentionally
does not trigger restart.
See [systemd restart semantics](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html).

Private current evidence: `diagnostics/pf1007l/finalization/` (ignored), in addition
to the original physical acceptance results under `diagnostics/pf1007l/mint-install/`.

## Remaining stability gaps

1. **Boot and long-duration proof.** Boot enablement is verified; actual Linux/frame
   reboots, power loss and a multi-day soak are not. Do not reboot Jellyfin as part
   of routine dashboard checks. Save the URL before scheduling a separate frame
   cold-start test. Saving a URL does not make this app the default launcher or
   cause it to open automatically after boot.
2. **Address continuity.** Server Ethernet is configured statically. The frame's
   current address is the sole allowed dashboard client. A DHCP change will deny
   access safely. Confirm a frame DHCP reservation separately; do not broaden the
   allowlist or alter router/network settings silently.
3. **Restart exhaustion and hangs.** Repeated bind/start failures can exhaust the
   20-per-five-minute limit. Systemd does not automatically try again solely because
   that interval expired. A running but hung process also is not detected by the
   restart policy: there is no watchdog/health timer. A future project-specific
   monitor could check both health and the guard, record bounded failures and
   restart only these units with backoff. This needs an explicitly reviewed change.
   [systemd rate limits](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html)
4. **Guard monitoring.** `active (exited)` records successful rule installation;
   it does not continuously verify that the nft table still exists. Application
   IP/Host/Origin restrictions are independent defenses. No global firewall reset
   or network-manager restart should be used to repair this project.
5. **Cloudflare/DNS dependence.** The Mac is absent from the active request path,
   but HTML/assets still come through Cloudflare. Document failures show a 10-second
   retry page; the proxy bounds upstream requests and validates TLS. A loaded demo
   can continue locally, but a cold load is not fully offline-capable.
6. **Partial boot errors.** `dashboard/index.html` retries an incomplete boot only
   while `window.__failed` is false. A script/resource error sets that flag and can
   leave the error screen until reload. The kiosk's title-based `loadedOnce` check
   is not an application health signal. A future fix should distinguish transient
   asset failures (bounded retries) from persistent code errors, with regression
   tests. No production code or Cloudflare deployment changed during this review.
7. **Maintenance and privacy.** The isolated Node runtime needs planned security
   updates; automatic global package upgrades are not a solution for this service.
   Android 6/WebView 106 remain old software even after transport encryption.
   Before an eventual HTTPS mode, review the kiosk's existing permissive mixed-
   content setting and restrict navigation/JavaScript bridge exposure to the trusted
   dashboard. Keep live APIs/writes/WebSockets blocked in the current HTTP mode.

Completed crash-test evidence is saved privately as
`diagnostics/pf1007l/finalization/recovery-verification.json`; service logs corroborate
its result. The checker only killed the dedicated proxy's main process; systemd
performed recovery without a manual start. There is no pending authentication or
need to repeat this successful test.

## Procedure to persist the LAN URL — prepared, not executed

Scope is only `com.huntsyea.frame`; HomeHQ (`com.wesbos.homehq`) and Rootless
Launcher stay untouched. No APK replacement, launcher selection, package disabling,
preferences overwrite or data clearing is required.

1. Recheck service/guard health and current frame address; leave demo-only mode
   enforced. Confirm the Linux page still works on Wi-Fi and the Mac fallback is
   available before making the one preference change.
2. A read-only snapshot of this kiosk's `shared_prefs/kiosk.xml` has already been
   saved under ignored `backups/pf1007l-desk/kiosk-finalization-20261113/` with a
   0700 directory and 0600 files, plus a hash manifest. The existing ADB daemon
   already runs as root; no privilege or Android settings change was made.
   `run-as` is unavailable because this is a release app; Android backup is disabled
   in its manifest. Do not enable backup, make it debuggable, or root anything.
   The snapshot confirms the previous URL is `http://127.0.0.1:5173/?diag`.
3. After approval to persist the address, launch only the test kiosk explicitly:

   ```sh
   adb -d shell am start -n com.huntsyea.frame/.MainActivity \
     -d 'http://10.157.1.115:8788/' --ez debug false
   ```

   `MainActivity.handleIntent()` saves only the `url` preference for this change.
   Never append an access key. Removing `?diag` hides diagnostics without changing
   the origin: the Linux-origin demo settings, theme and local invented data remain.
   The USB origin's separate browser storage also remains intact.
4. Verify the saved preference by a private read, then Home/Calendar/Tasks/Focus/
   Settings, both themes and demo state. Confirm the frontend contains no key.
5. Prove persistence with an approved cold launch of **only** this app (force-stop
   and start with a fresh MAIN/LAUNCHER intent carrying **no data URL**). It must
   read the saved LAN URL rather than reuse the prior in-memory page. Do not reboot
   the frame or change the default launcher to accomplish this.
6. Temporarily remove only the original `tcp:5173` reverse mapping and reload the
   dashboard to reconfirm Wi-Fi. Restore it afterward for fallback. Disable remote
   debugging/remove any test DevTools forward, then leave Home/light theme visible.

Rollback the URL through the same supported intent path, not by copying XML over
live preferences:

```sh
adb -d reverse tcp:5173 tcp:5173
adb -d shell am start -n com.huntsyea.frame/.MainActivity \
  -d 'http://127.0.0.1:5173/?diag' --ez debug false
```

The Mac's original local dashboard must be running for that fallback. Alternatively
return to HomeHQ with its previously verified component:

```sh
adb -d shell am start -n com.wesbos.homehq/.MainActivity
```

No `pm clear`, uninstall, preference deletion, whole-app restore or launcher change.
The previous configuration remains preserved by not clearing either origin's data.

## Encryption options

All options must preserve upstream HTTPS validation and server-side cloud secrets.
Cost estimates exclude existing hardware/electricity and are not purchase approval.
None of these encrypted alternatives was deployed or proven end-to-end this review.

| Option | Privacy and validation | Expected cost | Reliability / complexity | Assessment |
| --- | --- | --- | --- | --- |
| Current frame-restricted LAN HTTP | No LAN confidentiality/integrity; source IP is not cryptographic identity. Wi-Fi encryption does not authenticate this HTTP server. | No new fees | Lowest complexity; already tested | Keep for demo only. A compromised LAN peer/ARP interception can read or alter the dashboard and exercise allowed proxy capabilities without the cloud key. |
| LAN HTTPS with compatible public CA and DNS hostname | Full hostname, expiry and chain verification in existing WebView; no new Android trust anchors | Potentially zero using free DNS and free Google Public CA; paid owned domain optional, not authorized | Moderate: hostname, DNS-01 issuance, renewal, local resolution, full-chain selection, renewal monitoring | Preferred investigation because the kiosk can stay unchanged. Compatibility of the actual issued chain must be proven, including after renewal. |
| LAN OpenVPN tunnel with current Android-6-compatible client | Encrypt/authenticate frame-to-server traffic; VPN CA held only in its profile, no Android system CA install. HTTP remains inside tunnel. | Community software has no subscription requirement; local resources only | Higher: new frame app/VPN consent, private client identity, dedicated server instance/interface and narrow rules, boot/reconnect/fail-closed testing | Plausible no-domain alternative; current OpenVPN for Android source declares minSdk 23. Must verify the chosen signed release/ABI on this frame before promising support. |
| App-specific native TLS gateway | Native client can validate an app-bundled CA, hostname, expiry and chain, exposing only loopback content to WebView | No required hosting/domain fee; substantial development/maintenance | Highest: revised APK, HTTP/API/WS gateway, redirect/Origin rules, local authorization, rotation and negative security tests | Possible engineering fallback, not a simple WebView trust-config switch. Needs separate design review. |
| Existing Tailscale / current WireGuard Android apps | Server-only overlay does not encrypt the frame's Wi-Fi leg | Existing account may have no new fee, but compatibility is blocking | Current Tailscale requires Android 8; current WireGuard Android source minSdk 24 (Android 7) | Not a direct supported solution on this Android 6 frame. Do not sideload obsolete versions. |

### Preferred HTTPS investigation: free DNS + compatible CA

DuckDNS offers free subdomains and TXT updates. Google Public CA documents free
certificate requests and ACME/DNS validation with external account binding to a
Google Cloud project. Combining those is a **candidate design**, not evidence that
an unregistered name is available, current provider CAA permits issuance, or that
an issued Google chain will anchor in this frame's actual store.

Proposed changes, only after approval:

- Reserve a neutral free DNS hostname (no identifying household/calendar names),
  authenticate through the provider/browser, and protect its DNS token server-side.
- Create/select an appropriately scoped Google Cloud project, enable only Public
  CA, generate EAB securely, and use an ACME client with DNS-01 validation. Confirm
  the account needs no paid services/billing change before proceeding. Never paste
  tokens in chat, logs, shell history or a public frontend.
- Keep the service LAN-only: DNS-01 requires public TXT visibility, **not** public
  port 80/443 or router forwarding. Resolve the chosen DNS hostname to the private
  server address through an approved local DNS arrangement (or a provider-supported
  private A record, after checking router DNS-rebinding protection). Do not disable
  rebinding protection globally.
- Add a separate LAN TLS listener, e.g. 8789 after collision checks, and its own
  frame-only firewall rules. Preserve HTTP 8788 unchanged during proof. Adapt exact
  Host/Origin/CSP/redirect/ws-to-wss handling and backend forwarding; simply putting
  a generic TLS terminator in front of this exact-authority proxy is insufficient.
- Serve leaf plus the correct intermediates/cross-signs. Test against copied frame
  roots with hostname verification, then in the actual kiosk without keys or SSL
  overrides. The prior `https://pki.goog/` control succeeded through GlobalSign;
  that does not guarantee every GTS-issued chain will work.
- Automate renewal and atomic reload, alert before expiry, and revalidate renewed
  chains. A public certificate may reveal the hostname in Certificate Transparency;
  it does not expose the dashboard or personal data by itself. Clock synchronization
  after frame power loss remains necessary for certificate date validation.

No Cloudflare DNS/certificate/Worker change is needed for this LAN TLS design.
The existing Cloudflare deployment and upstream validated HTTPS remain intact.

Sources: [DuckDNS API/TXT support](https://www.duckdns.org/spec.jsp),
[Google Public CA pricing and setup](https://docs.cloud.google.com/certificate-manager/docs/public-ca-tutorial).

### Alternatives and limits

A public certificate for `10.157.1.115` is not a practical route: it is a reserved
private address, not a globally unique public endpoint. Let's Encrypt now supports
short-lived public IP certificates, but its documented Android baseline is 7.1.1;
that does not solve this frame's missing ISRG roots. Tailscale HTTPS also uses
Let's Encrypt. A default Caddy/Certbot setup is therefore not a verified fix.
[Let's Encrypt compatibility](https://letsencrypt.org/docs/certificate-compatibility/),
[IP certificates](https://letsencrypt.org/2026/01/15/6day-and-ip-general-availability),
[Tailscale HTTPS](https://tailscale.com/docs/how-to/set-up-https-certificates).

For OpenVPN, use a dedicated LAN-bound instance with unique keys/certificates and
only a route to the dashboard; no default route, DNS takeover, NAT, public exposure
or changes to existing NordVPN/Tailscale instances. Validate the server CA, server
purpose and exact identity (`remote-cert-tls server`, `verify-x509-name`), with a
separate client certificate. Permit only the assigned tunnel client to the proxy;
remove direct HTTP access before personal data. Prove tunnel-loss behavior cannot
fall back to unencrypted LAN HTTP. Android VPN consent and startup/reconnection
are new device changes requiring approval; confirm no existing frame VPN conflict.
[OpenVPN client minSdk](https://github.com/schwabe/ics-openvpn/blob/master/main/build.gradle.kts),
[OpenVPN verification](https://openvpn.net/community-docs/community-articles/openvpn-2-6-manual/).

App-private trust is different from adding a CA to Android's system/user store.
However, Android's declarative Network Security Config arrived in Android 7/API24;
adding its XML alone will not fix this API23 WebView. A native, fully validating
connection/gateway would be new engineering, including correct hostname checking,
key rotation, and protection of loopback endpoints from other apps. Never use
`SslErrorHandler.proceed()`, a trust-all manager, or certificate-failure fallback.
[Android 7 security configuration](https://developer.android.com/about/versions/nougat/android-7.0#network_security_config),
[Android TLS guidance](https://developer.android.com/privacy-and-security/security-ssl).

Current overlay compatibility sources:
[Tailscale Android requirements](https://tailscale.com/docs/install/android),
[WireGuard Android minSdk](https://git.zx2c4.com/wireguard-android/plain/ui/build.gradle.kts).

## Recommendation and approval boundary

Keep this working deployment demo-only. The saved-URL procedure above is ready for
approval independently of encryption work; it changes only the separate kiosk.
Next investigate free-DNS/GTS issuance if third-party account setup is acceptable,
then test the exact chain before changing the permanent address again. If that
path fails, evaluate the dedicated OpenVPN client/server proof before writing a
custom native gateway. Neither private data nor credentials should be enabled over
the present HTTP link.


## Subsequent HTTPS finding

See [the updated HTTPS plan](pf1007l-https-plan.md). ZeroSSL comparison endpoints
now pass both copied-root validation and physical WebView testing. Free DNS plus
ZeroSSL ACME is the preferred next proof, ahead of Google Public CA account setup.
No hostname/account/certificate has been created, and the working HTTP deployment
and saved kiosk address are unchanged.
