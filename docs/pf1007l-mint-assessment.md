# Linux Mint host assessment — PF1007L

Read-only SSH assessment completed 2026-11-13 as `hub@10.157.1.115:22`.
The remembered SSH host key was accepted. Passwords were entered by the owner in
native Terminal SSH/sudo prompts, not supplied to the assistant or saved in reports.
No private key or credential file was read. Detailed diagnostic metadata is stored
under gitignored `diagnostics/pf1007l/server/`, not in this document.

**Conclusion:** this server has sufficient resources and a working LAN/Cloudflare
network path for the proxy. Node is missing and nothing was installed. For personal
calendar/tasks, encrypted transport remains preferable; the working HTTP design
still requires an explicit privacy decision before permanent use.

## Verified system and capacity

| Item | Observed result |
| --- | --- |
| Host | `hub-Inspiron-5570` |
| OS | Linux Mint 22.3 (Zena), Ubuntu noble base |
| Kernel / architecture | Linux 7.0.0-34-generic, x86_64 |
| CPU | Intel Core i3-8130U at 2.20 GHz, 2 cores / 4 logical CPUs |
| RAM | 3,808 MiB total, 2,935 MiB available at inspection |
| Swap | 4,003 MiB total, 161 MiB used |
| Load | 0.32 / 0.12 / 0.03; uptime about 42 days |
| Root filesystem | 916 GB total, 847 GB available |
| Media mount | `/mnt/media`, ext4; unchanged |
| systemd | 255; credential support is available in this version |
| Node / nodejs | Neither command nor package found |
| Existing reverse proxy | No nginx/caddy package or TCP 80/443 listener found |

The prior Mac proof measured roughly 26–29 MiB proxy RSS and 0.22% of one M1 core
for one frame. That is a baseline, not an Intel-server measurement. Budget roughly
64 MiB for normal operation with a proposed 128 MiB ceiling and a 10%-of-one-core
quota. A supported isolated Node LTS runtime needs to be installed only after
approval. Do not change Jellyfin's runtime or upgrade unrelated system packages.
Jellyfin's cgroup memory counter includes cache and must not be added directly to
the host's reported RAM-used figure.

## Network, DNS and VPN findings

| Item | Observed result |
| --- | --- |
| Active Ethernet | `enx00e04c6138c0` (carrier up) |
| Server LAN | **10.157.1.115/24**, NetworkManager manual/static configuration |
| Gateway / LAN DNS | 10.157.1.1 |
| Other physical interfaces | `enp1s0` and `wlp2s0` down |
| Frame Wi-Fi | 10.157.1.247/24; direct route to server |
| Server reply route | Frame traffic leaves Ethernet directly, source 10.157.1.115 |
| Tailscale | Active, healthy, 100.76.50.37; no exit node selected |
| Resolver | systemd-resolved stub 127.0.0.53 |
| Public DNS | Ethernet/router is default DNS path; Cloudflare hostname resolved successfully |
| Tailscale DNS | Scoped to tailnet/ts.net and reverse domains, not the default public-DNS route |
| Cloudflare HTTPS | Server curl returned HTTP 200, certificate verification 0 |

The server also has IPv6 addresses, including a globally scoped address. The proposed
proxy must bind only to the explicit private IPv4 address, with no wildcard/IPv6 or
Tailscale listener. Do not alter existing IPv6 configuration or other services.

### NordVPN discrepancy

The owner described NordVPN use, but this inspection found **no native `nordvpn`
command/package/service and no active NordLynx/OpenVPN tunnel or VPN process**.
OpenVPN 2.6 is installed. Its umbrella service is `active (exited)`, with no running
client instance. The `nordvpn` group exists, which does not establish an active client.
NetworkManager shows only Ethernet, Tailscale and loopback as active connections.

Current routes and firewall rules show no NordVPN kill switch interfering with LAN
or public DNS. This does not establish what happens if a previously used VPN profile
is re-enabled, nor whether a VPN operates elsewhere in the network. No VPN was
started, stopped, reconfigured or repaired. Preserve this current state unless the
owner explicitly asks otherwise.

NordVPN documents that Linux LAN traffic can be blocked depending on client version,
LAN discovery/allowlist and kill-switch settings. If NordVPN is activated later,
repeat routing, DNS, frame access and Cloudflare TLS checks first. Do not disable its
kill switch or broadly allowlist the home subnet to make the dashboard work.
[NordVPN Linux documentation](https://support.nordvpn.com/hc/en-us/articles/20196094470929-How-to-install-the-NordVPN-app-on-Linux-distributions)

## Firewall and existing services

The owner authenticated sudo securely in a local Terminal for fixed read-only checks.
UFW is **inactive**. IPv4/IPv6 INPUT/FORWARD/OUTPUT policies are ACCEPT; existing
iptables-nft tables contain Tailscale `ts-*` input/forward/NAT and mark rules. No
NordVPN kill-switch chain was observed. nft emitted existing iptables-managed-table
and MASQUERADE representation warnings; those warnings were preserved, not “fixed.”

Important current listeners:

| Service | Ports / state |
| --- | --- |
| SSH | TCP 22 |
| Jellyfin | TCP 8096; discovery UDP 7359; service active/enabled |
| Tailscale | UDP 41641 plus its own dynamic bound listeners |
| Samba | TCP 139/445, UDP 137/138 |
| NFS/RPC | TCP/UDP 111, TCP 2049 and dynamic RPC listeners |
| DNS stub / printing | Loopback 53 and 631 |
| mDNS | UDP 5353 |
| Proposed proxy 8788 | No listener; frame receives connection refused |

The frame successfully pinged the server (~6.9 ms in one sample) and received Jellyfin's
HTTP 302 response on port 8096. Thus frame-to-Ethernet TCP works today. A restricted
8788 listener is feasible under current routes/rules, but **not yet end-to-end tested
on this server** because starting one would exceed this read-only stage.

Jellyfin's PID remained 459473 and Tailscale's PID remained 468133 from initial to
final checks. Both remained active/running. The media mount remained ext4 and mounted.
No playback, storage contents or credentials were inspected, and no package/service,
mount, firewall, routing, resolver, router, NordVPN, Tailscale or Android configuration
was changed. The existing USB dashboard still returns HTTP 200 with forwarding intact.

## Secure transport decision before personal data

The proxy **must continue validating HTTPS to Cloudflare** and keep the device key
server-side. That protects the upstream leg and key distribution; it does not encrypt
the LAN HTTP page, calendar/task responses or `ws://` messages. A compromised LAN
participant or active interception can disclose/alter content and exercise the proxy's
capabilities without learning the cloud key. Source-IP checks are not device identity.

Preferred order:

1. **Compatible HTTPS endpoint:** use an existing owner-controlled hostname and a
   legitimate public certificate chain the frame accepts, either on a Worker custom
   domain or the local proxy. GTS cross-signing through the existing GlobalSign root
   was verified on the frame. No eligible domain was found in the inspected Cloudflare
   account and this server has no current HTTPS front door to reuse. Domain ownership,
   certificate issuance/renewal and DNS still need resolution; no purchase is authorized.
2. **Cloudflare-side compatible certificate:** request a supported GTS reissue/path for
   the new Pages project if Cloudflare can provide it. A support request was not sent.
   Do not buy ACM expecting it to override `pages.dev` certificate selection.
3. **Encrypted overlay:** this must protect the actual frame-to-server leg. Tailscale
   running only on the server does not do that. Current Tailscale Android requires
   Android 8+, while the frame is Android 6. Tailscale HTTPS certificates use Let's
   Encrypt, so simply using a `.ts.net` certificate does not solve this trust problem.
   Do not install an obsolete client or change the frame during this assessment.
4. **Restricted HTTP:** suitable for demo/low-sensitivity content only with explicit
   owner acceptance, ideally on a deliberately restricted device network. Keep live
   writes blocked. Network isolation reduces exposure but does not provide HTTPS
   confidentiality or integrity. I do not recommend it by default for private personal
   calendars, work tasks, medical/financial information or a mixed guest/IoT LAN.

Sources: [Tailscale Android requirements](https://tailscale.com/docs/install/android),
[Tailscale HTTPS issuance](https://tailscale.com/docs/how-to/set-up-https-certificates),
[OWASP TLS guidance](https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Security_Cheat_Sheet.html).

There is no currently verified no-change, no-domain, no-overlay HTTPS solution for
this frame. That limitation should not be concealed by calling restricted HTTP secure.
Do not configure personal feeds/tokens until a transport decision is made.

## Concrete proposed installation — not executed

Local review templates now contain the inspected addresses/interface:

- `deploy/lan-proxy/config.mint.example.json`
- `deploy/lan-proxy/firewall.mint.example.nft`
- `deploy/lan-proxy/pf1007l-proxy-firewall.service`
- `deploy/lan-proxy/pf1007l-proxy.service`

### Service and credentials

After installation approval, place an isolated, supported x86_64 Node LTS runtime and
the reviewed proxy under `/opt/pf1007l-proxy`. Verify official download signatures/
checksums. No npm dependencies are required. Keep configuration under
`/etc/pf1007l-proxy`; transfer the existing desk key through secure SSH input to a
root-owned 0600 file, never an argument, environment dump, frontend file or URL.
systemd 255 can supply it through LoadCredential to the DynamicUser service.

Bind **10.157.1.115:8788**. Only **10.157.1.247** is an application client. The server's
own address has access only to `/__proxy_health`, not the private APIs—otherwise a
compromised unrelated local service could use the proxy's authority. This health-only
restriction was added locally as preparation; no revised proxy was started or installed.
Confirm/reserve the frame's IP before installation; address assignment is not cryptographic
authentication. Real POST writes remain disabled.

Use network-online ordering, Restart=on-failure, five-second restart delay, rate limiting,
low priority, 64 MiB soft/128 MiB hard memory budget and a 10% CPU quota. The proxy
depends on the new firewall-guard unit so it cannot start if that guard fails. Preserve
the existing media mounts, Jellyfin unit/runtime and Tailscale settings. No containers
or global runtime/package upgrades are needed.

### Port-specific firewall guard

**Do not enable UFW globally.** That would change policy for Jellyfin, Samba, NFS,
SSH and Tailscale outside this project's scope. Do not flush or edit Tailscale's
iptables-nft tables or enable a global nftables ruleset that replaces them.

Instead, after approval and syntax/collision checks, create only a dedicated
`inet pf1007l_proxy` table with an early input hook and default ACCEPT. It permits
Ethernet traffic from the frame to this private address/port and local health traffic,
then drops other TCP 8788 input. All other ports keep their existing behavior. The
template is limited to INPUT; it changes no forwarding, NAT, VPN marks or DNS.

A dedicated oneshot unit owns only this table and starts before the proxy. Stopping
the guard stops the dependent proxy first; rollback deletes only this new table.
The template has **not** been applied or kernel-syntax-checked remotely. Validate it
with check-only mode before an approved installation, then verify both IPv4 and IPv6
port exposure and existing Tailscale/Jellyfin/storage access. Reassess rule persistence
after any future VPN reconnect or firewall-manager restart, with separate permission.

### DNS failure recovery and monitoring

Keep systemd-resolved, router DNS and scoped Tailscale DNS unchanged: current public
resolution and upstream TLS tests passed. Do not pin Cloudflare IPs or bypass TLS to
mask a DNS problem. The proxy has a 15-second DNS/connect/TLS deadline, no-store 502
API failures, and an initial HTML retry page reloading every ten seconds. The dashboard
retains cached feeds, and its WebSocket reconnects with backoff. A prolonged DNS failure
must be reported, not “repaired” by restarting VPNs or Jellyfin.

Proposed monitoring: service state/restarts, RSS/CPU, local health counters and recent
upstream errors; independently check public Cloudflare DNS/HTTPS status without keys.
Do not log API bodies, full URLs, authorization headers or secrets. Alert if the unit
restarts repeatedly, memory reaches its budget, or upstream failures persist. Do not
install a monitoring agent or enable a timer until separately approved.

Perform an initial demo-only acceptance test and longer soak on the server before
boot enablement or any frame URL change. Recheck Jellyfin playback and media-share
access with owner participation; no playback was disturbed for these diagnostics.
VPN disconnect/reconnect, reboots and permanent kiosk configuration remain outside
this authorization.

## Rollback and approval boundary

No server rollback is needed now: nothing was installed, enabled or changed. After
a future approved deployment, stop only the proxy and its guard, remove only their
new port-specific table/rule, and restore the test kiosk's USB URL/mapping if needed.
Leave Jellyfin, storage mounts, Tailscale, OpenVPN and Cloudflare resources untouched.
Removing service files/runtime/credential copies requires explicit deletion approval.

**Recommended next approval:** either resolve compatible HTTPS for personal data,
or approve a demo-only restricted HTTP server installation using these templates.
Do not combine installation approval with implicit acceptance of plaintext personal
calendar/task traffic, live provider credentials, a VPN change or permanent kiosk URL.


Implementation follow-up: the demo-only service was installed and physically
verified on 2026-11-13. See [installation results and rollback](pf1007l-mint-installation.md)
for current status; the earlier assessment remains the pre-installation record.
