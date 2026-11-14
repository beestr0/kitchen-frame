# PF1007L compatible LAN HTTPS plan

Investigation updated 2026-11-13. No purchase, account creation, certificate
issuance, DNS modification, deployment or permanent kiosk URL change was made.
This plan supersedes the earlier preference for Google Public CA as the first CA
to try. The working demo-only HTTP service remains untouched.

## Recovery verification completed

The existing test succeeded; it did not time out. At 19:50:12, its SIGKILL stopped
only proxy PID 475683. Systemd scheduled a restart at 19:50:17; PID 475842 opened
the listener at 19:50:20. Health returned in **8.75 seconds**, and NRestarts rose
from 0 to 1. The result file and journal agree. Both project services remain
enabled/active. Jellyfin PID 459473, Tailscale PID 468133, `/mnt/media` and existing
IPv4/IPv6 filter rules were unchanged. No installation, resource recreation,
second crash test or new administrator authentication was necessary.

Private evidence: `diagnostics/pf1007l/finalization/recovery-verification.json`.
The checker's deliberate crash explains NRestarts=1; it is not an unexplained
production failure. Host reboot/power-loss testing remains outside this result.

## Recommendation

Use a **free DNS hostname plus a ZeroSSL ACME certificate**, served by a separate
LAN-only HTTPS listener on the Mint server. This is currently the simplest
promising option that preserves the kiosk, its normal certificate validation and
Android's existing trust store. It needs fewer account/project steps than Google
Public CA. The actual issued certificate and renewal chain must still pass both
copied-root verification and physical WebView testing before promotion.

ZeroSSL documents no-charge, automated 90-day ACME certificates and EAB account
registration. This applies to ACME, not an assumption that every REST API or
manually managed certificate product is free. DuckDNS offers free hostnames and
TXT updates suitable for DNS-01 validation. A hostname still needs to be registered
and its availability/issuance checked after approval.
[ZeroSSL ACME documentation](https://zerossl.com/documentation/acme),
[DuckDNS DNS/TXT API](https://www.duckdns.org/spec.jsp).

Expected recurring service fees: **$0 using the documented free services**, with
no domain purchase, paid plan, load balancer or public router ports. Stop rather
than enter a paid upgrade/payment flow. Free providers are external dependencies;
this is not a service-level or perpetual-pricing guarantee.

## New compatibility evidence

The copied frame system store includes USERTrust RSA and USERTrust ECC roots.
Mac OpenSSL was restricted to that copied store, with hostname checking,
`-verify_return_error`, and default CA paths/stores disabled.

| Endpoint | Copied frame roots on Mac | Physical frame WebView |
| --- | --- | --- |
| `https://zerossl.com/robots.txt` | Verified; ZeroSSL ECC DV SSL CA 2 → Sectigo E46 cross-sign → USERTrust ECC | HTTP 200; secure; TLS 1.3; issuer ZeroSSL ECC DV SSL CA 2 |
| `https://acme.zerossl.com/v2/DV90` | Verified; Sectigo OV R36 → Sectigo R46 cross-sign → USERTrust RSA | HTTP 200; secure; TLS 1.2; issuer Sectigo OV R36 |
| `https://pki.goog/` | Current chain verifies through existing GlobalSign | Earlier physical control already passed; not repeated this review |

These are **comparison endpoints**, not a certificate issued to our dashboard.
The first proves an actual current ZeroSSL DV chain works on this physical frame;
the second confirms an RSA/USERTrust chain as well, although its leaf is OV rather
than the DV certificate we would request. Actual issuance, hostname resolution,
local HTTPS/API/WebSocket behavior and renewal remain to be tested.

The observed Sectigo RSA/ECC root cross-sign certificates expire in January 2038;
leaf certificates and intermediate CAs have their own earlier renewal/expiry dates.
This is an observed certificate date, not a promise that the provider will keep
issuing the same chain until then. Google's current comparison chain contains a
GlobalSign cross-sign expiring **2028-01-28**. That makes its present legacy path
less attractive for a deployment intended to last years without Android trust
updates. Google remains a fallback; it explicitly documents alternate legacy
chains, but selecting one is conditional on actual issuance and future availability.
[Google alternate-chain documentation](https://developers.google.com/public-key-infrastructure/updates/march2025-alternate-chains),
[ZeroSSL legacy-chain guidance](https://help.zerossl.com/hc/en-us/articles/360060198034-Legacy-Client-Compatibility-Cross-Signed-Root-Certificates).

Physical probes used temporary navigation within only the separate test kiosk.
No key or personal credentials were used. Its existing Linux Home page was restored,
remote debugging/forwarding removed, and native preferences compared byte-for-byte
with the private backup: unchanged. Saved native URL is still the USB fallback.

Private evidence under `diagnostics/pf1007l/finalization/`:
`physical-ca-result.json`, `zerossl-comparison.json`, public chain captures,
`gts-current-frame-roots.txt`, and the copied-root subject inventory.
No new root certificates or certificate exceptions were installed on Android.

## Exact next proof, requiring approval

1. **Free accounts/hostname.** Register a neutral available DuckDNS name such as
   `desk-<random>.duckdns.org` (example only), plus a free ZeroSSL account. Use secure
   browser login and obtain ACME EAB/DNS credentials into protected local/server
   files. No chat credentials, CLI secret arguments, shell history, debug logs or
   frontend secrets. No existing Cloudflare resource changes are needed.
2. **DNS resolution.** Resolve the name to `10.157.1.115`. DNS-01 certificate
   validation only needs public TXT visibility; it does not require public HTTP,
   a public IPv4 address or port forwarding. Check whether DuckDNS accepts the
   intended private A record and whether the home resolver allows it. If rebinding
   protection blocks it, use a separately approved local DNS override; do not
   disable global protection or change Android DNS. An unavailable safe resolution
   path is a blocker, not permission to alter router settings.
3. **Automated issuance.** Use an isolated, pinned/reviewed ACME client with automated
   DuckDNS DNS-01 updates and ZeroSSL EAB. Keep its account state, DNS token, EAB
   material and server private key under restrictive permissions. Inspect credential
   handling/logging before execution. Prefer an RSA leaf initially for conservative
   legacy compatibility; actual leaf/chain acceptance is the deciding check. Do not
   buy a certificate or substitute a different default CA silently.
4. **Validate full chain before serving.** Verify hostname, dates, server purpose and
   full chain against copied frame roots. Include the appropriate intermediates/
   cross-sign, not merely a new Sectigo root absent from the frame. Never append an
   arbitrary trusted root to an unrelated chain or trust `--preferred-chain` as proof
   of success: some clients fall back if the preference is unavailable.
5. **Separate HTTPS proof.** Port 8789 was unused at inspection. Create only new
   project-specific HTTPS service/guard assets (proposed names
   `pf1007l-proxy-https.service`, `pf1007l-proxy-https-firewall.service`, own nft table),
   bound to the explicit LAN address and restricted to the frame. Keep port 8788
   and its current files/rules unchanged. Use an isolated HTTPS proxy code/config
   version, server-side cloud credential, and fully verified upstream HTTPS.
6. **Application adaptation.** Separate the bind IP from the accepted DNS authority.
   Use `https://<name>:8789/`, exact Host/Origin checks, HTTPS redirects and matching
   CSP. Keep assets/API same-origin; support `wss://` forwarding in the design.
   A generic TLS wrapper alone is insufficient because today's proxy expects a
   literal `10.157.1.115:8788` authority. Keep `demoOnly=true`, live WebSockets and
   writes blocked during proof. No personal data or cloud mutations.
7. **Physical proof and renewal.** Temporarily open the HTTPS URL without changing
   the saved kiosk URL. Test normal certificate validation, all views/themes,
   reconnection, reboot-time clock considerations and performance. Verify invalid
   chains/wrong hostnames are rejected. Exercise automated renewal and atomic
   certificate activation, validating every new chain before reload and retaining
   the previous valid certificate for rollback. Add expiry/renewal-failure monitoring.
   DNS or renewal outages must never trigger certificate bypass or HTTP fallback.

A dedicated certificate client does not need to change Jellyfin, Tailscale,
NordVPN, existing storage or public Cloudflare resources. New listeners/rules and
account creation are approval boundaries, not changes already made.

## Rollback and promotion

Until acceptance, 8788 remains the working demo fallback. Roll back by restoring
the current Linux HTTP page through temporary navigation and stopping only the
new HTTPS units; leave old proxy/guard, Cloudflare and protected credentials intact.
No certificate/hostname deletion is needed for immediate rollback.

After HTTPS and renewal proof, seek separate approval to persist the HTTPS URL.
HTTP and HTTPS have **different browser storage origins**, so explicitly enable
demo mode and preferred settings on the HTTPS origin without clearing the old
origin. Before personal integrations, remove any direct HTTP path to private APIs
and review the kiosk's permissive mixed-content/navigation settings. Retain normal
HTTPS validation on both legs. Encryption does not update Android/WebView security.

If safe free DNS/ZeroSSL issuance cannot be made reliable, try GTS with an explicitly
compatible chain or evaluate the previously documented dedicated OpenVPN proof.
A new VPN client/network configuration is more intrusive than this HTTPS plan.
No obsolete client, trust-all callback or Android CA installation is an alternative.


## Implementation preparation

Local HTTPS and ZeroSSL DNS-01/renewal automation is now implemented and tested.
See [the implementation, provider comparison and account actions](../deploy/lan-proxy/tls/README.md).
The preparation has progressed to a successful Linux installation and real ZeroSSL
certificate issuance. Physical acceptance and scoped timer enablement passed; see
[the current installation results](pf1007l-https-installation.md).
