# Recurring reminders — verified preparation, completion still disabled

November 14, 2026. This work is checkpointed source/tests only; the live bridge,
APK, existing demo resources and all personal reminders were not modified. Further
recurrence work is deferred behind the owner's primary live Apple Calendar goal.

## Completed automated work

- Nine Python tests passed on Mint: four new recurrence tests plus the five existing
  bridge regressions. Three focused JavaScript completion tests passed.
- Actual installed Radicale was instantiated in-process with WSGI, fictional Basic
  authentication and temporary storage under `/dev/shm`. No TCP listener or service
  was created. The test verified VTODO series/exception/alarm preservation, REPORT
  retrieval and rejection of stale If-Match writes (412). Temporary data is removed.
- Bridge fixtures reject completion for daily, weekly, monthly/BYSETPOS, explicit
  RDATE, EXDATE/EXRULE, detached and master-plus-exception resources, without PUT or
  recording a completed operation. Alarm/unknown Apple properties remain intact.
- Hypothetical client advancement of a due date retains the same task ID and updates
  the revision without creating occurrences. This fixture is not actual iOS evidence.
- The candidate Python parser now rejects duplicate detached recurrence identifiers
  rather than arbitrarily choosing one. A failed snapshot retains last-good data.
- The unused JavaScript completion helper now blocks EXDATE/EXRULE-only resources,
  matching the active bridge's existing exclusion-aware recurrence gate.

The standards describe recurrence sets and detached instances, not proof of this
phone's advancement strategy: [RFC 5545](https://www.rfc-editor.org/rfc/rfc5545)
and [CalDAV recurrence data model](https://www.rfc-editor.org/rfc/rfc4791#section-3.2).
A generic STATUS=COMPLETED update of a series is not a proven next-occurrence policy.
No recurring-write candidate was activated or speculative advancement implemented.
The frame continues to show recurring reminders conservatively and requires phone
completion. No occurrence expansion runs on the old frame.

## Deferred short physical batch — only if recurrence becomes next priority

Do not repeat cellular/authentication tests. Prepare a reviewed sanitized observer
first, then one owner session using newly named daily date-only, weekly timed and
month-end disposable reminders in PF1007L Test. Collect initial UID/recurrence/due/
alarms, complete one occurrence on iPhone, then collect changed fields and verify
future occurrence/list state. Preserve those fictional examples as regression
fixtures. Never inspect personal recurring tasks or change default lists.

Only after the observed Apple representation is supported by tested conditional,
idempotent instance writes should a frame-completion candidate and its short
physical return check be proposed. Until then the server and UI gates stay closed.
This deferred batch is not a prerequisite for the Apple Calendar implementation.
