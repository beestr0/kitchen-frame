# Reminders demonstration pilot — fixed disposable collection only

The native iPhone → Radicale → physical dashboard → Radicale → iPhone loop is now
verified for the disposable collection, including phone edits/completion and Siri
creation. See [current integration results and rollback](../../docs/pf1007l-reminders-integration.md).
The demo frame URL is `https://beestr0.duckdns.org:8789/__reminders-demo/`; actual
iCloud calendars/personal reminders remain inactive and production is not approved.

The owner has approved an isolated Radicale/Tailscale pilot. Persistent SSH via
`pf1007l-mint` is verified and deployment has resumed; see
[current pilot status](../../docs/pf1007l-reminders-pilot-status.md).
`install_demo.py` is the scoped native-sudo installer for the pinned loopback-only
service. Check its remote status before assuming the templates are installed or
validated. Production synchronization remains unauthorized.

Private HTTPS is now verified; see the latest checkpoint in the status document.
Do not rerun installation to verify access. `verify_native.sh` invokes the dedicated
`verify_https.py` with existing credentials and a tailscale0-bound client socket
for same-host checks; normal CA/hostname checks remain enabled. The native TTY
shows the disposable password for owner iPhone entry, never in chat. When staging
an installer/resume helper, include `verify_https.py` and `show_demo_account.py`.

The standalone CLI demonstration below is still offline. Its example configuration
is documentation, not a runtime switch. The separate Radicale pilot and fixed task
adapter are installed on Linux. Only the local demo frontend/proxy route uses the
adapter; cloud Workers and the ordinary dashboard route never receive task data.

Run from the repository root:

```sh
node deploy/reminders/demo.mjs
cd dashboard
node --test src/lib/reminders.test.js worker/reminders-vtodo.test.js
```

The simulator uses invented reminders in two lists, partitions undated Tasks from
Calendar due markers, simulates a frame completion and a phone completion, and
prints only demonstration data. Tests also simulate a phone edit racing with a
frame completion, list exclusion, an outage, reopening a completed item, invalid
snapshots, and preservation of VTODO properties during completion.

This is a protocol/state demonstration, not an iPhone simulator or a working DAV
connector. No claim of tested Siri, Radicale interoperability or physical frame FPS.
Recurring rules are preserved by refusing recurring writes; expansion and recurring
completion are intentionally unimplemented pending real-client compatibility tests.
Normalized timed due dates must be supplied by the future Linux collector: `day`
in the display timezone, `at` as a UTC instant. Date-only due dates never shift zones.
Calendar markers carry `kind: reminder`; existing event components must be adapted
to render due labels and completion before these markers enter the real UI.

See [assessment and approval gates](../../docs/pf1007l-reminders-assessment.md).
