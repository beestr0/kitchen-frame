# Private iCloud calendar preparation — inactive

No service is installed, no credential collector has been run and no Apple
account request has been made. Running the tests uses invented data and mocked
transport only. Importing the transport or constructing its client does no I/O.
Do not run credential entry or call discovery against Apple until method approval.

Prepared pieces:

- `readonly_caldav.py`: bounded HTTPS PROPFIND discovery and VEVENT REPORT reads;
  no write methods; narrow Apple CalDAV endpoint/redirect validation; normal
  hostname and certificate checks; no inherited HTTP proxy; sanitized errors;
  namespace-aware XML parsing with DTD/entity, UTF-16 and size rejection.
- `prepare_credentials.py`: future hidden native Terminal entry on Linux root TTY,
  opt-in `--approved-storage`; atomic non-overwriting root-private storage. It
  validates expected app-password format but cannot prove credential scope or
  authenticity. It never authenticates, discovers calendars or starts syncing.
- `config.example.json`: disabled, no selected calendars, no cloud upload, minimal
  event fields. Selection remains a separate step after approved metadata discovery.
- `tests/`: entirely offline fixtures for TLS configuration, endpoint restrictions,
  read-only requests, discovery, bounded event queries, redacted failures and
  private non-overwriting credential storage.

Validation: `python3 -m unittest discover -s deploy/icloud-calendar/tests -v`.

These primitives are not a production-ready sync service. Live Apple compatibility,
full multistatus/partial-result handling, recurring-event normalization, snapshot
retention, calendar selection persistence, authentication to the frame and frontend
calendar-only activation still need implementation/acceptance after approval.
The allowed Apple endpoint names are an initial restrictive implementation rule,
not a guaranteed complete Apple service contract. New discovered hosts fail closed
pending review, not an automatic expansion of the credential destination list.

The proposed architecture, comparison, account permissions, secure entry and
activation/rollback boundaries are in
[the private calendar proposal](../../docs/pf1007l-private-icloud-plan.md).
