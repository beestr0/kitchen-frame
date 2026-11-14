# Apple Reminders assessment and inactive preparation

Prepared November 14, 2026. Apple Reminders replaces Todoist in the proposed task
roadmap. No personal lists, defaults, Apple accounts, services or deployments changed.
The separate [private iCloud Calendar plan](pf1007l-private-icloud-plan.md) still
applies to actual VEVENT calendar events and remains read-only and inactive.

## Recommendation and limits

Pilot **Radicale on Mint, storing VTODO lists**, added as a CalDAV account in the
native iPhone Reminders app. Use a private Tailscale HTTPS endpoint, authentication
and collection authorization. The dashboard talks to a restricted Linux task adapter,
not directly to DAV. Mint is the source of truth for these new lists. Neither the
MacBook nor an Apple app password is required for this task-account architecture.

This is genuine two-way access to the same task store, not a periodic copy of iCloud
Reminders. Existing upgraded iCloud lists stay in iCloud and will not appear through
this server unless separately migrated. A private CalDAV account does not provide
all of modern iCloud Reminders. If preserving existing iCloud lists and every Apple
feature is mandatory, no supported Linux-only solution has been established.

Apple explicitly supports adding CalDAV accounts to Reminders, but documentation
does not establish the exact iPhone/Radicale/recurrence combination. Recommend a
demo-list pilot rather than promise all required behaviors before device testing.
Get the iPhone iOS version before that pilot; menu names and support can vary.
[Apple account support](https://support.apple.com/en-euro/guide/iphone/iph8739025dd/26/ios/26),
[Radicale capabilities](https://radicale.org/v3.html).

| Approach | Existing iCloud lists | Mac independent | Assessment |
| --- | --- | --- | --- |
| Mint Radicale + native CalDAV Reminders | Separate lists; migration optional | Yes | Recommended pilot; small, free/open source; Apple feature limits |
| EventKit app on Mac | Authorized existing reminder lists | No, unless another supported Apple host runs bridge | Best direct access to iCloud data, but Mac must be awake, connected and running the app for propagation |
| EventKit app on iPhone | Authorized existing reminder lists | Yes | Supported API, but custom app distribution/maintenance and background scheduling prevent a promise of continuous low-latency sync |
| Nextcloud Tasks + CalDAV | Separate lists | Yes | Same basic account model; more components/database/maintenance than Radicale; no benefit sufficient to justify installing it here |
| Shortcuts/manual export | Can access some reminder data | Sometimes | Useful for a supervised one-time migration; not a dependable continuous two-way conflict-safe sync engine |

EventKit runs in Apple applications, not a Linux service. It supports reminder
retrieval and writes after permission; it is not a hosted iCloud REST API. A bridge
would need full Reminders consent, stable identity reconciliation, reconnect handling,
and a secure command channel. iOS decides when background work runs; it is not an
always-running daemon. A dedicated always-on Apple host is another option, but
requires hardware and does not meet the existing Linux-only preference.
[EventKit](https://developer.apple.com/documentation/eventkit),
[access permissions](https://developer.apple.com/documentation/eventkit/accessing-the-event-store),
[iOS background execution](https://developer.apple.com/documentation/backgroundtasks/choosing-background-strategies-for-your-app).

Radicale requires no software subscription. Reuse existing Tailscale only after
checking current account eligibility and policy; no upgrade is authorized. Hosting,
backups and power still require maintenance. Nextcloud also has a self-hosted free
option; it is an alternative server, not a bridge to upgraded iCloud Reminders.
[Nextcloud Tasks project](https://github.com/nextcloud/tasks),
[Tailscale plans](https://tailscale.com/pricing).

## Siri, defaults and feature compatibility

Apple documents that Default List controls reminders created outside a particular
list, including Siri. Once a pilot account/list exists, test a uniquely named list
using “Add test paper to my PF1007L Test list.” Confirm the actual account and list
in Reminders, not just Siri's acknowledgement. Named-list recognition, device lock,
Siri settings and the installed iOS version need physical verification. Do not
change the default yet. After approval, Settings → Apps → Reminders → Default List
should let the owner select the new account's list; if it is absent, stop the pilot.
[Apple Default List guidance](https://support.apple.com/en-ie/guide/iphone/f898416824ef/ios).

Basic text, completion, multiple lists and date/time fields are the pilot targets.
VTODO supports STATUS, COMPLETED, DUE, recurrence and alarms, but server support
does not guarantee the iPhone round-trips each feature. Validate date-only, timed,
floating, timezone, DST and recurring reminders on both clients. Determine whether
recurring completion advances the original task, creates another occurrence, or
uses detached instances. Do not invent the next occurrence from a simplistic rule.
[iCalendar VTODO specification](https://www.rfc-editor.org/rfc/rfc5545).

Treat tags/Smart Lists, subtasks, attachments, flags, custom icons/colors, grocery
categorization, shared-list assignment/collaboration, location and messaging alerts,
and newer Apple intelligence/urgent features as unavailable or unverified for the
third-party account. Do not promise parity. Some alarms or priority values may
round-trip, but require individual testing. Apple notes that all documented Reminders
features require updated iCloud reminders and some are unavailable for other accounts.
The frame initially displays title, list, due and completion only; alarms remain on
the iPhone. No notes, attachments, location or contacts are delivered to the frame.

## Home and away networking — proposed, not configured

1. Before changing anything, inspect Mint's existing Tailscale status, Serve/Funnel
   configuration, listeners, firewall and tailnet ACL/grants read-only. Last SSH
   health attempt failed authentication; current runtime and available ports are
   not verified. Never reset Serve or flush firewall rules to make room.
2. Bind an isolated authenticated Radicale instance to loopback on a verified free
   port. Disable arbitrary access and unnecessary web/admin features; use hashed
   passwords and explicit collection rights. A no-auth quickstart is unsuitable.
3. Add a dedicated **Tailscale Serve** HTTPS listener using the Mint tailnet DNS
   name, preserving existing Serve routes/listeners. Serve is tailnet-only; do not
   use Funnel, router forwarding or public DAV. If an existing listener conflicts,
   choose an approved separate supported HTTPS port and validate iOS discovery.
4. Permit only the approved iPhone identity/device to the task listener in tailnet
   policy. Retain DAV authentication as an additional boundary. Provision a dedicated
   local task-account password through private native Terminal entry after approval,
   never chat/URLs/logs. Backend service credentials remain root-private and are
   passed only to their dedicated service, never Cloudflare or Android.
5. Install/sign into Tailscale on the iPhone only after authorization, if not already
   present. Use the same verified `https://<mint-host>.<tailnet>.ts.net` endpoint at
   home and away; no subnet router or exit node is needed. Keep Tailscale connected
   on Wi-Fi and cellular; configure VPN On Demand after reviewing other VPN use.
   A disabled VPN, expired device authorization, sleeping server or internet outage
   delays synchronization. Offline changes on iPhone upload when connectivity returns.
6. Serve manages its HTTPS certificates. Tailnet HTTPS names enter public certificate
   transparency logs: use a non-sensitive hostname. Do not accept self-signed
   certificate warnings or disable TLS verification. Verify discovery, redirects,
   principal paths and authentication via the final endpoint.

[Serve privacy and access control](https://tailscale.com/docs/features/tailscale-serve),
[HTTPS certificates](https://tailscale.com/docs/how-to/set-up-https-certificates),
[iPhone VPN On Demand](https://tailscale.com/docs/features/client/ios-vpn-on-demand).

The frame keeps its existing LAN HTTPS dashboard URL and does not need a new VPN.
Only a narrow authenticated task API is added to HTTPS after approval. Existing HTTP
8788 remains synthetic; task data/credentials never traverse Cloudflare. Jellyfin,
Tailscale's existing routes, certificate renewal, live weather, HomeHQ and launchers
remain untouched. Tailnet membership does not replace application authentication
on the LAN frame endpoint.

## Dashboard inspection and proposed changes

- `src/lib/state.svelte.js` currently loads `/api/lists/todo`, caches in localStorage,
  groups Todoist sections and removes a completed row optimistically. Its global
  demo flag also affects other integrations. Introduce an independent task source
  with disabled/demo/private states; do not switch the global demo flag to enable it.
- `views/List.svelte` and `components/TaskRow.svelte` can reuse their layouts, mapping
  selected task lists to groups. Replace Todoist-specific labels/error handling and
  route creation/completion to the task adapter only. Recipe-to-grocery writes also
  use Todoist today: leave them disabled or explicitly map a selected Reminders list
  after approval. Never silently redirect a grocery write or retain a hidden Todoist
  fallback. The old Worker module stays dormant until a later reviewed cleanup.
- `views/Home.svelte`, `Week.svelte`, `Month.svelte` and `EventRow.svelte` use calendar
  event shapes. Merge task due **markers** at display time, not by creating Apple
  calendar events. Undated active tasks appear on Tasks; dated active reminders appear
  on their due day in Week/Month and relevant Home agenda. Due markers need a checkbox
  and “Due” labels, not fictional appointment durations. Handle zero-duration timed
  markers in day filtering and avoid “Now until” event rendering. Use namespaced
  identity keys; don't deduplicate a task against an actual event by title.
- The current task poll only runs on Home/Tasks. A new bounded task poll must also
  run when Calendar is visible, with one in-flight request and an immediate refresh
  on wake/tab changes. Target 30–60 seconds initially; iOS provider refresh is
  independently scheduled, so promise eventual sync, not instant push delivery.
- No recurrence expansion or ICS parsing on Android. Linux supplies bounded minimal
  JSON, stable IDs and revisions. Skip unchanged state updates and run only active
  views; no new animation or streaming connection. Physical FPS remains an acceptance
  check, not something offline tests prove.

## Adapter, writes, caching and failure contract

Use separate unprivileged task service/state under project-specific `/opt`, `/etc`
and `/var/lib` paths. The iCloud Calendar read-only transport must not gain PUT or
other writes. Task credentials authorize only dedicated task collections, not Apple's
calendar account. Radicale owns storage; adapter reads/writes through DAV, never
edits Radicale's backing files. Use proper locking/ETags and service isolation.

Discovery selects VTODO collections explicitly. Persist canonical collection IDs,
not names/indices; new lists default unselected. Internally identify objects by
collection, UID and recurrence ID with canonical href/ETag mapping. Expose opaque
local IDs/revisions, never paths, account identifiers or DAV credentials. Same UID
in different lists is distinct. Reconcile cross-list moves using a complete selected
collection scan before atomic publication; never guess that equal titles are copies.

Proposed GET `/api/reminders` returns minimal selected-list metadata, active tasks,
per-list last attempt/success and stale status. Proposed POST
`/api/reminders/<opaque-id>/complete` takes expected revision and a persisted
idempotency key, not DAV URLs. Resolve identity server-side, GET latest resource,
verify selected collection, reject obsolete revision with 409, and use conditional
PUT with `If-Match`. Change only completion fields; preserve unknown properties,
alarms, due date and recurrence. A 412 triggers refresh/conflict display, never an
unconditional overwrite. A retry after an ambiguous response checks the resource
and idempotency record before writing. Repeated requests must not complete the next
recurrence. Recurring writes remain blocked until occurrence semantics are proven.
[CalDAV conditional updates](https://www.rfc-editor.org/rfc/rfc4791).

Frame write authentication must be stronger than IP allowlisting: reviewed revocable
kiosk session, Secure/HttpOnly cookie, CSRF protection, strict same-origin checks,
navigation/bridge review, method/body allowlists, request-size and rate limits. No
general DAV tunnel, remote paths, creation/deletion or arbitrary edits in this first
adapter. If frame task creation is desired, add a separately approved narrow route
and explicit destination list. Phone creation/editing works through its native DAV
account. No account setup on the legacy WebView.

Use bounded per-list last-good snapshots with atomic combined publication, sync
tokens where supported and periodic full reconciliation. Query undated tasks too;
a due-date window alone loses them. Keep completed identities/tombstones long enough
to reconcile safely; completion history and retention policy need owner approval.
Successful empty results remove old active items, but partial/malformed/error results
must not look like deletions. Unselection purges display data immediately. An outage
retains selected last-good data with age; 401/403 suspends retries and alerts locally;
429/5xx back off with jitter. Logs contain fixed codes/counts, no titles or raw ICS.

Disable completion while offline rather than maintain an untested browser mutation
queue. Display pending until acknowledged; on timeout refresh and show uncertain
status, rather than silently roll back or claim success. Persist server idempotency
outcomes across restart. Do not allow older in-flight snapshots to resurrect pending
or confirmed completions. Cross-device stale edits require conflict reconciliation,
not a last-writer-wins blind PUT.

Use `Cache-Control: no-store` for private responses. Prefer memory-only frame state;
existing generic localStorage caching must not receive private task payloads until
retention is explicitly approved. Linux snapshots/backups stay private with bounded
retention, permissions and restore testing; file permissions are not encryption.
Tasks failure must not restart HTTPS/weather or other services.

## Isolated preparation and remaining work

[Demo and commands](../deploy/reminders/README.md) provide an in-memory two-list
test, a pure display partitioner, last-good state reducer, and non-recurring VTODO
completion patcher with preservation tests. No runtime wiring, listeners, scheduled
jobs, packages, credentials or live requests were added. The simulator's revisions
model conflicts; it is not a real DAV transport, durable cache or idempotency ledger.

Still required after architecture approval: authenticated local Radicale pilot,
discovery/transport with strict TLS and allowed destinations, normalized due date
parsing (including VTIMEZONE/floating/DST), snapshot validation, bounded recurrence
expansion, proven recurring completion, conditional write/idempotency integration,
per-list partial failures, endpoint security and actual UI wiring. Test real DAV
412s, malformed multistatus, deletes/moves, restarts and timeout-after-success.

Local validation: all **49 dashboard tests passed**, including six new Reminders
tests; the offline demonstration ran successfully; `npm run build:desk` passed;
`git diff --check` passed. No real iPhone, DAV server or physical FPS test was run.
The original production client asset hashes remain unchanged by this inactive code.

## iPhone pilot instructions — only after architecture/setup approval

1. Verify the Mint listener is tailnet-only and authenticated: unauthorized tailnet
   device denied; missing/wrong DAV password denied; LAN/public direct access denied.
   No public exposure or changes to existing dashboard listeners.
2. On iPhone, connect Tailscale and verify HTTPS with no certificate warning. Under
   Settings → Apps → Reminders → Reminders Accounts → Add Account → Other → Add
   CalDAV Account, use the approved server hostname, dedicated local username/password
   and SSL/port settings. Supply a full account URL in advanced settings if discovery
   requires it. Turn on Reminders for that account. These are local DAV credentials,
   not Apple Account credentials. Do not alter iCloud settings or the default list.
3. Create only a new uniquely named `PF1007L Test` VTODO list. Test with invented
   text: undated, date-only, timed and daily recurring reminders in two test lists.
   Use named-list Siri first. Verify its target. Add/rename/edit/complete on iPhone,
   confirm server and demo adapter snapshot; complete on frame fixture UI, confirm
   phone, then reopen on phone. Check both list membership and completion history.
4. Once approved, select the new test list under Default List and test an unqualified
   Siri reminder. Record the previous default privately for rollback. Never change
   it on the owner's behalf before that explicit approval.
5. Repeat on cellular with Wi-Fi disabled, while MacBook is off. Lock iPhone, allow
   background refresh, measure observed sync delays; reopen Reminders to distinguish
   foreground success from background reliability. Test Tailscale disconnect/reconnect,
   server outage, airplane-mode edits, expired auth and concurrent phone/frame edits.
6. Verify due-date edits move between Tasks/Calendar without duplicates, date-only
   dates stay fixed, DST/timezone changes behave, and recurrent completion advances
   exactly once. If recurrence fails, keep that feature gated and do not migrate
   recurring personal reminders. Test Home/Week/Month, themes, restart and frame FPS
   with synthetic data. Redact personal screenshots/logs in any later acceptance.

## Reversible migration — no migration authorized

Keep existing iCloud lists unchanged during the pilot. Native cross-account moves
and exports can omit unsupported fields, so do not promise a lossless bulk move.
After separate approval, inventory counts and feature types in a private local
session, create a recoverable backup using a supported Apple app, and validate the
restore process first. Trial-copy a few simple items into a new list, record source
and destination identity mappings, compare titles/due/recurrence/completion/notes,
and keep originals. If supported copying is unavailable, use an owner-approved
EventKit migration utility on the Mac once, with a dry run and no deletes; this does
not require the Mac for ongoing sync. Do not scrape native databases.

Copies and originals are independent; there is no supported automatic mirroring
between the accounts in this design. Select only destination lists on the dashboard
and agree on one authoritative list per migrated task set, avoiding ongoing edits
to both copies. Changing the Siri default later affects new reminders only. Leave
complex/shared/Apple-only reminders in iCloud unless their limitations are accepted.
Never delete/archive originals or mark them completed to conceal duplicates without
separate authorization. Any later source cleanup requires verified backups and
explicit owner approval.

Rollback: disable only task adapter/UI source; stop only the new task service and
listener mapping; restore the old default only if it had been changed with approval.
Removing the new iPhone account stops displaying its reminders; preserve its server
data and backups. New tasks/edits made after migration need a reviewed reverse-copy
before retirement. Revoke only dedicated task credentials; do not touch iCloud,
HomeHQ, calendar collector, weather, Jellyfin, Tailscale connectivity or dashboard TLS.

Next decision: approve this **demo-list-only Radicale/Tailscale pilot**, or retain
existing iCloud lists and accept an always-on Apple EventKit host. Credentials,
account addition/default changes, personal migration and live frame activation
remain distinct approval gates.
