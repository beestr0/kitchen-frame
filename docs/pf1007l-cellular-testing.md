# Cellular/Tailscale demo testing — November 14, 2026

**Cellular/Tailscale milestone closed: physical workflow checks passed.**
Exact background timing and long-term soak are recorded limitations, not blockers
to further feature development. The owner accepted this milestone as complete.
Baseline source checkpoint `3eed5dd`, disposable PF1007L Test only. No personal lists,
defaults, Fetch settings, production integration or service configuration changed.
No Linux/Mac reboot, service restart, public exposure or Funnel activation occurred.

## Final result and timing

Owner-reported times below are local EST (UTC−05:00) on November 14. Server samples
use UTC. “By” means first positive sampled response completion, not exact network
arrival. Reminders polls and DAV request durations vary; no fixed latency is assumed.

| Operation | Owner action | First server observation | Bridge / physical result |
| --- | --- | --- | --- |
| Wi-Fi baseline | Save `Cellular pilot WiFi 01` 16:39:15 | Present by 16:39:25.959808 (10.960 s); due today by 16:39:36.670729 | Bridge by 16:39:53.066327 (38.066 s); owner confirmed frame Tasks/incomplete/today |
| Switch to cellular | Wi-Fi off approx. 16:42:15; Tailscale stayed connected | — | Owner confirmed cellular transition |
| Cellular creation | Save `Cellular pilot Cellular 01` 16:43:40 | Present by 16:43:52.463212 (12.463 s), undated/incomplete | Bridge by 16:44:00.664172 (20.664 s); frame observed 16:44:35 (55 s) |
| Siri over cellular | Approx. 16:48:45, actual title `Cellular pilot series 01` | Exact-title observer excludes Siri transcription variant; no direct UID/latency claim | Owner confirmed correct demo list and frame at 16:51:04 (approx. 139 s observation bound) |
| Cellular return completion | Frame C1 tap 16:52:35 | Same UID completed by 16:52:49.163302 (14.163 s); bridge likewise | Owner saw phone completed 16:54:15: **100 s** observed return delay |
| Offline creation | Tailscale disconnected 16:55:30; save `Cellular pilot Reconnect 01` 16:56:20 | Absent while disconnected; original local item retained | Existing tasks/states intact |
| Tailscale recovery | Reconnected approx. 16:57:10 | One R1 resource by 16:57:57.970305 (approx. **48 s**) | Bridge same sample; owner confirmed frame incomplete |
| Create then lock | Save `Cellular pilot Locked 01` 17:00:05; lock 17:00:10 | Present by 17:00:32.372153 (27.372 s) | Bridge by 17:00:50.366102 (45.366 s); upload may have started before lock |
| Complete while phone locked | Frame L1 tap approx. 17:02:15 | Same UID completed by 17:02:27.882060 (approx. 13 s); bridge likewise | Phone unlocked approx. 17:03:10, already completed: approx. **55 s** observation bound |
| Return Wi-Fi | Home Wi-Fi restored 17:04:40 | Four observer-tracked identities/status stable through 17:06:32.669518 | Owner confirmed all five once, expected states, Tailscale connected, no account warning |

The proposed wait until 17:05:15 was **not performed**: actual unlock was 17:03:10.
No inference about exact locked-background download time follows from completion
seen upon unlock/open; this could have downloaded while locked or at unlock. No
instant-push guarantee, three-minute post-completion lock test or battery SLA claimed.
Mac stayed on for diagnostics; Mac-off physical acceptance was not performed.

### Reconciliation

Owner confirmed each reminder appears once after returning to Wi-Fi:

| Reminder | Final state |
| --- | --- |
| Cellular pilot WiFi 01 | Incomplete, due 2026-11-14, date-only |
| Cellular pilot Cellular 01 | Completed, undated |
| Cellular pilot series 01 | Incomplete, undated |
| Cellular pilot Reconnect 01 | Incomplete, undated |
| Cellular pilot Locked 01 | Completed, undated |

Four directly observed DAV resources retained stable hashed UIDs and bridge opaque
IDs, with exactly one match each. C1/L1 completion persisted; W1/R1 stayed incomplete.
Siri variant has physical phone/frame confirmation but no direct server identity
observation because of the observer's intentional exact-title privacy filter.
Initial W1 was first undated then dated on the same UID; no duplicate was created.
No fixture was deleted. Separate Calendar-view placement was not explicitly checked
in this run; earlier physical Calendar acceptance remains the evidence for that view.

## Authentication, health and privacy checks

- Initial session issuance 1794692008.5152674 advanced automatically to
  1794692760.8004494 (21:46:00.800449Z), then 1794693502.5073633
  (21:58:22.507363Z); each lifetime 900 seconds. One authorized device, sessions
  unexpired and bridge stale=false in samples. No manual renewal/reprovisioning.
- Six existing Linux services remained active, HTTPS upstream errors zero, private
  Serve root → loopback5238 unchanged and tailnet-only. Jellyfin, weather/dashboard
  and Tailscale preserved. No frame app update/restart/debugging change was made;
  HomeHQ was not touched. No new FPS measurement was needed or performed.
- Validated private HTTPS PROPFIND of the demo collection without credentials
  returned **401**; bridge snapshot without credentials returned **403**. Private
  root GET returned a normal **302** web redirect, not evidence of collection access.
  No keys/cookies were extracted to test these denials.
- Two observer tests passed: exact synthetic-title/UID-hash projection privacy and
  native root-TTY authorization before any read. The deployed dashboard/core was
  unchanged, so the full 195-test suite was not repeated for this diagnostic-only run.
- Read-only observer reads protected aggregate session metadata/cache and REPORTs
  only `/pf1007l-demo/pf1007l-test/`. It never writes tasks/services/auth configuration.
  Credentials stay in process memory, raw UIDs/headers/proofs/cookies are not output.

## Observer lifecycle and evidence

Native observer was authorized privately, checksum pinned to
`be653bb0d0a485fb5406cffc9e2e442f093ba27d4f2e3062192abc17bcafd31b`.
Only five exact original synthetic labels are permitted; do not broaden it to
unrelated titles. A future reviewed revision can explicitly add the accepted Siri
alias with fixtures; it cannot retroactively reconstruct unobserved arrival times.

Private report on Mint (0600, outside Git):
`/home/hub/pf1007l-autonomous-tests.xc2ZzG/20261114-cellular-be653bb0.jsonl`.
Sample observedUnix is read-start, observedUTC is REPORT-response completion;
bridge lastSuccess is its own cache refresh time. Do not confuse them. Native
observer started around 21:37 UTC, is bounded to one hour and otherwise remains
read-only until it exits. Owner may press Ctrl+C in that observer Terminal to stop
it earlier; no service depends on it. Closing/stopping it does not affect runtime.
The old deployment controller remains finished; do not reuse its queue.

## Nonblocking limitations and separate reliability work

1. Repeat controlled locked/closed-app background-fetch timing over longer windows,
   record existing Fetch policy without changing it, distinguish foreground refresh
   from background fetch using sanitized per-client evidence if available. Keep
   physical proof requirements; server mocks cannot prove iOS scheduling.
2. Run a multi-day disposable reconnect soak, varied outage durations, offline
   phone edits and operation conflict reconciliation. Expand offline/recovery
   fixtures; sampled success here does not rule out all future data-loss conditions.
3. Add the Siri alias to a reviewed observer for direct resource reconciliation,
   repeat Calendar visibility and independently test with Mac off.
4. Proceed to real disposable recurrence fixtures afterward; frame recurring
   completion remains blocked. Isolated restore testing precedes any separately
   approved whole-server reboot. Everyday use/personal migration remain unapproved.
