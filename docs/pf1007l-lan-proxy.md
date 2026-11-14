# PF1007L LAN reverse-proxy proof of concept

For subsequent read-only diagnostics of the actual Linux host and the server-specific
deployment proposal, see [Linux Mint assessment](pf1007l-mint-assessment.md).

Tested on the physical frame on 2026-11-13. **The proof of concept passed over Wi-Fi
with USB dashboard forwarding removed.** The frame was restored to the previous USB
Home screen afterward, and the temporary Mac proxy listener was stopped.

No Cloudflare deployment/configuration, HomeHQ, Android system setting, launcher,
certificate store, router, Linux service, Jellyfin, Tailscale or NordVPN configuration
was changed. Only invented dashboard data was used. No Linux connection was made:
the server address/access details are not known, and local Tailscale CLI discovery
was unavailable. Linux-specific resource, routing and firewall checks remain pending.

## How it works

```text
Frame -- LAN HTTP + ws --> restricted proxy on always-on server
                              -- verified HTTPS + wss --> Cloudflare Pages
                                                            -- service binding --> private Worker
                                                                                   KV / MessageRoom
```

`scripts/pf1007l-lan-proxy.mjs` uses Node built-ins only, with no package dependencies.
It forwards the complete deployed application, relative same-origin API paths and
WebSocket upgrades. The tested upstream is fixed to
`https://pf1007l-desk-dashboard.pages.dev`; it is not an arbitrary forward proxy.
No new domain, paid service or Cloudflare change is required.

The proxy reads the existing new desk key from a protected server-side file and
injects it into the **encrypted upstream Authorization header only on API requests**.
The frame receives no key and needs none in localStorage or its URL. Empty frontend
`?key=` parameters are removed; nonempty client keys are rejected. The WebSocket
upgrade also uses upstream Authorization rather than putting the secret in a URL.
Client Authorization/Cookie/forwarded-address headers are not trusted or forwarded.
Existing Cloudflare authentication, Worker, KV and MessageRoom remain intact.

Upstream TLS uses `rejectUnauthorized: true`, normal hostname/SNI verification and
TLS 1.2 or newer. No certificate bypass, private CA, system DNS change or certificate
installation is involved. Linux will need a supported Node runtime with current CA
roots, independently of the old Android trust store.

### Access restrictions

- Requires an explicit RFC1918 IPv4 listener; refuses wildcard/public binds.
- Explicit source-IP allowlist, using the socket peer, never X-Forwarded-For.
- Exact Host check, plus Origin and cross-site Fetch Metadata checks.
- WebSocket upgrade restricted to `/api/messages/live` with matching Origin.
- No CORS allowance; same-origin resource policy, frame/base/form restrictions and
  a same-origin Content Security Policy are added to forwarded HTTP responses.
- No request/access log, header dump or query-string log. Health contains aggregate
  process/counter data only and has the same source/Host restrictions.
- Real API writes are **disabled by default** in the final source/config template.
  Only explicitly enabled task/dismiss POST routes could pass. Agent posting and
  other methods remain blocked. Demo task changes run locally in the browser.

The test allowed the frame plus the Mac's own LAN address for diagnostics, bound
only to the Mac's current LAN interface. These addresses are retained in ignored
diagnostic configuration, not proposed as permanent server addresses. A deployment
must use reserved frame/server addresses and an interface-specific firewall rule.

## Tests and measurements

| Test | Result |
| --- | --- |
| Home | Rendered invented events/tasks at 1280×800, DPR 1, no horizontal overflow |
| Calendar | Week/month views, next month and Today worked |
| Tasks | Invented task added and completed through touch controls |
| Focus | Countdown advanced, paused correctly and survived reload; reset afterward |
| Settings/themes | Settings modal, light/dark themes and theme persistence worked |
| Wi-Fi independence | Removed `adb reverse tcp:5173`; LAN dashboard reloaded and API returned 200 |
| Actual frame network path | DevTools document remote address was the Mac's LAN address, HTTP/1.1 |
| Same-origin APIs | Calendar GET returned 200 through proxy-authenticated Cloudflare backend |
| WebSockets | Secret-free browser connection upgraded and ping/pong passed; frame app established connections before/after reload |
| Reconnection | App-scoped offline fetch failed as expected; online fetch returned 200 afterward |
| Source/Host/Origin gates | Wrong source, Host, Origin and cross-site browser requests returned 403 |
| Key protection | Frame's LAN-origin `frame-key` remained absent; response bodies/headers contained no key |
| Final write guard | A valid task POST was rejected locally with 403 before reaching Cloudflare |

USB remained connected for debugging/input, but **application traffic used Wi-Fi,
with no USB reverse mapping during the reload/API check**. Cleanup restored the
original mapping and local URL, disabled WebView debugging and removed port-9223
forwarding. This was a short test, not an overnight reliability or finger-accuracy test.

Five-second settled rendering-loop samples during the physical test:

| View | Reported fps | Gaps over 50 ms | Maximum gap |
| --- | ---: | ---: | ---: |
| Home, early sample | 57.0 | 3 | 149.6 ms |
| Calendar week | 60.2 | 0 | 17.1 ms |
| Tasks | 60.2 | 0 | 17.7 ms |
| Focus paused | 60.2 | 0 | 16.9 ms |

Home showed brief initial jank; screenshots of Home, Calendar, Tasks, Focus and
Settings showed no obvious missing styles or clipping. These requestAnimationFrame
samples are not a guarantee of display presentation timing or sustained 60 fps.

Proxy RSS during the physical suite was approximately **26–29 MiB**, ending at
28.4 MiB. Its measured CPU use over 57.9 seconds was **0.22% of one Mac CPU core**.
This includes the proxy's HTTP/API/TLS/WS work, not the browser/ADB test tools.
The frame used approximately **79 MiB total PSS**, with no attributed swap in the
snapshot. These are M1/frame measurements, not measurements of the Linux server.

Evidence is retained in ignored `diagnostics/pf1007l/lan-proxy/`: security-test results,
`frame-LAN-proxy-results.json`, screenshots and the final safety check. The source
and systemd/config templates contain no secret. A Git-visible-file scan found no
copy of the existing protected desk key.

### DNS/VPN failure observed after the successful suite

A subsequent Mac check encountered a real **DNS resolution timeout**. A direct curl
request to the cloud hostname failed resolution too. A diagnostic-only curl address
override, retaining normal hostname/certificate validation, returned HTTP 200. This
isolates that later failure to name resolution rather than the Cloudflare app or TLS.
No address is pinned in production code and no DNS setting was changed.

The Mac resolver listing included Tailscale and VPN resolvers. Their presence alone
does not prove which caused the timeout. This is a reason to inspect Linux DNS/VPN
behavior before claiming unattended reliability, not a reason to disable either VPN.

Added an overall **15-second upstream deadline**, covering DNS/connect/TLS as well as
socket inactivity. During the observed DNS failure, the final proxy returned a 502
retry page after 15.03 seconds; the page automatically reloads after ten seconds.
API failures return JSON and no-store so the app can retain its last successful data.
WebSocket connections use the app's existing retry/backoff and ping/pong. TLS failures
remain failures. Neither stale DNS bypass nor insecure fallback is used.

The final source differs from the fully exercised version only by the explicit
read-only default and bounded/startup-retry handling. Those additions received narrow
checks: real write rejection 403 and bounded automatic-retry response 502. The full
physical UI suite was not repeated during the Mac's DNS outage.

## Privacy decision: HTTP is a deliberate limitation

**The LAN leg is unencrypted and unauthenticated at the transport layer.** Android
correctly reports an insecure context. Upstream HTTPS does not protect frame-to-proxy
traffic. An active LAN adversary could read calendar/task information, alter the
delivered JavaScript or impersonate the frame/proxy. IP allowlisting is not cryptographic
device identity. Source spoofing/ARP manipulation and a compromised allowed device
are outside its protection. A malicious page injected on that link could use the
proxy's authorized capabilities even without learning the actual cloud key.

Host/Origin checks help with opportunistic access, DNS rebinding and browser-origin
attacks. They do not encrypt traffic. Private Wi-Fi/WPA protection and Ethernet do
not make every guest/IoT/LAN host trustworthy. No private calendar/task information
was exposed during this proof because none is configured and demo data was used.

This is appropriate for a demo or low-sensitivity display **only if the owner accepts
that residual LAN risk**, preferably on an isolated trusted frame/server network with
firewall restrictions. It is not my recommendation for confidential appointments,
work tasks, financial/medical data or a mixed guest/IoT network. Keep writes blocked
by default and obtain a separate decision before adding personal feeds/tokens.
OWASP recommends TLS on all pages; this approach is a constrained legacy-client
workaround, not equivalent protection. [OWASP TLS guidance](https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Security_Cheat_Sheet.html)

If that tradeoff is unacceptable, use a server endpoint with a publicly trusted
certificate chain the frame accepts, or investigate an encrypted tunnel/gateway that
actually protects the frame's network leg. Tailscale running only on the Linux server
does not encrypt ordinary HTTP from a frame without an overlay client. Either
alternative needs further design/approval; no Android trust changes, router changes
or purchases were made. A trusted HTTPS LAN hostname is preferable if one is already
available with an Android-compatible chain.

## Linux Mint / Jellyfin deployment plan — not installed

Prepared reviewable templates:

- `deploy/lan-proxy/config.example.json`
- `deploy/lan-proxy/pf1007l-proxy.service`
- Runtime: `scripts/pf1007l-lan-proxy.mjs`

### 1. Read-only preflight

Obtain the server's LAN hostname/IP and existing SSH access; never paste passwords
or tokens into chat. Confirm Mint/version/architecture, systemd version/credential
support, installed Node version, RAM/load and listening ports. Inspect Jellyfin,
Tailscale and NordVPN status, routes, DNS, LAN access policies and existing firewall
rules read-only. Do not restart/reconfigure them. Check that port 8788 is unused.

Specifically verify: frame → server Ethernet address TCP 8788; server → existing DNS;
server → Cloudflare HTTPS 443 through its normal route; and LAN replies return via
Ethernet without being captured by a VPN kill switch. Evaluate VPN-connect/reconnect
behavior later with explicit approval; do not toggle VPNs as a diagnostic shortcut.
Do not pin Cloudflare anycast addresses or replace global DNS to mask resolver issues.

### 2. Approval of a dedicated service

After preflight and the owner's privacy decision, install only a dedicated proxy
directory/service. If needed, use an isolated supported Node LTS runtime under
`/opt/pf1007l-proxy/node`, leaving Jellyfin's packages/runtime untouched. No npm
dependencies, containers, Docker-network changes or Jellyfin plugins are needed.
Do not change Jellyfin's listener, reverse proxy or ports 8096/8920.

Use `/etc/pf1007l-proxy/config.json` with the server Ethernet address and explicit
frame/server allowlist. Store the existing desk key separately, root-owned 0600.
The template supplies it through systemd `LoadCredential`; the runtime reads the
private credential path rather than placing a key in environment values or command
arguments. Confirm credential support before installation; do not upgrade systemd
globally merely to use the template. No key belongs in the JSON config.

The template uses DynamicUser, no capabilities, read-only system/home protection,
private temporary storage, low CPU priority, a 128 MiB ceiling and 10% CPU quota.
Those are proposed Linux limits, not settings applied to this Mac or server. Confirm
startup and responsiveness under the limits before enabling boot startup. It waits
for network-online and retries failures every five seconds; unavailable bind addresses
fail closed. Do not use PrivateNetwork, which would prevent the required LAN access.
See [systemd restart behavior](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html).

### 3. Narrow firewall/network approval

Preserve existing firewall policy and ordering. After inspecting the actual UFW/nftables
and NordVPN rules, propose an additive rule for **frame reserved IP → server Ethernet
IP TCP 8788 on the Ethernet interface**, with other remote sources denied for that
port. Keep the app allowlist too. Do not reset/enable/disable the firewall, flush
chains, widen Tailscale access or alter NordVPN's kill switch. If their existing rules
block the path, show the exact narrow exception before requesting approval.

Bind only the Ethernet LAN address, not all interfaces or the Tailscale/public address.
Use existing static/DHCP reservations if available. Router/DHCP/VLAN changes are a
separate approval; there is no router port-forward or public internet exposure in
this plan. Verify IPv6 is not listening and that guest/untrusted clients are denied.

### 4. Validate, then separately approve permanent kiosk URL

Test HTTP reads, local write rejection, WebSocket ping/pong and the real frame on
the server before enabling startup. Repeat screenshots, frame timing, process RAM/CPU
and upstream TLS checks. Observe a longer soak and service restart/reconnection with
approval, while verifying Jellyfin playback and Tailscale/NordVPN functionality.

Keep the Mac USB server/mapping as a fallback during testing. Only after acceptance
and explicit approval save the server's stable LAN URL in the separate kiosk. Its
new origin needs demo/theme/idle preferences initialized; do not copy a cloud key to
the frame. HomeHQ and default Home selection need no changes.

### 5. Rollback

Return only the test kiosk to its prior USB URL and re-establish the existing reverse
mapping if necessary. For a server rollback, stop/disable only the dedicated proxy
service and remove only its newly added firewall rule after approval. Jellyfin,
Tailscale, NordVPN, Cloudflare and HomeHQ need no rollback because they are not part
of the proposed changes. Delete the dedicated credential copy/config/runtime only
with deletion approval; preserve the original cloud key backup and deployment.

## Current state and next safe step

The Mac LAN listener on port 8788 is **closed**. The frame is back on the USB Home
screen, with the original mapping active and WebView debugging off. The cloud stack
and protected key remain unchanged. No permanent server or frame changes occurred.

Next: read-only Linux server inventory using its LAN address and existing SSH access,
then review the exact service/firewall proposal and explicitly decide whether LAN
HTTP is acceptable **before** configuring personal information or approving installation.
