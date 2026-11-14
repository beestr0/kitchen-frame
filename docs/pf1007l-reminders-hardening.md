# Everyday-use hardening plan — no production activation authorized

**Latest priority:** live Apple/iCloud Calendar comes next. Cellular milestone is
closed (`64aa9bb`); further recurrence/background/soak work below is deferred and
not a blocker to calendar development. Follow [the completion plan](pf1007l-completion-plan.md)
and the automated-first/batched hardware workflow in NEXT_SESSION.md.

The verified disposable demonstration is the rollback baseline. Keep PF1007L Test
as the only selected collection throughout hardening. Existing iCloud reminders,
default lists, calendar preparation, weather, Jellyfin and Tailscale remain intact.
This document is a plan, not approval to migrate personal data or reboot the host.

## Verified authentication activation — November 14, 2026

Device-v1 is now deployed for the disposable collection after owner risk acceptance,
physical fingerprint verification and controlled enrollment. Read [actual activation
results](pf1007l-device-auth-activation.md) before repeating any procedure. Continuous
renewal across 32 minutes, app/backend restart, network loss, natural expiry during
an actual 16-minute bridge-only outage, revocation/re-enablement and the owner-
confirmed phone round trip passed. Debugging and privileged test session are off.
Original backup remains private/restorable; 195 automated tests passed.

**Next priority is cellular/Tailscale/background-fetch acceptance**, then actual
recurrence semantics and multi-day stability/restore. Full Linux reboot still needs
its own maintenance-window approval. No production/personal migration is approved.

## Next implementation sequence and evidence gates

1. **Cellular/Tailscale reconnection:** first add a sanitized timestamp/UID test
   worksheet and non-destructive health checks. With the owner operating the iPhone,
   exercise Wi-Fi → cellular → Wi-Fi, disconnected/reconnected Tailscale and offline
   phone edits using new disposable tasks. Record creation, discovery, completion
   and recovery delays at each hop; check unchanged identifiers and no duplicates.
2. **Background synchronization:** separately measure locked-phone and closed-app
   fetch at the existing account settings, including after network transitions.
   Report observed latency rather than promise push delivery. Any Fetch-setting
   change needs owner participation; do not change defaults or other accounts.
3. **Recurrence:** keep frame recurring completion blocked. Create disposable daily,
   weekly and month-end/date-only/timed examples on the phone; capture sanitized
   VTODO revisions before/after phone completion and add compatibility fixtures.
   Enable occurrence completion only after proving one advancement, alarm/exception
   preservation, conflict handling and retry idempotency across timezone/DST cases.
4. **Stability/recovery:** run a multi-day synthetic soak, track bounded memory and
   sanitized failure counters, and rehearse backup restore in isolated storage.
   Verify preserved IDs, completion history and operation reconciliation. Test
   delayed startup dependencies before a separately approved whole-server reboot.

Each phase retains demo-only scope, stale-write blocking, validated TLS and the
current working deployment as baseline. No new feature is activated merely by
writing fixtures or a plan. Physical cellular/background tests cannot be certified
by server-side mocks alone.

## Priority 1 — durable, revocable device enrollment

**Status:** demonstration activation/physical acceptance passed. Preserve the
working device-v1 deployment and original backup. The checklist below remains
reference for a new device or future hardening, not instructions to repeat setup.

1. Inspect the actual Android/WebView and app signing identity, available Keystore
   algorithms and persistence behavior. Do not assume hardware-backed/non-exportable
   keys on this legacy device. Record the risk of its unsupported OS explicitly.
2. Prefer a native device key that signs a server nonce, with the public identity
   enrolled through an owner-controlled physical/local step. If Keystore support is
   inadequate, assess app-private storage of a device-scoped revocable secret as a
   weaker alternative before selecting it; never store provider credentials there.
3. Bind enrollment to this app/device and the exact verified dashboard HTTPS origin.
   Review native navigation, mixed-content settings, JavaScript bridge invocation
   origins and the app-only connection routing. No URL-borne enrollment secrets,
   cloud backend key in the browser, certificate bypass or IP-only authorization.
4. Exchange device proof for short-lived HttpOnly/Secure/SameSite sessions, with
   bounded automatic renewal, explicit revocation and safe credential rotation.
   Retain exact-origin/CSRF/body/method restrictions. Keep enrollment, session and
   CalDAV credentials separate; persist only protected server-side verifiers where
   appropriate. Do not simply make the current bearer cookie permanent.
5. Preserve a controlled rollback to the demo session and original dashboard URL.

Acceptance: device cold start and app restart without Mac/USB or an interactive
password; session expiry/renewal across midnight; revoked/cloned credentials denied;
captured proof cannot be replayed; wrong-origin/bridge/navigation requests rejected;
no secrets in URLs/logs/Git/localStorage; existing weather/HTTPS and frame FPS intact.
The first implementation remains demonstration-only. Personal use requires separate
owner approval even after these tests pass.

## Priority 2 — automatic boot and recovery

Read-only checkpoint inspection confirms Radicale, bridge and HTTPS units are active
and enabled. Tailscale Serve has a background private mapping. This is not evidence
of a successful complete Linux reboot.

Audit dependencies/start ordering, credential mounts, DynamicUser state ownership,
SQLite recovery and backups, network-online behavior, delayed DNS/Tailscale startup,
certificate availability and Serve persistence. Health checks should back off and
report stale data, not restart unrelated services. Avoid startup races and restart
storms; limit corrective actions to this project's own units. Include stale-session
recovery after a boot and persisted pending-operation reconciliation.

First test isolated bridge restarts and simulated startup dependencies. Then schedule
an **owner-approved maintenance-window Linux reboot**, because it also interrupts
Jellyfin and other workloads. Before reboot, confirm backups and a native SSH
recovery path. Acceptance: original HTTPS/weather, private CalDAV, same task IDs and
completion history, valid certificate and frame session recover automatically, with
Mac off and no duplicate writes. No boot auto-launch/default-launcher change is
assumed or authorized; test the kiosk's current launch behavior separately.

## Priority 3 — cellular, Tailscale and native fetch timing

Use newly named synthetic tasks and record each hop's timestamps. With the Mac off,
test home Wi-Fi → cellular → Wi-Fi, Tailscale reconnect, locked phone, Reminders
closed/open, server outage and airplane-mode phone edits. Inspect the current demo
account's Fetch policy before proposing changes; don't alter other accounts or Siri's
default list. Native CalDAV fetch is not an instant push guarantee.

Acceptance: stable UIDs/list membership/completion in both directions, bounded
observed delay, clear stale/offline indicators, no manual duplicate entry, no
credential prompts after ordinary reconnect, no lost phone edits and no frame
completion permitted from stale data. Keep the same private hostname/validated TLS;
no Funnel, router forwarding or public DAV. Measure device/network energy cost as
well as Linux CPU/RAM and frame rate. Review DHCP stability separately; the current
frame IP allowlist still fails closed after address changes. Do not change the
router without specific approval.

## Priority 4 — recurring reminders and calendar semantics

Frame completion of recurring resources remains blocked. In a separate demo list
or uniquely identified fixtures, record actual native iPhone behavior for daily,
weekly, monthly, COUNT/UNTIL, overdue, date-only, timed, timezone/DST, exceptions and
detached occurrences. Compare UID, RECURRENCE-ID, RRULE/RDATE/EXDATE, DTSTART/DUE,
COMPLETED/STATUS and collection revisions before and after completion.

Determine which client owns advancement; don't independently generate occurrences
in multiple places or mark the series complete. Build fixtures from sanitized
examples and implement only semantics proven compatible with the phone. Acceptance:
exactly one occurrence completes, the next appears correctly, exceptions and alarms
survive, due dates don't drift, retries cannot advance twice, and recurrence stays
safe across conflicts/restarts/offline use. If compatibility cannot be established,
retain phone-only recurring completion rather than silently degrade reminders.

## Priority 5 — sustained reliability, observability and restore

Checkpoint retesting exposed one intermittent three-second loopback HTTP fixture
timeout; the unchanged test and all six HTTP boundary tests passed on rerun.
Investigate fixture timing/cleanup under disk load before widening coverage; preserve
production deadlines and security checks.

Run a multi-day synthetic soak including completion during slow/lost responses,
auth revocation, 429/5xx, malformed/partial multistatus, clock changes, cache expiry,
SQLite interruption and constrained resources. Expand tests around ambiguous writes
and client operation-ID reuse across recovery; retain offline write blocking unless
a durable queue is explicitly designed and approved. Add bounded exponential backoff
with jitter and sanitized metrics without task titles/credentials. Define cache,
completion-history, pending-operation and backup retention limits.

Acceptance: stable memory/request counts and approximately 60 FPS, no duplicate or
lost completion, authoritative empty results handled safely, unchanged data avoids
rerender, prolonged outages clearly visible, and tested backup restore preserves
UIDs and idempotency state. Keep logs private and minimal; validate permissions and
encryption/backup exposure rather than equating 0700 with disk encryption.

Only after all selected gates pass should the owner review everyday-use activation
and any proposed personal-list migration. The separate iCloud Calendar integration
remains read-only and requires its own authentication/selection approval.
