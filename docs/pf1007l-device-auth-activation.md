# PF1007L persistent device authentication — verified demo activation

Verified November 14, 2026. The owner accepted the software-backed/physical-access
tradeoff and approved controlled deployment, fingerprint enrollment and narrowly
scoped project-service restarts. **Device-v1 is active for the disposable demo.**
No production synchronization, personal-list migration or iCloud account change occurred.

## Final deployed state

- Core bridge/auth/proxy handler/unit match reviewed commit `8aade81` (five runtime
  file hashes verified). Frame APK v5 `1.4-auth-candidate` installed in place with
  the existing signer and application UID; app data was retained.
- Owner physically compared the full Device ID and explicitly approved that public
  key. The displayed SPKI hashes to the displayed ID; hardwareBacked=false. Public
  identity evidence remains ignored in `activation-public-enrollment.json`; no
  private key was read/exported. The owner then physically enabled native auth.
- Device-v1 accepts signed one-use proofs and renewable 900-second sessions. Legacy
  cookie authentication is rejected in this mode; no automatic weaker fallback.
- One authorized device, current key epoch advanced through a deliberate
  revoke/re-enable test. Existing CalDAV/backend/CSRF/identity key values preserved.
- Original URL, design, automatic theme preference, live weather and selected
  PF1007L Test collection preserved. Actual calendar events remain synthetic;
  private iCloud Calendar preparation is still inactive.
- Native privileged session deliberately finished, WebView debugging off, USB
  forwarding removed. Temporary Mac sleep assertion stopped; one-shot recovery
  timer automatically collected. Runtime authentication needs neither Mac nor sudo.

## Verified acceptance results

| Check | Result |
| --- | --- |
| Preflight/backup | Private baseline files/UI/settings and consistent SQLite snapshot; quick_check passed |
| Compatibility | Legacy auth/five original task states verified before APK update; live weather and HTTPS recovered |
| In-place APK | Same signer, v5, saved URL/session/theme retained; HomeHQ remains installed/data untouched |
| Initial native proof | Frame session/snapshot 200 device-v1, fresh tasks, valid weather |
| Continuous renewal | 44 healthy samples over **1921.296 seconds**; initial + **two automatic renewals**, fixed 900-second lifetimes; no reload/manual renewal/password |
| Live denials | No-cookie session/snapshot 401; unknown device 403; missing CSRF 403; legitimate session still 200 |
| Phone creation | New disposable task appeared once in Tasks and correct November 14 physical Calendar day |
| Phone edit | Due moved to November 15, same UID-derived ID/new revision, correct physical Calendar day, no duplicate |
| Frame completion | Normal UI checkbox completed same resource; November 15 preserved |
| Phone confirmation | Owner confirmed completed on iPhone and due date preserved |
| App process restart | No data clearing; saved URL, key/auth, theme and fresh tasks/weather recovered |
| Browser network loss | 90-second WebView-only simulation retained rows/blocked completion; automatic recovery **4.023 seconds**, no refresh; physical Wi-Fi/unrelated apps untouched |
| Bridge restart | Existing session persisted, issuance unchanged, authenticated frame/data recovered without reprovisioning |
| Real expiry outage | Actual bridge-only stop **960 seconds**, independent timer installed; old session naturally expired while stopped; other services active throughout |
| Recovery without debugger | Debugging/USB forwarding off throughout expiry test; fresh native proof issued ~5.4 seconds after scheduled restart; healthy recovery observed within **22.65 seconds** |
| Revocation | Loaded key disabled; zero sessions/authorized devices; real session/read/complete 401, renewal 403; saved row disabled |
| Re-enablement | Same key re-enabled with a new epoch for this no-compromise test; fresh proof and automatic UI recovery; completed task/due preserved |
| Final services | All project/Jellyfin/Tailscale services active; required services enabled; private Serve unchanged, Funnel off; Jellyfin healthy, HTTPS upstream errors zero |

Continuous observation issuances were Unix 1794685316.875905,
1794686044.0307913 and 1794686793.4127488. Observation code never requested native
renewal or reloaded; it only inspected safe session/snapshot and aggregate issuance
metadata. The existing idle preference stayed 0. No server/client clock change or
shortened session constant was used.

The expiry outage started Unix 1794687932.8861678. Previous expiry was
1794688416.8026922; fresh post-outage issuance was 1794688898.2893062, while debugging
was off. The restored bridge purged expired session records during new proof.
Revocation then removed that still-valid session; re-enablement generated a new
issuance at 1794689057.9652524. Epoch rotation is not private-key replacement and
must not be used to recover a genuinely stolen key.

## Performance, resources and tests

All **195 automated tests passed**: 62 dashboard, 48 proxy/TLS, 5 Node demo-proxy,
67 Mint Reminders fixtures (including 12 activation-controller and 3 preflight),
3 SSH and 10 inactive iCloud tests. Fixtures use invented resources/temporary keys;
no live account/settings or personal reminders are test inputs.

Settled physical Home/Tasks/Calendar measurements under both themes were about
**59.99–60.16 FPS**, with no >50 ms gaps in stable-theme samples. Final post-recovery
Home measured **59.77 FPS**, no >50 ms gap. Earlier transition samples ranged
55.7–60.2 FPS with occasional 50–116 ms gaps; one explicitly crossed automatic
restoration to the current light theme at a minute boundary. Preserve that evidence;
this is approximately 60 FPS, not a promise of universally jank-free transitions.
Original Home/light appearance and automatic preference restored at finish.

Final cgroup memory: bridge ~18 MB, Radicale ~19 MB, HTTPS ~51 MB. No automatic
service restarts were recorded. Jellyfin/Tailscale/Radicale start timestamps stayed
unchanged throughout deployment; only project bridge/HTTPS restarts were performed.
Mac ~13 GiB and Mint ~846 GiB free at checks; no large downloads or OS changes.

## Preserved backup, artifact integrity and recovered startup error

Original private backup:
`/var/backups/pf1007l-device-auth/backup-20261114T192145Z-7aef9bbe`.
Frozen artifacts/retained diagnostics:
`/var/backups/pf1007l-device-auth/artifacts-20261114T192145Z-7aef9bbe`.

Frozen manifest SHA256:
`e1d119d6e96a548612e16751ee940a11e1951903873d6bca5b6956f788544f53`.
Candidate and same-version rollback APK checksums/signatures match their manifest
and the installed signer. Rollback APK was built/verified, not installed; it requires
neither uninstall/data clearing nor a version downgrade. Private snapshot remains
on Linux; it was **not** restored over newer tasks/operation history.

The first compatibility attempt checked HTTPS before Node bound its socket (curl
exit 7). Automatic rollback restored files but repeated that premature health
check, reporting failure. We stopped, confirmed physical legacy operation and
byte-identical original code, then privately reauthorized recovery because the
failed helper had exited. Recovery verified **all original files/UI/modes and
protected hashes** against backup, with database/history not rewound. Root-only
sanitized diagnostics confirmed curl exit 7 for both checks. Corrected bounded
readiness waits and stale-action prevention passed regression tests; the next
compatibility attempt passed. No verification gate was bypassed or TLS weakened.

The current tested scoped controller SHA256 is
`e1e0c3be7013fecc080d0e682b31eaa842e7cec31c5d2c0b3433ebcae472bc30`.
Its final action was `finish-0321d8585d304551b43df5994df95873`, phase finished,
device-v1/bridge active/one authorized device. The former Terminal no longer holds
an active privileged session. Do not queue more actions assuming it is alive.

## Evidence, recovery and remaining limits

Physical/runtime evidence is ignored under `diagnostics/pf1007l/reminders/`, including
renewal, workflow, denial, network, expiry, revocation and FPS reports/screenshots.
Do not commit these payloads, settings, cookies, databases, keys or diagnostic dumps.
No raw cookie/CSRF/private-key values were returned by inspection tools or logs.

Use [the security and rollback runbook](pf1007l-auth-security-review.md). Ordinary
rollback restores the immediately-pre-activation demo code/settings/UI and retains
current SQLite/Radicale task/operation history. Never rewind completion history to
the backup snapshot. Do not use the old pre-demo `rollback_bridge.py` for this.
For suspected compromise, revoke and fail closed; do not revert to IP/legacy auth.
A clean new key/device is required after key theft. No resets occur automatically.

Still not verified: cellular/Tailscale handoffs, locked-phone/background fetch timing,
real recurring occurrence advancement, multi-day stability/restore and a full Linux
reboot. Frame recurring completion remains blocked. The unsupported rooted,
unencrypted Android/software Keystore risk remains as accepted for this demo.
Everyday personal use, migration, other lists/providers and production need separate
owner approval. Native iPhone fetch is not an instant-push guarantee.
