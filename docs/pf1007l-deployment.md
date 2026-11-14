# PF1007L standalone deployment preparation

For the executed deployment, security tests and unresolved Android certificate blocker,
see [deployment results](pf1007l-deployment-results.md).

For the subsequent authorized account inventory and the recommended Pages + private
Worker option, see [Cloudflare inventory and deployment proposal](pf1007l-cloudflare-inventory.md).
That report supersedes the domain-selection and account-access prerequisites below.

Prepared locally on 2026-11-13. **No Cloudflare account credentials were used and no
cloud resource or Android system setting was changed.** A later approved temporary
HTTPS kiosk probe and restoration are documented below.
The live USB fallback at `http://127.0.0.1:5173/?diag` remains available (HTTP 200,
reverse mapping present, test kiosk foreground). HomeHQ remains untouched.

## HTTPS investigation

Chromium defines `net_error -202` as `CERT_AUTHORITY_INVALID`, while certificate
date failures use `-201`. The frame's clock was correct at inspection. This makes
an untrusted/incomplete certificate chain the leading explanation, not a dashboard
JavaScript or Worker API failure. The initial investigation preceded the exact
hostname; the confirmed reproduction against it is recorded below.

Read-only inspection copied 158 **public** system CA certificates from
`/system/etc/security/cacerts` into gitignored `diagnostics/pf1007l/`.
The inventory contains no ISRG Root X1/X2 or GTS roots. It does contain GlobalSign
Root CA and several DigiCert roots. User-installed trust anchors were not inspected.
Updating WebView alone does not establish that the OS trust anchors are current.

Mac OpenSSL tests explicitly used only the copied frame roots, enabled chain
validation and checked the requested hostname:

| Public comparison host | Observed chain / validation |
| --- | --- |
| `www.cloudflare.com` | Let's Encrypt YE1 / ISRG chain; failed with unable-to-get-local-issuer |
| `pki.goog` | GTS WE2 → cross-signed GTS Root R4 → existing GlobalSign Root CA; verify code 0 |

These are comparison hosts, not the previous dashboard. OpenSSL's path building
and network route differ from Android WebView, so this is evidence for a solution,
not physical HTTPS acceptance. Captures: `cloudflare-chain.txt`, `gts-chain.txt`,
`ca-inventory.json` in the ignored diagnostic directory.

Cloudflare documents that its Let's Encrypt chain change affects Android 7 and
earlier and recommends GTS certificates for compatibility. Its CA documentation
explains the older GlobalSign cross-signing path. No guarantee follows from the CA
name alone: the actual served chain, hostname, validity, signature algorithms and
renewed certificates must be checked.

Sources:

- [Chromium error definitions](https://chromium.googlesource.com/chromium/src/+/main/net/base/net_error_list.h)
- [Cloudflare old-client SSL troubleshooting](https://developers.cloudflare.com/ssl/troubleshooting/general-ssl-errors/)
- [Cloudflare CA compatibility](https://developers.cloudflare.com/ssl/reference/certificate-authorities/)
- [Workers custom domains](https://developers.cloudflare.com/workers/configuration/routing/custom-domains/)
- [Advanced Certificate Manager](https://developers.cloudflare.com/ssl/edge-certificates/advanced-certificate-manager/)

### Secure hosting decision

First inspect the actual previous hostname and its served chain without credentials.
If a new `workers.dev` address validates on the frame, it can serve the standalone
demo; do not assume every Cloudflare endpoint has the same chain. Wrangler's Worker
configuration does not select the TLS certificate authority for `workers.dev`.

If the served chain is incompatible, prefer a **new dedicated custom hostname** in
an owner-controlled Cloudflare zone with a compatible edge certificate chain, such
as GTS cross-signed to an existing GlobalSign root. A Workers custom domain provisions
DNS and a certificate automatically; inspect that actual certificate before deciding
whether a separate advanced certificate/CA selection is needed. Explicit CA selection
through Advanced Certificate Manager can require a paid add-on. Confirm available
zone controls, certificate priority, renewal behavior and cost before requesting
approval. Do not change a zone-wide SSL mode, existing site routes, CAA records or
certificates merely to test this dashboard.

Maintain TLS 1.2 or newer and normal hostname/date/chain validation. Keep the kiosk's
SSL handler cancelling failures. Do not use HTTP for permanent hosting, install roots
system-wide, override certificate errors, pin a short-lived leaf certificate or call
`SslErrorHandler.proceed()`. If a compatible server-side chain cannot be provided,
pause cutover and present alternatives; no Android trust-store change is prepared.

## Prepared local configuration

The existing `dashboard/wrangler.jsonc` targets `photo-frame-dashboard` and a fixed
existing KV ID. Its existence does not establish the user's account ownership or
whether it is still serving another frame. **Do not use `npm run deploy` for this
stage**: that command targets this existing configuration.

New files isolate the desk deployment:

- `dashboard/wrangler.desk.jsonc`: draft Worker name `pf1007l-desk-dashboard`, no
  existing namespace ID or custom-domain route; preview URLs and observability off.
- `dashboard/vite.config.desk.js`: explicit separate config and `dist-desk/` output;
  retains Chrome 106 JS / Chrome 61 CSS targets. Does not overwrite USB `dist/client/`.
- `dashboard/worker/desk.js`: production entry point denying **all API routes** with
  503 when `DASHBOARD_KEY` is missing, instead of the original development bypass.
  Configured keys use the existing bearer authentication. Public assets contain
  only the application shell; HTML remains uncached, with no-referrer and nosniff.
- `dashboard/worker/desk.test.js`: tests missing-secret rejection, incorrect/correct
  keys and public shell caching/security headers.
- `npm run build:desk`: builds only; there is intentionally no new deploy script.

`REPLACE_WITH_NEW_DESK_KV_ID` is an explicit placeholder, **not a deployable resource
ID**. Account ID, resource availability, hostname and key provisioning remain pending.
Do not run a deploy with the draft. Inspect the final generated Wrangler config as
well as source before any authorized deployment; a stale build can target stale IDs.

Local validation: **34 tests passed**, desk production build passed. The desk client
asset hashes match the previously tested client (`index-D5HOjphp.js` and
`index-wo8PUttg.css`); no UI feature or runtime dependency was added. Informational
Svelte default-config notices remain. No new Android APK is needed for hosting.

### Exact proposed cloud changes (none performed)

| Resource | Proposed action |
| --- | --- |
| Account | Confirm owner-selected account with authorized read-only inventory; set explicit account ID |
| Worker | Create **new** `pf1007l-desk-dashboard`; stop if the name already exists |
| KV | Create **new** `pf1007l-desk-dashboard-calendar`; bind only its returned ID as `CALENDAR` |
| Durable Object | Create new SQLite `MessageRoom` namespace scoped to the new Worker, migration tag `desk-v1`; bind `MESSAGES` |
| Static assets | Upload `dist-desk/client` with the new Worker |
| Secret | Set new, independent `DASHBOARD_KEY` on this Worker through approved secure input |
| Hostname | Initially new workers.dev endpoint for validation, or approved unused custom hostname after chain investigation |
| Logs/previews | Keep Worker observability disabled and preview URLs off |
| Scheduled jobs | None for the standalone demo; add a calendar cron only in a future integration change |
| Provider credentials | None: no iCloud, Todoist, Spotify, Bambu or Home Assistant tokens |
| Images binding | Omitted; inactive recipe/image features are not part of the standalone-demo acceptance scope |

The current frontend connects to the messages socket even in demo mode, so the new
MESSAGES binding is retained rather than leaving broken background requests. Current
source modules remain separate and active views alone mount. Review plan/quotas and
any new paid certificate subscription before approval; README account/price statements
are historical, not a verified account inventory.

## Authentication and credential handling

After separate credential authorization, use Cloudflare login or a narrowly scoped
token for the selected account. Do not paste tokens or calendar URLs into chat. Do
not inspect ignored `.prod.vars` or existing account secrets without authorization.
No authentication session/account inventory has been used in this investigation.

Generate a fresh strong dashboard key outside version control and set it as a Worker
secret; never bake it into JS, Wrangler vars, screenshots or committed files. The
API fails closed before the key is present. Static code remains public intentionally;
no personal content is embedded in it. Keep agent posting disabled by leaving
`AGENT_TOKEN` absent. A device key grants the existing frame API privileges; it is
not a per-user login system.

For provisioning on the frame, prefer entering the key directly into the permanent
origin's localStorage over an approved local DevTools session, then launch/save a
**key-free HTTPS URL**. The existing `?key=` bootstrap works but can expose a key in
request/intent logs, so do not put a production key in an ADB command or shared log.
The current WebSocket/image authentication still puts the key into request query
strings; disabled observability does not remove all Cloudflare infrastructure logs.
Before live personal integrations, review that residual exposure and whether to
replace those paths with secure same-origin cookie authentication. No provider
secrets belong on the frame.

## Verification and cutover gates

1. Obtain the old public hostname (no key) and permission to temporarily probe HTTPS
   in the test kiosk. Inspect its current chain and verify against copied roots.
   A current chain may differ from the historical failing one.
2. After credential authorization, inventory selected Cloudflare account, Workers,
   namespaces and any proposed zone/DNS/certificates **read-only**. Stop on name or
   hostname conflicts; do not adopt or overwrite an existing resource automatically.
3. Replace only approved placeholders locally, rebuild, run tests and local dry-run
   packaging, then show the exact account/name/namespace/hostname/certificate changes
   and cost implications for final approval. A dry run is not a deployment.
4. With explicit cloud approval, create only the new resources, set the independent
   dashboard key and upload the prepared Worker/assets. Missing-key API access must
   fail closed from the first upload. Verify unauthorized API access is denied,
   authorized access works, and HTML/assets have the intended caching behavior.
5. Before changing the saved frame URL, perform an approved transient HTTPS probe in
   the separate kiosk and verify the actual TLS connection. Use no SSL bypass. Restore
   the USB page if it fails. Do not load authenticated app data through a Mac TLS proxy
   and mistake that for frame-to-Cloudflare validation.
6. With frame-change approval, save the key-free permanent URL in the existing test
   kiosk; HomeHQ is unaffected. The new HTTPS origin has separate localStorage, so
   initialize demo mode, idle/theme preferences and focus state deliberately. Local
   USB state does not automatically migrate. Set demo before testing tasks.
7. Validate all four views, themes, persistence/reload, authenticated APIs and error
   logs over the frame's existing Wi-Fi. Then, with approval, remove only the reverse
   mapping and stop the Mac server; reload and verify the dashboard still works.
   Keep a way to restart the USB server and mapping. No reboot/autostart/default
   launcher change is included; standalone networking and auto-launch are separate.

Rollback after an approved URL cutover: restart the known loopback static server and
USB reverse mapping if needed, then launch `com.huntsyea.frame/.MainActivity` with
`http://127.0.0.1:5173/?diag`. Its USB-origin demo preferences are preserved. HomeHQ
remains available via `com.wesbos.homehq/.MainActivity`. Cloud rollback/deletion of
new resources requires its own approval; no unrelated resources need to be touched.

## Future pages (design constraints only)

Spotify Now Playing and Bambu A1 Mini are **not implemented**. Keep each future view
and server adapter separate, return small normalized status snapshots, back off on
errors, cache/poll at sensible intervals and suspend view-specific work when hidden.
Keep Spotify OAuth/refresh tokens server-side and request only necessary metadata
permissions; stream no audio. Printer credentials and any MQTT/cloud/LAN bridge must
also stay server-side/on a trusted bridge, with read-only status access and no camera
or print-control endpoint. A Cloudflare Worker cannot directly reach a private printer
LAN merely because the frame is on that Wi-Fi; resolve that topology in its own phase.

Next credential gate: authorized read-only Cloudflare account and zone inventory.
No deployment or permanent frame URL change is authorized by preparation alone.

## Exact hostname tested and restored — 2026-11-13

The owner supplied `https://home-hq.strotherbee.workers.dev/` and explicitly approved
a temporary key-free test in the separate kiosk. No dashboard access key, authorization
header or saved HomeHQ configuration was used. The Mac HTTP probe discarded the body.

| Test | Result |
| --- | --- |
| Mac normal HTTPS GET | HTTP **200**, certificate validation succeeded |
| Mac OpenSSL using only copied frame system roots | Verification code **20**, unable to get local issuer |
| Physical frame, existing kiosk | TLS handshake failure **net_error -202**, kiosk SSL error **3** |
| Restoration | Local URL restored; Home/demo/light screen visually verified; overlay 61 fps |

Observed server chain:

```text
*.strotherbee.workers.dev (leaf CN strotherbee.workers.dev)
  → Let's Encrypt YE1
  → ISRG Root YE
  → ISRG Root X2 (cross-signed by ISRG Root X1)
```

Leaf validity: 2026-11-12 18:27:08 UTC through 2027-02-10 18:27:07 UTC. Its SANs are
`*.strotherbee.workers.dev` and `strotherbee.workers.dev`, covering the tested hostname.
The matching hostname and currently valid dates do not compensate for a missing
trusted root. The supplied chain cannot terminate at an ISRG root trusted by this
frame's inspected system store. The physical handshake confirms the failure.

At 17:07:49 EST the test process logged:

```text
chromium: handshake failed; returned -1, SSL error code 1, net_error -202
FrameKiosk: ssl error 3 (device time Fri Nov 13 17:07:49 EST 2026)
```

This is a **certificate failure before an HTTP response on the frame**, not a 401/403
authentication failure. The Mac's HTTP 200 confirms successful TLS on the Mac only.
The kiosk also logged `loaded Frame` after the SSL error; its title-based load
heuristic is not reliable TLS evidence and was not treated as success. The SSL
handler still cancelled the failed connection, with no validation bypass.

The probe script restored the local URL in a `finally` block. A subsequent native
screenshot confirmed Home with invented tasks/events, light theme and the diagnostic
overlay. The local server still responds, the port-5173 reverse mapping remains,
and HomeHQ's APK is still present. No extra debug port or trust anchor was installed.
Evidence lives in ignored `diagnostics/pf1007l/home-hq-chain.txt`,
`home-hq-frame-probe.txt` and `restored-after-https.png`.

### Hosting recommendation after the confirmed failure

Do not try to repair this by redeploying the old Worker: its edge certificate is
outside the Worker application code. The certificate is a wildcard for this account's
workers.dev subdomain. A different Worker name under `strotherbee.workers.dev` can
receive the same incompatible wildcard certificate; it is not a dependable workaround.
We have no owner-controlled certificate/CA setting for this platform-owned hostname
in the prepared configuration. Only a Cloudflare-side certificate change could fix
the exact hostname; future certificate selection/renewal could also change behavior.

Prefer a dedicated, unused hostname under a domain the owner controls, for example
`desk.<owned-domain>`, attached to the **new** Worker. Cloudflare documents that a
Workers custom domain creates DNS and a default advanced certificate without a
separate Advanced Certificate Manager subscription. Inspect that issued chain first.
If it is incompatible, explicit CA selection/overriding the default certificate may
require additional certificate management and cost; present that exact change for
approval rather than deleting any certificate or purchasing anything automatically.
The target is a chain validated by the existing frame, such as the previously
Mac-verified GTS/GlobalSign path. A GTS label alone is not enough; validate the full
served chain, including after renewal, on the physical WebView.

Prepared `wrangler.desk.jsonc` now has `workers_dev: false`, `preview_urls: false`
and a commented custom-domain route example. It deliberately has no live route and
still has a new-KV-ID placeholder. Do not deploy this incomplete draft.

Exact proposed changes, subject to selected account/zone/hostname inventory and approval:

1. Create new Worker `pf1007l-desk-dashboard`; preserve existing `home-hq` and
   `photo-frame-dashboard` Workers. Stop on any name conflict.
2. Create new KV `pf1007l-desk-dashboard-calendar` and bind its returned ID as CALENDAR.
   Create the new Worker's SQLite MessageRoom namespace/migration as already prepared.
3. Provision the new independent DASHBOARD_KEY secret and upload the built desk assets
   and fail-closed Worker entry. Do not copy old provider credentials.
4. Add only the approved unused custom hostname, with
   `routes: [{ pattern: "desk.<owned-domain>", custom_domain: true }]`. This creates
   that hostname's DNS mapping and certificate; review existing DNS/routes/CAA first.
5. Validate the automatically issued edge certificate. If needed, separately approve
   a compatible certificate/CA change scoped as narrowly as possible, with its renewal
   behavior and pricing. No zone-wide TLS weakening, trust-store changes or paid
   subscriptions are part of the default plan.
6. Verify HTTPS on the Mac and frame before permanent kiosk cutover, preserving the
   USB fallback throughout. Only after success approve the saved URL change and final
   USB removal. HomeHQ and launcher defaults need no changes.

Next required information: an owner-controlled domain suitable for the dedicated
hostname, or permission to use Cloudflare credentials for **read-only** account/zone
inventory. This approval does not itself authorize resource creation or deployment.
