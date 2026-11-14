# Path to completion — Apple Calendar first

Owner priority update November 14, 2026: close existing work cleanly, then live
Apple/iCloud Calendar takes precedence over further Reminders research, optional
soaks and other integrations. Await the owner's detailed calendar requirements;
implementation preparation does not authorize Apple-account access or activation.

| Area | Actual current status | Essential next work | Validation approach |
| --- | --- | --- | --- |
| Dashboard/kiosk/HTTPS/weather/themes | Working and physically verified, approximately 60 FPS | Preserve as baseline | Existing regression tests; hardware only for relevant UI/native changes |
| Apple Reminders/Siri | Real two-way Radicale demo; cellular/offline/reconnect verified | Separate approval before using personal/non-demo lists; preserve third-party Apple feature limits | Fixture/conflict tests first; no repeat unchanged physical checks |
| Persistent device auth | Activated, renewable/revocable; software-backed rooted-frame risk accepted for disposable demo | Personal-use security scope approval; no hardware-backed prerequisite imposed | Controlled-clock auth fixtures; completed hardware evidence reused |
| Apple/iCloud Calendar events | Inactive private read-only discovery/REPORT/credential primitives; event appointments on live screen are synthetic, reminder due markers are real | **Primary next feature:** Linux-local selected-calendar collector, event normalization/cache, authenticated calendar-only route and frontend activation; approve account/calendar scope before real access | Offline CalDAV and existing VEVENT recurrence/DST fixtures; one secure setup and short consolidated real-event check |
| Recurring reminder completion | Disabled on frame; new recurrence/Radicale tests passed | Needed only to complete recurring tasks from frame; not a calendar blocker | One future batched phone representation capture, then automated instance-write validation; keep disabled meanwhile |
| Spotify Now Playing | Planned; existing music UI is Home Assistant based, not a Spotify connector | Optional after actual calendar; supported API eligibility/OAuth before access | Mocked state/token/backoff tests, then one real playback check |
| Bambu A1 Mini | Planned, no live telemetry connector | Optional after actual calendar; secure supported firmware/protocol check before credentials | Recorded disposable telemetry/reconnect fixtures, then brief read-only printer check |
| Recovery/retention | Private consistent backup, restarts/outages/revocation exercised; units enabled | Verify operational restore/retention before relying on important personal data | Isolated restore and controlled failure tests; long soak separately; full Linux reboot only in an approved maintenance window |

## Ordered implementation

1. Review detailed Apple Calendar requirements and existing
   [private CalDAV preparation](pf1007l-private-icloud-plan.md). Preserve local-only
   credentials/event storage; no public feed or cloud upload substitution.
2. Finish the offline collector/normalization/cache and calendar-only frontend path,
   reusing existing event parsing tests. Explicit selected-calendar scope, partial
   failure last-good retention, privacy projection and synthetic-data separation
   must pass before account connection. Use existing device auth; do not remove
   global demo isolation merely to show real calendar events.
3. Batch genuinely required authorization: owner chooses approved account/calendars,
   enters app-specific credentials privately, and verifies a few synthetic events
   in their selected calendar. Do not request secrets in chat or connect early.
4. Run one short physical calendar check for all-day/timed/date placement and
   unchanged theme/weather/tasks. No new 15-minute auth wait or cellular rerun.
5. Resume deferred recurrence, Spotify/Bambu and sustained reliability in that order
   as needed after the real calendar is useful. Optional investigation is not a
   gate to an otherwise working feature.

Nonblocking limitations: native iOS fetch delays, exact locked-background download
timing, Mac-off acceptance in the last cellular run, and multi-day soak evidence.
The Siri transcription variant was physically verified but excluded from exact-title
server observation. These remain documented rather than triggering repeated tests.
Security/privacy authorization and failed critical data-integrity tests remain real
gates. No personal iCloud migration or production activation has been authorized.
