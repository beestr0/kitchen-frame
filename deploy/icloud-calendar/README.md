# Private iCloud Calendar — active on Mint

Owner authorized Option B and selected two calendars privately. Read-only sync and
physical event/edit acceptance passed. Credentials remain root-private on Linux;
do not repeat setup/discovery or overwrite configuration. Consult the live report.

- `readonly_caldav.py`: existing read-only HTTPS discovery and bounded VEVENT reads,
  now rejecting failed/duplicate/incomplete multistatus resources before deletion.
- `collector.py` / `service.py`: selected-calendar per-source last-good SQLite cache,
  five-minute refresh, retry/auth latch and keyed loopback5241 snapshot service.
- `normalize.mjs`: existing tested ical.js calendar parser reused on Linux, bounded
  and minimally projected. Uses the already installed proxy Node runtime. No browser
  parsing, Apple credential, network access or implicit setup in the normalizer.
- `pf1007l-calendar.service` / `bridge-calendar.conf`: isolated DynamicUser collector
  and optional credential-only task-bridge extension. Both are installed; collector is enabled and running.
- `authorize.py` / `prepare_credentials.py`: private native root-TTY credential and
  metadata selection helpers; never fetch events, write Apple data or start services.
- `start_authorization.py`: checksum-pinned native SSH setup launcher, used privately after approval; no repeat entry needed.
- `prepare_release.py`: non-overwriting credential-free candidate freeze; v3 is the
  tested bundle. No deployment, service restart or Apple request on preparation.

Validation: `python3 -m unittest discover -s deploy/icloud-calendar/tests` (27 tests including activation/retry),
`npm test` in dashboard (72 tests including parser/projection), and relevant bridge/
relay tests. Full fixture pipeline passed on Mint with zero Apple requests.

Follow [implementation, account choice and deployment/rollback runbook](../../docs/pf1007l-calendar-integration.md).
