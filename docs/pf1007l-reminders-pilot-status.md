# Approved demonstration pilot — persistent SSH restored

**Latest:** the iPhone account and physical frame demonstration loop are now
verified. See [current integration results](pf1007l-reminders-integration.md) and
[next-session handoff](NEXT_SESSION.md). Pending/failed sections below are history,
not instructions to repeat setup or reset credentials.

## Current iPhone verification investigation — authenticated discovery pending

Owner reports Safari reaches HTTPS and prompts for authentication, but native
CalDAV setup says `Calendar Account Verification Failed`. Do not equate the prior
direct-collection test with proven iOS account discovery or Reminders interoperability.

Read-only checks: all existing services active, exact root Serve mapping unchanged,
Funnel absent. Both GET and PROPFIND `/.well-known/caldav` return 301 `Location: /`.
Resolving that relative redirect preserves HTTPS, the external hostname and port
443. Root/principal paths require Basic authentication (401). OPTIONS returns 200
with `calendar-access` and required DAV methods. No path prefix is stripped by this
root-to-root mapping. Warning-level logs show earlier intentional bad-password and
stale-write tests; they do not yet identify the iPhone's failing request. No server
configuration, credentials, data or service units have been changed during diagnosis.

`diagnose_discovery.py` is staged for root-private credential use in a read-only
HTTPS principal → calendar-home → Depth-1 collection → VTODO REPORT test. It emits
only a sanitized `discovery-status.json`; raw XML, task titles and passwords are
not reported. A new native Terminal was opened with:

```sh
ssh -tt -o BatchMode=yes pf1007l-mint sh /home/hub/pf1007l-reminders-stage.LEZsOd/discovery_native.sh
```

Its actual hidden sudo prompt was verified. The authenticated test has not begun
until the owner completes that prompt. Do not ask for an iPhone retry or claim the
issue fixed before reviewing its result. The owner's iOS version and actual SSL,
port and Account URL settings were also requested without requesting a password.
Two offline redirect-origin tests passed. Further server changes require evidence
from authenticated discovery or a captured failing client request, not speculation.

## Current verified state — private HTTPS ready

Browser authorization propagated and the existing Serve process configured only:
`https://hub-inspiron-5570.tailb76e1b.ts.net:443/` → `http://127.0.0.1:5238`.
No installation, data migration, credential replacement or unit reconfiguration
was repeated. Funnel is false/absent. Radicale still listens only on loopback;
Serve listens only on Tailscale addresses bound to `tailscale0`. LAN-address ports
443 and 5238 refused connection from the Mac.

`verify_https.py` completed authenticated HTTPS verification with an explicitly
tailscale0-bound client socket, system CA trust and hostname validation. TLS 1.3;
certificate expires February 12, 2027 at 13:30:19 UTC. Missing/wrong passwords
returned 401; the existing account returned 207 for `PF1007L Test`; other-owner
access was denied. Remote phase is `tailnet-https-demo-ready`.

The original same-host HTTPS probe timed out because the ordinary local path did
not reach Tailscale's interface-bound listener. No listener restriction or TLS
security was weakened. Installer/resume source now delegates HTTPS verification to
the corrected helper. Verify without reinstalling with:

```sh
ssh -tt -o BatchMode=yes pf1007l-mint sh /home/hub/pf1007l-reminders-stage.LEZsOd/verify_native.sh
```

The existing demo password is displayed only in the native TTY after verification.
All existing services are active; Jellyfin `/health` returned 200, dashboard HTTPS
health passed with zero upstream errors, and certificate timers remain scheduled.
HomeHQ and kiosk launched successfully on the frame; no app data/launcher settings
changed, and the original launcher was restored. This proves app launch, not
exhaustive HomeHQ provider functionality. No iPhone/Siri/cellular or frame Reminders
integration acceptance test has run.

**Next: add the demo account to iPhone with Tailscale connected.** The exact iPhone
values below are now verified and ready. Leave iCloud and Siri's default list
unchanged. Dashboard task/calendar data remains demonstration-only.

## Resume verification

The prior installer had exited with failure, leaving no sudo prompt; it was not
still awaiting authentication. A new native Terminal was opened with:

```sh
ssh -tt -o BatchMode=yes pf1007l-mint sh /home/hub/pf1007l-reminders-stage.LEZsOd/resume_native.sh
```

The actual hidden prompt `PF1007L Mint sudo password (hidden):` was verified by a
boolean Terminal check without returning Terminal contents. Sudo succeeded. The
resume-only helper does not run pip/apt, rewrite units or credentials, recreate the
collection, or edit existing tasks. It verified the existing `PF1007L Test` VTODO
list and passed new-resource DAV create/edit/complete, stale-write rejection and
due-date preservation tests. It then reached `awaiting-native-tailnet-https-setup`.
At that checkpoint Serve config was still empty and no public listener was added.
The owner must handle any Tailscale HTTPS authorization link privately in Terminal.
Use the remote non-secret status file for the latest phase; do not infer success.

### iPhone configuration after private HTTPS verification

Remote phase is now `tailnet-https-demo-ready` and certificate/auth checks passed.
These exact connection values are ready for the owner to enter:

- Server: `hub-inspiron-5570.tailb76e1b.ts.net`
- HTTPS/SSL: on; port `443`
- Username: `pf1007l-demo`
- Account URL if requested: `https://hub-inspiron-5570.tailb76e1b.ts.net/pf1007l-demo/`
- Description: `PF1007L Demo`
- Existing list: `PF1007L Test`

Retrieve only the disposable DAV password in a private native Terminal:

```sh
ssh -tt pf1007l-mint sudo -- python3 /home/hub/pf1007l-reminders-stage.LEZsOd/show_demo_account.py
```

Do not send that password or screenshots to chat. It is not an Apple Account
password. Connect Tailscale on the iPhone to the same tailnet, then use Settings →
Apps → Reminders → Reminders Accounts → Add Account → Other → Add CalDAV Account.
Enter the values above and enable Reminders only. Keep iCloud and Default List
unchanged. Open `PF1007L Test` in Reminders and verify its demo task. Then test Siri
with “Add test paper to my PF1007L Test list,” confirming the actual list destination.
No physical iPhone/Siri/home-cellular or frame dashboard integration test has yet run.

## Latest access update

Loopback service is now installed and active: Radicale 3.9.1/bcrypt 5.0.0,
127.0.0.1:5238 only, dedicated `pf1007l-demo` account, `PF1007L Test` collection.
Missing/wrong authentication, other-owner denial and stale conditional PUT rejection
passed. The code-directory umask issue in the first start was corrected. Observed
cgroup memory ~24 MB, with CPU ~5.95 seconds accumulated during startup/auth tests;
this is not a sustained-load or frame FPS benchmark. Existing services remain active.

Follow-up native sudo session is running additional DAV edit/completion probes and
guarded tailnet HTTPS setup. HTTPS was not yet enabled at the last recorded baseline.
Read `/home/hub/pf1007l-reminders-stage.LEZsOd/pilot-status.json` over persistent SSH
for the actual current phase. No iPhone account/default or personal reminders changed.

The owner authorized a permanent SSH fix. Dedicated Ed25519 key authentication now
works through `pf1007l-mint`, including BatchMode with the agent disabled. Use that
alias for every future SSH/scp operation; temporary control sockets are no longer
required. See [persistent access instructions](../deploy/ssh/README.md).

The pilot has resumed: installer staged at
`/home/hub/pf1007l-reminders-stage.LEZsOd/`, native sudo Terminal opened. Check its
`pilot-status.json` for the actual result before taking subsequent deployment actions.
Current baseline: existing services active, HTTPS healthy, cert timers scheduled,
no Serve/Funnel mapping, tailnet HTTPS not yet enabled. The historical blocked report
and socket restoration commands below are retained as history, not current guidance.

Owner approved the isolated Radicale/Tailscale demonstration on November 14, 2026.
This does not authorize personal-list migration, Siri default changes or production
task synchronization. The existing iCloud Calendar preparation remains unchanged.

## Actual results

- Reviewed the prepared demo and assessment; existing uncommitted work preserved.
- Mint SSH reached the server but rejected authentication with
  `Permission denied (publickey,password)` using noninteractive authentication.
- The previous secure SSH control socket at
  `/private/tmp/pf1007l-server-ssh/control` no longer exists.
- Consequently no remote preflight ran, no Radicale package/service/account/list was
  installed, no credentials were generated, and no Tailscale route was changed.
- No actual iPhone, Siri, Wi-Fi/cellular, DAV conflict/outage, Linux resource or frame
  FPS test has run. The earlier simulated tests are not evidence for those checks.

## Historical temporary-session workaround — superseded by persistent key

In a native Mac Terminal, create a private, reusable authenticated SSH session:

```sh
mkdir -p /private/tmp/pf1007l-server-ssh
chmod 700 /private/tmp/pf1007l-server-ssh
ssh -M -S /private/tmp/pf1007l-server-ssh/control -o ControlPersist=30m -o StrictHostKeyChecking=yes -N hub@10.157.1.115
```

Enter any SSH password only at that native Terminal prompt. No password, key,
terminal transcript or screenshot should be sent to chat. Keep the Terminal open;
the foreground command has no shell prompt after login because it maintains the
connection. If host-key validation fails, stop and verify the host through a trusted
channel; do not disable checking or remove the remembered key to get past it.
Tell the assistant when connected. If an existing configured SSH key/host alias is
preferred, provide only that alias/path, never key contents. Sudo may require a
separate private native Terminal prompt later; do not cache or pipe its password.

End the shared session after work with:

```sh
ssh -S /private/tmp/pf1007l-server-ssh/control -O exit hub@10.157.1.115
```

## Prepared deployment templates — not installed or runtime-tested

`deploy/reminders/radicale-demo.conf.example` binds loopback only, requires bcrypt
authentication, restricts collections to their owner, disables web UI and collection
replacement/deletion, limits request sizes and uses locked filesystem storage.
`deploy/reminders/pf1007l-reminders-demo.service` uses DynamicUser, private state,
systemd credentials and process/memory/CPU/network limits. The proposed 5238 port
is a placeholder until inspected. These are preparation, not a runnable installer;
Radicale config acceptance, permissions and systemd hardening need validation on
Mint with the chosen pinned release. No broad system package upgrade is needed.

Next remote actions after access is restored:

1. Read-only baseline: active services/certificate timers, HTTPS health, RAM/CPU/load,
   listeners, Python/venv availability, existing Tailscale Serve/Funnel configuration,
   device identity and applicable tailnet policy. Do not dump secrets or personal peers
   into chat. Identify a free loopback port and an unused Serve HTTPS listener.
2. Install an isolated pinned Radicale venv under `/opt/pf1007l-reminders-demo`,
   root-owned code, 0700 `/etc/pf1007l-reminders-demo` and private state. Generate
   only a dedicated pilot credential; keep it server-private, with bcrypt hash for
   Radicale and secure native Terminal retrieval for iPhone entry. No Apple password.
3. Validate config with the selected Radicale version, verify the systemd unit, start
   the loopback service, test auth failure and owner isolation before publishing a
   tailnet route. Confirm cgroup loopback restrictions are effective.
4. Add an additive Tailscale Serve HTTPS mapping with narrow access rules, preserving
   all existing mappings. Verify certificate/hostname and DAV method forwarding.
   No Funnel, public listen address, router ports or global firewall change.
5. Create `PF1007L Test` under the dedicated pilot account via authenticated
   MKCALENDAR declaring VTODO support, with invented reminders only. Capture
   resource/ETag behavior and conditional 412 tests before frame mutation wiring.
6. Implement and validate the task adapter and demo-only UI using the assessment's
   security and cache contract. Do not enable production sync. Recurring completion
   must remain gated until its real-client behavior is known.
7. Record the real hostname, username, HTTPS port and secure password retrieval
   procedure. Then pause for the owner to add the account to the iPhone as requested.
   Do not give placeholder connection values as if the service is already usable.

## iPhone interaction checkpoint (not reached)

Exact connection values are unavailable until deployment succeeds. Once provided:

- Connect the iPhone to the same tailnet, using Tailscale on Wi-Fi and cellular.
- Settings → Apps → Reminders → Reminders Accounts → Add Account → Other → Add
  CalDAV Account. Enter the verified server, dedicated local username/password and
  SSL port supplied at the checkpoint. Enable Reminders for this account only.
- Keep the existing default list and iCloud configuration unchanged.
- Ask Siri explicitly: “Add test paper to my PF1007L Test list.” Inspect the list in
  Reminders to confirm its destination; Siri's spoken acknowledgement is insufficient.
- Use demonstration text only. Follow the assessment's bidirectional, recurring,
  offline/conflict and Wi-Fi/cellular checklist; report observed delays rather than
  assume instant background synchronization.

Readiness for everyday use requires all these physical checks, secure frame write
authentication, durable idempotency/conflict handling, a tested backup/restore and
resource/FPS measurements. None are marked passed by the offline simulator.
