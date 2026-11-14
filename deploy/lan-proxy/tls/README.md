# LAN HTTPS / ZeroSSL automation

**Current update:** the owner subsequently approved saving the HTTPS URL. Promotion, restart and corrected automatic-recovery tests passed; see [permanent HTTPS results](../../../docs/pf1007l-permanent-https.md). Earlier unchanged-URL statements below describe the pre-promotion test.

**Status (2026-11-14 UTC):** installed on Linux using the existing saved private
configuration. ZeroSSL issuance and validated activation succeeded; HTTPS runs on
8789 alongside the unchanged HTTP fallback on 8788. Automatic crash recovery
passed in 7.69 seconds. Physical WebView acceptance passed; HTTPS, guard, renewal and monitoring
are enabled for startup. The saved kiosk URL remains unchanged. See [installation results](../../../docs/pf1007l-https-installation.md).

The account instructions below describe the original setup; existing credentials
must be preserved, not collected again during a normal resume.

## Owner actions needed

1. Sign in at <https://www.duckdns.org> and register **one dedicated free hostname**.
   Send only the full hostname to the assistant. Do not send its token. Do not
   install a DDNS updater: automatic WAN-IP detection would overwrite the required
   LAN record. The token can affect other names in the same account; treat it as
   an account-wide credential, not a scoped per-host token.
2. Create/use a free account at <https://app.zerossl.com>. Complete email verification.
   In its Developer area, locate **ACME EAB credentials**. A paid REST API key is
   neither needed nor interchangeable with EAB. Do not buy a plan or post values
   in chat. Report only that the account is ready.
3. After the hostname is known, configure **only that new hostname's IPv4 record**
   to `10.157.1.115` and leave no conflicting AAAA record. We will first show the
   exact record change. No router/global resolver setting or port forwarding is
   required. Private A-record acceptance and home DNS-rebinding filtering remain
   untested until this name exists. If blocked, stop and discuss a narrowly scoped
   alternative; do not disable protection or modify global DNS.
4. Once these files are staged on the Linux server, a native Terminal SSH/sudo
   session will run `prepare_secrets.py`. It asks for the hostname/email and uses
   hidden terminal input for the DuckDNS token and ZeroSSL EAB ID/HMAC. It writes
   only root-private files on Linux and performs no DNS/ACME operation. Do not
   enter values into chat, shell arguments, clipboard scripts, environment dumps
   or a Terminal session being recorded. No secret collection is requested yet.

## Provider decision

| Provider | Free hostname / DNS-01 | Operational considerations | Decision |
| --- | --- | --- | --- |
| DuckDNS | Free subdomain; documented HTTPS TXT API | Small API; one shared TXT value across a name's sub-subdomains; account-wide token; use one dedicated hostname and serialized jobs | Recommended for this single display |
| Dynu | Free third-level names; TXT management/API documented | More flexible record model but more API/account setup; verify current free-tier permissions for chosen name | Alternative if DuckDNS or its local resolution fails |
| deSEC | Free DNS hosting and rich API | `dedyn.io` registration has been suspended/restricted; hosting an already owned domain does not supply an immediately usable new free name | Not the simplest predictable new-hostname choice |

No free provider is guaranteed to have better uptime or permanent pricing. Renewal
must fail visibly and preserve a valid active certificate when a provider is down.

Sources: [DuckDNS](https://www.duckdns.org/spec.jsp),
[Dynu free hostnames](https://www.dynu.com/en-US/DynamicDNS),
[Dynu API](https://www.dynu.com/Support/API),
[deSEC registration restrictions](https://talk.desec.io/t/update-dedyn-io-suddenly-fails-responds-with-nohost/1099).

## Files and behavior

- `scripts/pf1007l-lan-proxy.mjs` now supports an optional `tls` configuration.
  HTTPS separates the DNS authority from the bind IP, enforces TLS 1.2+, checks
  certificate dates/hostname/key pairing, protects private-key reads, and uses
  HTTPS redirects and a WSS-aware CSP. Without `tls`, HTTP mode still works.
  This modified source has **not** replaced the server's working HTTP source.
- `config.json.example` keeps demo-only/read-only policy on 8789. Its placeholder
  hostname is intentionally invalid and must be replaced before use.
- `prepare_secrets.py` refuses existing files; it never silently overwrites a key
  or account configuration. Root-owned `/etc/pf1007l-tls/` is 0700; its generated
  profile, token and Certbot configuration are 0600. EAB material is read from
  Certbot's private configuration, not process arguments.
- `dns_hook.py` only modifies the chosen name's TXT record through validated HTTPS
  to a fixed DuckDNS endpoint. Redirects are refused. It never updates A/AAAA.
  It validates Certbot's exact single identifier, refuses foreign TXT challenges,
  polls all authoritative servers before allowing ACME validation, and cleans only
  the matching challenge. Exceptions never print credential-bearing URLs.
- `run_acme.py issue|renew` uses only the explicit ZeroSSL ACME endpoint and
  `pf1007l-desk` certificate in its own state directory. It requires local resolution
  to exactly the reviewed IPv4 address, takes an exclusive lock, captures client
  logs privately, and checks that issued/active certificates match and have at least
  21 days remaining. An error or a failed deploy hook cannot be reported as success
  merely because Certbot exited zero.
- `activate_certificate.py` checks the chain against the copied public frame roots,
  hostname, server purpose, at least 30 days remaining, private-key permissions and
  key pairing. It copies to a new versioned private bundle, atomically switches a
  `current` link, restarts only `pf1007l-proxy-https.service`, and waits for validated
  HTTPS health using the frame roots. Failure restores/restarts the previous bundle;
  an initial activation failure stops only the new HTTPS listener. It never touches
  HTTP 8788. Identical-bundle retries still verify service activation.
- The new systemd proxy/guard units use DynamicUser/LoadCredential and a separate
  `inet pf1007l_proxy_tls` table. They use neither global firewall resets nor default
  policy changes. IPv4 Ethernet from the frame and server-local health are the only
  allowed TCP 8789 paths; other 8789 traffic is dropped, including IPv6/Tailscale.
- The dedicated renewal timer checks twice daily with jitter and a persistent
  catch-up. It invokes only this project's root-private ACME state, with a
  20-minute service timeout. It does not change a global Certbot timer.

ZeroSSL documents free 90-day ACME certificates. No implicit default CA or paid
API fallback is permitted. Raw Certbot logs remain root-private because client
libraries can log account metadata. Hook diagnostics outside those logs are
sanitized. Certbot 5.10.0 was installed **only in an ignored local test venv**;
`requirements.txt` pins the locally exercised client and dependencies. It supports
Python >=3.10; the server's existing Python 3.12.3, dig and OpenSSL were found.
Linux dependency installation is not yet performed or validated. If the server
lacks venv/ensurepip support or compatible wheels, stop before global package or
compiler changes and review the isolated-runtime alternative.

[ZeroSSL ACME](https://zerossl.com/documentation/acme),
[Certbot hooks and renewal](https://eff-certbot.readthedocs.io/en/stable/using.html).

## Required deployment order after account setup

This is a reviewable sequence, not a command to rerun the HTTP installer.

1. Snapshot hashes/status of the current HTTP proxy and units, unrelated PIDs and
   filters. Confirm 8789/new unit names/table/directories are unused or recognize
   only artifacts from this HTTPS task. Refuse unrelated collisions.
2. Stage reviewed TLS scripts plus a **separate copy** of the updated proxy under
   `/opt/pf1007l-tls/`; preserve `/opt/pf1007l-proxy/` and its isolated Node runtime.
   Create an isolated Python venv under the new directory and install pinned
   requirements without upgrading global Python/system packages. Verify the actual
   Linux dependency set and executable paths before a privileged service start.
3. Place non-secret HTTPS config/firewall at `/etc/pf1007l-proxy-https/` (0755),
   code/root-owned scripts at 0755/0644 as appropriate, and root-private certificate
   state at `/etc/pf1007l-tls/` and `/var/lib/pf1007l-acme/` (0700). Put the copied
   public frame CA bundle at `/etc/pf1007l-tls/frame-roots.pem`. The existing backend
   credential stays in its original root-private file and is supplied by systemd.
4. Securely collect credentials with `prepare_secrets.py`. Confirm per-host DNS A,
   absence of unexpected AAAA and relevant CAA permissions from server and frame.
   Browser navigation to an unissued certificate is not a substitute for DNS checks.
5. Create **both** HTTPS unit files before `daemon-reload`; run unit/nft syntax checks
   and ensure paths/dependencies are valid. Keep the renewal timer disabled. Do not
   start the HTTPS proxy until certificate activation. Do not reset unloaded units
   or run the old HTTP installation automation.
6. Run the dedicated `run_acme.py issue` through secure Terminal/root authentication.
   Certbot saves its automated DNS hooks; successful issuance invokes the deploy
   hook, which supplies the first bundle and starts the new proxy/guard. If the CA's
   default fullchain lacks a compatible cross-sign, activation must fail. Inspect
   the actual chain and obtain/verify a legitimate alternative; never trust a new
   root, disable checks, or silently substitute a CA.
7. Exercise `--check-config` in the actual DynamicUser/credential context, validated
   server health and non-allowlisted-client rejection. Check backend validated TLS,
   no frontend key, and demo-only API/WS policy. Do not print secrets for debugging.
8. Temporarily navigate the test kiosk through DevTools to `https://<hostname>:8789/`
   without an ADB data URI (which would persist it). Initialize invented demo data
   on the new HTTPS origin, which has separate localStorage. Test Home, Calendar,
   Tasks, Focus, Settings, light/dark, same-origin assets/API and performance.
   Confirm normal TLS and invalid-host/chain rejection. Keep live WS and writes
   blocked; WSS routing is prepared, not a live integration authorization.
9. Test controlled crash recovery of **only** the new proxy and confirm the HTTPS
   guard stays active and unrelated services/HTTP hashes stay unchanged. Repeat
   failure/recovery with temporary app-scoped networking rather than Android settings.
10. Exercise real ZeroSSL renewal once after reviewing rate limits/account state;
    record leaf fingerprint changes, activation and health. Do **not** use Certbot's
    generic `--dry-run` unreviewed: it uses staging behavior, may select another CA,
    and does not prove production ZeroSSL/legacy-chain renewal. Local fixture rotation
    tests are already complete, but do not constitute this real issuance test.
11. Only after acceptance enable the new service/guard/timer and review expiry
    monitoring. A failed timer or certificate below the threshold must be visible
    through project systemd status/journal; no external alerts are configured yet.
    Obtain approval before saving the permanent HTTPS kiosk URL. No personal
    integrations until that transport decision is accepted.

## Rollback and known limits

Immediate rollback is temporary navigation back to
`http://10.157.1.115:8788/?diag`. The frame's saved native URL remains the old USB
fallback until separate approval. No HSTS, Android CA install, firmware, WebView,
launcher, router forwarding or permanent network setting change is part of proof.

If reverting the new HTTPS host service, stop/disable only
`pf1007l-cert-renew.timer`, `pf1007l-proxy-https.service` and
`pf1007l-proxy-https-firewall.service`. The guard removes only its own TLS table.
Preserve certificate/ACME files for reversible troubleshooting. Never flush nftables
or change the original HTTP units, Jellyfin, Tailscale or Cloudflare.

A conflicting/stale TXT challenge fails closed rather than overwriting unknown
records. If a process was killed before Certbot cleanup, a verified task-owned
stale challenge may need deliberate cleanup before retry. A provider outage can
also delay renewal. Current timer failures are local systemd diagnostics, not
remote notifications. Root/issuer migrations can invalidate future bundles even
when current public comparison sites work. There is no automatic HTTP downgrade.
The original HTTP listener remains demo-only and must not expose personal data
when HTTPS is later enabled. Keep device time synchronization working.

## Validation completed locally

`python3 -m unittest discover -s deploy/lan-proxy/tests -v`: **48 passed**.
Tests use invented keys/certificates in private temporary directories and scoped
client trust only; no test CA is installed on Android or any system trust store.

Coverage includes actual TLS sockets with valid trust, wrong-host and untrusted-CA
rejection, foreign-origin denial, plaintext rejection on the TLS port, unchanged
HTTP mode, key mismatch/near-expiry/untrusted-chain rejection, atomic renewal and
rollback after restart/health failure, first-install failure cleanup, DNS challenge
collision/cleanup, secret-redacted error handling, and the existing safe installer.

Certbot 5.10.0 parsed both generated issue/renew commands offline with the correct
ZeroSSL URL and project certificate name. No ACME request or account registration
was made. Local syntax/diff checks pass. Final test output and the isolated client installation log are retained under
ignored `diagnostics/pf1007l/finalization/`; initial fixture failure output is also
retained in the tool record.

Blocked on account setup: real certificate issuance/renewal, live DNS resolution,
Linux HTTPS service installation and restart tests, physical dashboard UI/performance
on **our own HTTPS hostname**, and permanent URL promotion. Prior public ZeroSSL
comparison-host tests on the physical frame are evidence of CA compatibility,
not proof that those remaining steps have already passed.

A final additional read-only SSH health recheck was blocked because the cached
authenticated session had expired (`Permission denied (publickey,password)`).
Earlier this turn both HTTP units were active and 8789 was unused. No server
mutation was performed during preparation. Establish a fresh secure SSH session
when account setup is ready; do not rerun the HTTP installer to fix authentication.
