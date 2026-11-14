# Cloudflare read-only inventory and proposed deployment

**Subsequent authorized execution:** see [deployment results](pf1007l-deployment-results.md).
The stack is deployed, but its issued Pages certificate failed on the physical frame;
the USB dashboard was restored. The recommendations below describe the pre-deployment proposal.

Inspected 2026-11-13 using the existing local Wrangler OAuth session. No new login
or token was needed. Cloud API operations were GET requests only. No secret values,
database contents, KV values, printer data or provider credentials were retrieved.
No resources, subscriptions, certificates, DNS or Android configuration were changed.

This report supersedes the earlier assumption that this account had a custom domain
and the recommendation to require a purchased domain before investigating alternatives.

## Verified account inventory

One account is visible to the current authentication: account ID ending `de8d`.
The two draft desk configurations now explicitly pin that account, preventing an
accidental selection of another account during a later approved deployment.

| Resource | Read-only finding |
| --- | --- |
| Workers | One: `home-hq` |
| Existing Worker URL | `home-hq.strotherbee.workers.dev`, enabled; previews disabled |
| Worker bindings | `ASSETS` (assets), `ALERTS` (AlertHub Durable Object), `DB` and `home_hq` (same D1 database), `DASHBOARD_KEY` (secret name/type only) |
| Worker schedule | `*/5 * * * *` |
| Durable Objects | One namespace: `home-hq_AlertHub`, SQLite |
| KV namespaces | None |
| Pages projects | None |
| Worker custom domains | None |
| DNS zones | None; both account-filtered and unfiltered visible-zone queries succeeded with empty results |
| Account subscription/billing | HTTP 403: existing OAuth session cannot read this metadata |
| Registrar inventory | HTTP 403: not visible to existing OAuth session |

Existing `home-hq` logging is enabled and query-string redaction is off. This was
observed as configuration metadata only; logs or secret values were not inspected
and that configuration was not changed. No existing access key was used.

There is no eligible **Cloudflare-managed custom domain in this account** today.
This does not prove the owner has no domain at another registrar/account. Without a
zone, there is no zone certificate configuration, DNS hostname availability or ACM
subscription to inspect. Do not request broader billing/registrar permissions merely
to infer a domain exists. Billing can be checked by the owner in the browser if needed.

The older repository `wrangler.jsonc` KV ID does not appear in this account. Its
`photo-frame-dashboard` Worker also does not exist here. Do not use the generic
`npm run deploy` command or copy its namespace ID into the new deployment.

Sanitized metadata and public certificate evidence are in gitignored
`diagnostics/pf1007l/cloudflare/`. Authentication was kept in memory and not placed
in shell arguments, chat or these files.

## Recommended option: Pages HTTPS front door and private Worker API

Proposed hostname: **`pf1007l-desk-dashboard.pages.dev`**. The project name has no
collision in this account, but the global hostname is not reserved or guaranteed.
If Cloudflare assigns a suffix or reports a collision at creation, stop and review
the actual hostname before proceeding.

Cloudflare Pages certificates are independent of the observed incompatible
`*.strotherbee.workers.dev` certificate. A read-only Mac TLS check of the public
`cloudflare-docs.pages.dev` hostname, using only the frame's copied roots and normal
hostname/chain validation, succeeded with this chain:

```text
cloudflare-docs.pages.dev → GTS WE1 → GTS Root R4 (cross-signed) → GlobalSign Root CA
Verify return code: 0 (ok)
```

This is promising evidence for a no-domain-purchase route, **not a guarantee for the
new hostname**, nor a physical-frame test of Pages. The new hostname's actual chain
must be inspected after creation and then tested on the frame with explicit approval.
Pages selects/manages its certificates; this plan neither pins a CA nor orders GTS.
If the assigned chain is incompatible, do not bypass validation or cut over. Revisit
the custom-domain option below. Recheck compatibility after certificate renewals.

Proposed request flow:

```text
Frame -- validated HTTPS --> new Pages hostname
                              ├─ HTML/CSS/JS: Pages static assets
                              └─ /api/*: Pages relay
                                           └─ internal service binding
                                                └─ new private desk Worker
                                                     ├─ new CALENDAR KV
                                                     └─ new MessageRoom Durable Object
```

The frame never needs to establish a TLS connection to `workers.dev`. APIs remain
same-origin, so browser authentication and future integrations need no cross-origin
workaround. The relay forwards the original request/response, including authorization,
POST bodies and WebSocket upgrades. The Worker remains fail-closed without its new
secret and has `workers_dev: false`, previews off and no public domain/route.

Service bindings from Pages to Workers and separate Worker ownership of Durable
Objects are supported by [Cloudflare's Pages bindings documentation](https://developers.cloudflare.com/pages/functions/bindings/).

### Local preparation completed

- `dashboard/wrangler.desk.jsonc`: new private backend, explicit selected account,
  new-KV-ID placeholder. No route is configured.
- `dashboard/wrangler.desk-pages.jsonc`: draft new Pages project, DESK_API service
  binding to the new backend; preview environment has no API service binding.
- `dashboard/hosting/pages-relay.js`: small API relay, no secrets; returns 503 when
  API binding is absent. Browser code and main view architecture are unchanged.
- `dashboard/scripts/prepare-desk-pages.mjs`: copies the separate desk build into
  ignored `dist-desk-pages/`, adds the advanced-mode `_worker.js` relay and an API-only
  `_routes.json`. Static HTML gets no-store; assets retain hashed caching; pages get
  no-referrer/nosniff headers. It neither deploys nor overwrites USB `dist/client/`.
- `npm run prepare:desk-pages`: build/package completed successfully.
- `npm test`: **37 passed**, including fail-closed API and relay behavior checks.

These are local unit/build checks. Pages runtime service binding, WebSocket handling
and the actual assigned certificate still require an approved deployment test. No
deploy command or automatic cloud creation was added to package scripts.

## Exact proposed cloud changes — approval required

| Item | Proposed action |
| --- | --- |
| Account | Use the inspected account pinned in the draft configs |
| Worker | Create NEW `pf1007l-desk-dashboard`; no public workers.dev, preview or custom-domain route |
| KV | Create NEW `pf1007l-desk-dashboard-calendar`; substitute only its returned ID as CALENDAR |
| Durable Object | Create the new Worker's SQLite MessageRoom namespace with migration `desk-v1`; bind MESSAGES |
| Authentication | Generate a fresh independent DASHBOARD_KEY and set only on the new backend; never copy the existing HomeHQ secret |
| Pages project | Create NEW Direct Upload project `pf1007l-desk-dashboard`, production branch `main`; stop on collision |
| Pages deployment | Upload reviewed `dist-desk-pages/`; bind DESK_API to the new private Worker; no production API binding in preview |
| DNS | No owned-zone or external DNS changes; Cloudflare supplies the Pages hostname |
| Certificate | Use the automatically managed Pages certificate; inspect and validate its chain before frame testing; no manual certificate order or paid ACM |
| Schedules/providers | No cron, real iCloud/Todoist/Spotify/Bambu/Home Assistant credentials or Images subscription |
| Existing resources | No changes to `home-hq`, its AlertHub/D1/secret/schedule/logging, or any existing app |

Approval should cover only new resources and the first test deployment. The actual
new namespace ID and assigned Pages hostname must be recorded before continuing.
Missing-key requests must fail closed during initial upload; provision the secret
before authorized API testing. Preview API access must remain unavailable. Do not
enable Git auto-deploys or mutate existing projects as part of Direct Upload setup.

After cloud creation/deployment, first inspect the new hostname's certificate and
unauthenticated API denial on the Mac. Obtain frame-test approval, then temporarily
load the new hostname, provision the new key through secure local debugging rather
than a key-bearing URL/command, and enable demo mode on the new origin. Return to USB
on any failure. Keep the Mac server/mapping available until Wi-Fi-only reload tests
pass and the owner approves removing them. No launcher/default-Home change is needed.

Existing URL-query authentication on message/image requests remains a logging/privacy
consideration before any live personal integrations; keep request logging disabled
on the new Worker and review cookie/session auth in that phase. No real private data
is part of the first standalone demo. Provider secrets remain server-side.

## Expected costs and alternatives

| Option | Expected cost / limitation |
| --- | --- |
| Recommended Pages + private Worker | No domain or certificate purchase. Static Pages requests are free; API/Worker/KV/SQLite-DO operations use shared account quotas. Target $0 additional cost within included allowances; cannot guarantee an account bill because billing access is unavailable and other usage shares quotas. |
| Workers Paid, if later needed | Published minimum $5/month per account, with usage charges above included allowances. No upgrade is proposed or authorized. |
| Bring a domain owned elsewhere | No new registration purchase; may require adding a Free Cloudflare zone and approved nameserver/DNS migration. Existing mail/sites/DNS must be reviewed first. A Workers custom domain includes its default certificate without a separate ACM subscription. |
| Buy a new domain | Annual registration/renewal, varying by name/TLD and premium status; no name selected or price quoted. Obtain an exact registration and renewal quote before approval. Cloudflare Registrar sells at registry/ICANN cost without markup. |
| Explicit custom-domain GTS/CA selection | May require paid ACM; Cloudflare advertises starting at $10/month. Verify actual zone checkout/availability before approval. No such purchase is recommended while Pages can be evaluated. |
| Ask Cloudflare to repair workers.dev compatibility | No resource change needed to report the issue; resolution, support availability and timing are not guaranteed. Does not provide a verified independent dashboard today. |

References checked during this investigation:

- [Pages/Functions pricing](https://developers.cloudflare.com/pages/functions/pricing/)
- [Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/)
- [SQLite Durable Objects pricing](https://developers.cloudflare.com/durable-objects/platform/pricing/)
- [Workers custom-domain certificates](https://developers.cloudflare.com/workers/configuration/routing/custom-domains/)
- [Cloudflare Registrar](https://www.cloudflare.com/domains/)
- [Advanced Certificate Manager advertised starting price](https://www.cloudflare.com/plans/business/)

No free-quota upgrade is technically required by the draft architecture. Actual account
plan, remaining quotas, usage and final Pages certificate are unresolved verification
items; do not infer a Paid subscription from `usage_model: standard` alone.

## Rollback and cleanup

During initial testing, leave the USB server and reverse mapping active. Restore the
test kiosk to `http://127.0.0.1:5173/?diag` on failure; the prior local-origin demo
preferences remain separate from Pages. HomeHQ remains an independent fallback.

After an approved stable release, future updates can roll back the new Pages deployment
and new Worker version together, retaining their KV/DO state. Do not roll back or
modify `home-hq`. Record successful deployment IDs and namespace IDs for this purpose.

If the owner abandons the new deployment, ask for explicit deletion approval and
remove only the new Pages project, new Worker, its new DO namespace and new KV, in
dependency order after confirming no required test data. Deleting/rolling back code
does not necessarily remove storage. No existing resource is part of cleanup.
No Android uninstall, data clear, certificate install or HomeHQ change is required.

**Next approval requested:** creation and deployment of the new Pages + private Worker
test stack above, with no paid subscription or domain purchase. If billing/quota
checks reveal a charge or upgrade requirement, stop before that action and report it.
Permanent frame URL cutover and removal of USB fallback remain separate approval gates.
