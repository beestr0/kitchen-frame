# Private iCloud Calendar proposal — approval required

November 14, 2026 UTC. No Apple account login, calendar discovery, credential entry,
public sharing, live synchronization or deployment was performed. Weather and all
existing Linux/Cloudflare/Android services remain unchanged. Preparation is local.

## Recommendation

Use authenticated **CalDAV on the Linux server**, with a dedicated Apple
app-specific password. Fetch only selected calendars using read-only protocol
operations, normalize on Linux, and serve minimum display JSON directly through
our verified LAN HTTPS listener. **Do not send Apple credentials, raw calendars or
private event snapshots to Cloudflare.** Cloudflare continues serving the shell
and existing weather backend; calendar processing/storage remain local.

For strongest practical account isolation, consider a separate Apple Account that
is privately invited to selected calendars with view-only permissions. Generate
its app-specific password for the collector. This adds account/2FA administration
and needs validation with the chosen shared calendars, but can enforce read-only
permissions at Apple's side rather than relying only on our code. No new account
has been created. A dedicated password on the primary account is simpler, but has
broader consequences if stolen; the owner must explicitly choose that tradeoff.

The dashboard accesses calendars **stored in iCloud**, not arbitrary calendars
visible in Apple Calendar. On My Mac, Google/Exchange calendars, subscribed feeds
and delegated/shared collections may have different availability. Approved
metadata discovery will determine what this account can actually read.

## Authentication options and evidence

Apple documents app-specific passwords for third-party mail/contact/calendar
apps, requiring two-factor authentication. Each can be individually revoked;
changing/resetting the main Apple Account password revokes all app-specific
passwords. This collector needs the account email and a newly generated dedicated
app-specific password, never the main password or a two-factor code.
[Apple app-specific password guidance](https://support.apple.com/en-us/102654)

Apple also supports Apple Account authorization for participating third-party apps.
I have not verified an openly documented enrollment/token flow this custom Linux
service can use. Do not substitute ordinary Sign in with Apple identity login for
calendar authorization, scrape a browser session, automate 2FA or extract native
Calendar account tokens. Reevaluate a documented supported integration if one
becomes available; it is not an assumed dependency of this proposal.
[Apple third-party authorization guidance](https://support.apple.com/en-us/121539)

CalDAV is a standardized calendar access protocol. It can read **and write**; our
code must limit operations to discovery/read REPORTs. An app-specific password
is **not** a user-defined read-only/per-calendar API scope. Selection limits what
our service requests, not what a compromised primary-account credential could do.
A private view-only share to a separate reader account provides a stronger boundary.
[CalDAV standard](https://www.rfc-editor.org/rfc/rfc4791),
[Apple calendar sharing](https://support.apple.com/en-gb/guide/icloud/mm6b1a9479/icloud)

The initial endpoint is `https://caldav.icloud.com/`; discovery obtains principal,
calendar home and partition endpoints rather than guessing account IDs or a pNN
server. Apple does not provide a full public service contract here comparable to
Google's Calendar API. Standards behavior and third-party access are supported in
practice, but endpoint/account compatibility must be verified after approval.
No calls were made to that endpoint during this investigation.

## Comparison

| Aspect | Private CalDAV, Linux-local | Public read-only iCalendar link |
| --- | --- | --- |
| Calendar publishing | None; calendars stay private | Enables access to anyone possessing the URL |
| Authentication | Account + revocable app password, verified TLS | Feed URL itself is a bearer secret; no account authentication |
| Read-only guarantee | Collector forbids writes; primary credential is broader. View-only reader account is stronger | Feed itself is read-only |
| Secret compromise | Primary app password can have broader account/service scope | Leaked URL exposes its published calendar; already downloaded copies cannot be recalled |
| Selection | Stable collection identifiers and selected calendars only | One configured link per published calendar |
| Reliability | Discovery/auth/partition changes, revocation and throttling need handling | Simpler fetch/parser; publishing changes and provider outages still need handling |
| Maintenance | More initial work; credential replacement and collection reconciliation | Lower code complexity but privacy tradeoff contradicts owner preference |
| Data residence in proposed design | Apple, Linux cache and authorized frame only | Existing feed implementation would ordinarily also store data in cloud KV |
| Cost | No paid connector/subscription proposed; separate reader account eligibility/setup remains user-controlled | No connector fee, but not recommended for this project |

Private does not automatically mean a narrower credential. We will not enable
public sharing as a shortcut or fall back to a public link on authentication failure.

## Prepared code and remaining implementation

[Inactive preparation](../deploy/icloud-calendar/README.md) contains:

- Strict read-only CalDAV transport/discovery/VEVENT query primitives. Only
  PROPFIND and REPORT can reach the transport; no PUT, POST, DELETE, PROPPATCH,
  MKCALENDAR, MOVE, COPY or scheduling operations.
- Normal system CA and hostname checks, TLS 1.2 minimum, bounded responses/window,
  explicit Apple CalDAV endpoint and redirect restrictions, no proxy inheritance,
  XML entity/DTD rejection, and fixed errors without account/event/header dumps.
- A hidden, atomic, non-overwriting Linux-only credential collector, not run.
- Disabled configuration with no calendars selected and no cloud upload.
- Ten offline tests using invented credentials/XML and mocked network calls.

This is **not installed or a complete production sync service**. After method
approval, complete the isolated collector, event shaping, cache and delivery gates
below. No live client performance claim is made before physical testing.

## Proposed runtime and synchronization

A dedicated unprivileged oneshot service and ten-minute systemd timer use an
isolated project directory under `/opt/pf1007l-calendar`. No always-running sync
framework or Mac dependency. Credentials live under `/etc/pf1007l-calendar/`
(root 0700; files 0600), delivered only to the collector with systemd LoadCredential.
The HTTPS proxy must never load the Apple password. Private state belongs in its
own 0700 `/var/lib/pf1007l-calendar/` directory; no generic project/Git/log backup.
Root file permissions are not disk encryption; encrypted system backups/disk
protection require a separate assessment. No such protection is assumed.

First discover calendar names, collection IDs and colors using PROPFIND, **without
fetching events**. Show the list only in the owner's secure SSH Terminal, not chat,
CI artifacts or screenshots. User chooses calendars and optional display aliases/
colors. Store stable IDs, not indices/name-only matches; new calendars default to
unselected. A renamed collection keeps its identity/color. Removal/unselection
must promptly purge it from published snapshots, not keep showing a stale copy.

Then query only chosen VEVENT collections over a rolling initial window of 31 days
past and 180 days future. Bound per-response bytes, event counts and total run time.
Use collection ETags/ctag or sync tokens where advertised, falling back to bounded
queries with a full periodic reconciliation. Sliding the window needs a refresh
even when collection tags are unchanged, so future recurrences enter the window.
Do not assume iCloud implements every optional synchronization report.
[WebDAV collection synchronization](https://www.rfc-editor.org/rfc/rfc6578)

Reuse the tested `ical.js` normalization semantics in a local Node bundle, or prove
an equivalent parser with the same fixtures. Preserve all-day exclusive end dates,
TZID/VTIMEZONE, floating times in Indianapolis, recurrence exceptions, cancellations
and DST. Apply per-calendar parsing before merging. Output only title/start/end,
all-day flag, local stable calendar ID/color and opaque event identity; omit notes,
attendees, conference URLs and location by default. Never return raw ICS, DAV paths,
Apple account IDs, authentication headers or backend filesystem paths to the frame.

Keep per-calendar last-good snapshots, and atomically publish a combined JSON
snapshot only after validation. Partial/malformed/multistatus errors must not be
mistaken for authoritative event deletion. A successful empty result should remove
old events; a failed request should retain them with that calendar marked stale.
Record last attempt/success separately and expose a clear last-updated/stale badge.
Do not rewrite unchanged data. Back off transient failures with jitter; stop repeated
authentication attempts on 401/403 and surface a local renewal/authentication alert.
Calendar failure must not restart HTTPS, weather or unrelated services.

Local event deletion means cache reconciliation only: there must be no API capable
of deleting, editing, responding to invitations or creating events on Apple.

## HTTPS delivery, frontend isolation and colors

Keep this private pipeline entirely out of Cloudflare Workers/KV. Extend only the
Linux HTTPS proxy to read the bounded sanitized snapshot through a local Unix
socket or protected file made available to that unit. Permit only the exact approved
calendar GET route. Do not forward a calendar query string to Apple, implement
account configuration on the frame or expose a DAV pass-through. HTTP 8788 stays
synthetic, regardless of live account state.

Before private event display, review stronger kiosk authorization and native
navigation/JavaScript bridge restrictions. Current IP/Host/Origin checks are not
cryptographic client authentication. Apple credentials will stay only on Linux.
A separate short-lived HttpOnly/Secure kiosk session would require storing an
opaque **dashboard** session on the frame, not an Apple credential; this distinction
needs explicit review. If the prohibition includes every kind of frame credential,
that limits stronger application authentication and must be resolved before activation.
No authentication/cookie/Android change is being made now.

Add calendar-specific source state rather than switching the global `ui.demo` off;
otherwise enabling the calendar could activate Todoist/photos/messages accidentally.
Tasks remain synthetic, weather remains live. Preserve Home/Week/Month layouts;
fetch small JSON at the existing five-minute display polling cadence. Sync stays
on Linux every ten minutes. Avoid event parsing and recurrence expansion on Android.

Existing CSS uses four repeating calendar color slots. For more than four calendars,
prepare validated per-calendar colors/tints with stable mapping and contrast in both
themes; do not claim today's modulo-four palette gives every calendar a distinct
color. Metadata determines safe selected colors; keep existing geometry unchanged.
Use the established browser event fields so rendering cost remains bounded. Mark
navigation outside the cached date window honestly rather than implying no events.
Review whether private event data may persist in Android localStorage: it improves
offline behavior but is readable on an unlocked/root-accessible device. Minimize
retention and offer a targeted clear-cache procedure; never clear HomeHQ data.

## Secure account and credential-entry procedure — after approval only

1. Owner approves private CalDAV and chooses primary-account password versus the
   optional dedicated privately invited, view-only reader account.
2. In the owner's normal browser, visit `account.apple.com`, sign in privately,
   verify 2FA, and create one app-specific password labeled `PF1007L Calendar`.
   Never enable Public Calendar. Never provide the primary password/2FA code here.
3. After local code review and explicit storage/discovery authorization, open native
   Terminal SSH to `hub@10.157.1.115`. Owner handles any SSH/sudo authentication there.
4. Stage the approved credential helper on Linux; verify its hash/ownership. Run it
   through that private TTY with explicit storage opt-in. Hidden prompts collect the
   account email and app-specific password. No shell arguments, environment exports,
   tee, terminal recording, debug tracing, paste-to-chat, or credentials on the Mac.
   Disable terminal input broadcasting/session recording; clear any clipboard used.
5. Helper writes only root-private Linux `apple.json` and does **no network access**.
   It refuses to overwrite existing credentials. Credential replacement/revocation
   is an explicit separate action, preserving other services and existing progress.
6. Run approved metadata-only discovery and select names/IDs/colors locally. Calendar
   names and IDs are private too; return only non-sensitive counts/status to chat.
7. With selected scope confirmed, approve a first read-only event fetch and local
   cache. Verify one calendar first, then expand. Only after security and acceptance
   tests enable the timer and replace demonstration calendar data on HTTPS.

Do not enter credentials yet: neither this helper nor any Terminal prompt has been
opened in this turn. The selected account method is awaiting review.

## Acceptance, recovery and rollback

Required tests before live activation: recorded request methods prove no writes;
reject redirects outside the allowlist/wrong TLS/untrusted chains; discovery does
not read events; only selected collections are queried; immutable stable selection;
multiple colors; all-day/recurrence/DST fixtures; per-calendar partial outage and
empty-result behavior; stale snapshot survives restart; unchanged snapshot avoids
rerender; no private response on HTTP/Cloudflare or to an unauthorized client.
Test Home/Week/Month/themes on the physical frame using safe fixture events before
showing real titles. For personal tests, redact screenshots/logs and preserve
59–60 FPS, existing HTTPS, live weather, HomeHQ and all other services.

401/403: suspend retries, keep stale snapshot with warning, generate a local alert,
and let owner replace only this app password. Never retry the primary password or
switch to public sharing. Provider/DNS outage: retain selected last-good events,
show age and resume with bounded backoff. Monitoring/alert delivery is local unless
an external mechanism is separately authorized; do not leak event titles in alerts.

Rollback: stop only the proposed calendar timer/service; disable only the HTTPS
calendar source; return calendar UI to demo; revoke the dedicated Apple app password
in the browser. Remove private snapshots/selected metadata only with owner approval.
Keep HTTPS certificates, live weather, HTTP fallback, HomeHQ/Jellyfin/Tailscale and
all Cloudflare resources. No router forwarding, public hostname publishing, paid
connector or new subscription is required by this proposed architecture.
