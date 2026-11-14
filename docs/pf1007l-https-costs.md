# PF1007L HTTPS cost protection

Reviewed 2026-11-13. No purchase, subscription change, paid feature, Cloudflare
resource creation or deployment was performed for this HTTPS installation.

## What is verified and what is not

Existing Wrangler OAuth authentication refreshed successfully. GET-only account
and project metadata now work. The account default and this Worker report
`usage_model: standard`; that field alone does **not** establish a free subscription.
The account subscription endpoint returns **HTTP 403** with the available OAuth
permissions. Actual Workers plan, existing subscription charges, aggregate usage,
current invoice and payment/billing details therefore remain **unverified**.
Do not label the entire Cloudflare account free based on deployment success.

The owner can confirm Workers & Pages plan/usage and Billing subscriptions in the
Cloudflare browser dashboard without giving credentials to the assistant. No
broader billing token or paid upgrade is needed just to finish LAN HTTPS.
Private evidence: `diagnostics/pf1007l/https-install/cloud-cost-readonly.json`.

## Expected incremental costs

| Component | Expected recurring cost | Conditions / risk |
| --- | --- | --- |
| Mint LAN HTTPS and monitor | No new subscription | Existing hardware/electricity/network; normal maintenance remains necessary |
| `beestr0.duckdns.org` | $0 under current free offering | Provider availability/policy and account access remain dependencies; no paid domain bought |
| ZeroSSL ACME | $0 under documented free ACME offering | Use the ACME endpoint and EAB, not paid REST certificate products; issuance/abuse limits may reject requests |
| Existing Cloudflare stack | No new resource/plan change from this work | Actual existing plan/bill is not accessible; paid-plan usage may create metered charges |
| Alerts | $0 for local journal/status files | External delivery is not configured; a chosen provider may have limits/costs and requires separate credentials/approval |

ZeroSSL documents automated 90-day ACME certificates free of charge, including
renewal. Its REST/manual products have different limits; those are not required.
Do not assume dashboard/API bulk-management features have identical allowances.
[ZeroSSL ACME](https://zerossl.com/documentation/acme),
[ZeroSSL pricing](https://zerossl.com/pricing/).

DuckDNS documents free DNS and its HTTPS TXT API. No contractual perpetual-free
or account-expiration guarantee was established. Retain account access, monitor
actual DNS and renewal results, and never install an automatic WAN-IP updater over
this deliberately private LAN A record.
[DuckDNS API](https://www.duckdns.org/spec.jsp),
[DuckDNS FAQ](https://www.duckdns.org/faqs.jsp).

## Published Cloudflare Free allowances — conditional on actual plan

These are published reference limits, **not a claim that the account is on Free**.
Shared account traffic, including existing `home-hq`, consumes relevant allowances.

| Product | Published Free allowance relevant here |
| --- | --- |
| Worker dynamic requests | 100,000/day; 10 ms CPU/invocation |
| KV | 100,000 key reads/day; 1,000 writes, deletes and list calls/day each; 1 GB stored |
| SQLite Durable Objects | 100,000 requests/day; 13,000 GB-s duration/day; 5 million row reads/day; 100,000 row writes/day; 5 GB total storage |
| Pages builds/assets | 500 builds/month, one concurrent build, 20,000 files/site; Functions use Workers allowances |

[Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/),
[KV pricing](https://developers.cloudflare.com/kv/platform/pricing/),
[Durable Objects pricing](https://developers.cloudflare.com/durable-objects/platform/pricing/),
[Pages limits](https://developers.cloudflare.com/pages/platform/limits/).

The existing project uses one Pages front door, its private Worker, one KV namespace
and a SQLite MessageRoom binding. It does not need D1, R2, an additional Cloudflare
service, a custom Cloudflare domain, paid certificate management or a new deployment
to support Linux TLS. Existing `home-hq` D1/AlertHub resources are unrelated and
must not be changed. Published Free over-limit behavior generally rejects requests
rather than upgrading automatically; a paid subscription has different metering.
Do not treat an application CPU setting as a universal billing cap.

Current demo APIs are local fixtures; live message data is blocked. A scoped WSS
heartbeat proof briefly uses the existing backend connection, filtering out message
payloads. The five-minute monitor adds about 288 public static HEAD checks/day,
not a new calendar/Todoist poll or cloud write. Actual totals and billing cannot
be estimated precisely without aggregate account usage visibility.

## Controls and alternatives

- No code path orders a paid certificate or upgrades a plan. CA/DNS failures stop
  issuance and alert locally; they do not choose a paid fallback or bypass TLS.
- Exclusive certificate-operation locking, twice-daily renewal checks, and reuse of
  an already issued certificate prevent repeated issuance during installer retries.
- Keep demo-only API policy until separate integration approval. Inspect polling,
  storage growth and WebSocket hibernation before enabling real providers.
- After owner confirmation of the account plan, use the provider's available usage
  and billing notifications. Configuring account-wide alerts/limits is a separate
  approved change; none was made here. No meaningful hard-dollar guarantee can be
  provided while existing billing/usage remains inaccessible.
- If DuckDNS is unsuitable, evaluate Dynu's free hostnames/TXT API and migration of
  this single hostname. Do not change global DNS automatically. deSEC remains an
  option for an owned domain but new free subdomain registration availability needs
  confirmation.
- If ZeroSSL free issuance becomes unavailable, Google Public CA is a no-charge
  alternative requiring account setup and a verified legacy-compatible chain.
  The currently observed GTS comparison chain's GlobalSign cross-sign expires in
  January 2028; revalidate the actual alternative before migration. Let's Encrypt's
  default chain is not a verified solution for this frame's trust store.
- If Cloudflare pricing becomes unacceptable, the same Linux host can be evaluated
  for local static assets/backend operation. That is an architectural change needing
  its own tests and approval, not an automatic migration. Current HTTP fallback
  remains demo-only and is not a safe downgrade for personal information.
