# Linux Mint demo proxy installation

## Scope and current status

Dedicated server: `hub@10.157.1.115`, proxy `http://10.157.1.115:8788/`.
Only the frame at `10.157.1.247` is allowed to use dashboard routes. The
server's own address can access the health route, not dashboard routes.
This is a **demo-only HTTP deployment**: live APIs and WebSockets are blocked.
Do not enable personal integrations over this transport.

Installation and physical acceptance completed on 2026-11-13. Both project
units are enabled; the proxy is active on the specific LAN IPv4 address above.
The frame is displaying the Linux-hosted Home screen. Its native saved URL
remains the previous USB URL; permanent kiosk URL changes are still deferred.
The Mac is not in the active dashboard request path. The original USB reverse
mapping was restored as a fallback after proving a reload without it.

## Corrected automation

`deploy/lan-proxy/install_host.py` is the canonical installer. Generated
`install-host.py` and `resume-host.py` now delegate to it rather than keeping
separate, string-patched installation logic.

The original failure came from unconditionally resetting a stopped, disabled
service that systemd could garbage-collect. The installer now:

1. Recognizes existing project files and refuses unknown collisions or drop-ins.
2. Verifies the installed Node binary/version and preserves it rather than
   extracting it again. Creates `/opt` parents for a fresh installation.
3. Preserves an existing root-private credential; never replaces it implicitly.
4. Checks JavaScript, demo policy and firewall syntax.
5. Writes **both** unit files, runs `systemctl daemon-reload`, verifies their
   registration/path and runs `systemd-analyze verify`.
6. Tests actual `DynamicUser`/`LoadCredential` access in a temporary unit with no
   listener. systemd credentials must reside on their read-only per-unit RAM
   mount; ordinary source files still require owner-only permissions.
7. Resets failure state only when the unit is loaded and actually failed.
   A benign unloading race is tolerated; genuine reset failures propagate.
8. Starts only the dedicated proxy and guard; checks health and unchanged
   Jellyfin/Tailscale PIDs, media mount and existing iptables rules.
9. Enables boot startup only after coordinated physical proof succeeds.

A private manifest and phase journal preserve completed steps. An exclusive lock
rejects concurrent installations. Failures preserve full command stdout/stderr;
if startup has begun, only these two new services are stopped.

`deploy/lan-proxy/launch_installer.py` prepares the native Terminal command.
It uses Bash `pipefail`, captures the SSH and `tee` statuses immediately, and
returns the failing status. Password entry stays in Terminal. No password is
stored by these scripts.

Prepared command (local, no credential arguments):

```sh
/bin/bash /Users/beestrother/Projects/kitchen-frame/diagnostics/pf1007l/mint-install/run-corrected-installer.sh
```

Do not run it concurrently with an already pending installer. Its final markers
must include `PF1007L_INSTALL_COMPLETE`, `PF1007L_SSH_EXIT=0`, and
`PF1007L_TEE_EXIT=0` before claiming installation success.

## Managed files and service operations

- `/opt/pf1007l-proxy/`: isolated Node runtime and proxy source.
- `/etc/pf1007l-proxy/config.json`: demo-only access configuration.
- `/etc/pf1007l-proxy/dashboard-key`: root-owned mode 0600, never log/copy to UI.
- `/etc/pf1007l-proxy/firewall.nft`: only the dedicated `inet pf1007l_proxy` table.
- `/etc/systemd/system/pf1007l-proxy{,-firewall}.service`.
- `/etc/pf1007l-proxy/install-manifest.json`: non-secret managed-file metadata.

After acceptance, service management on the server:

```sh
sudo systemctl status pf1007l-proxy pf1007l-proxy-firewall
sudo journalctl -u pf1007l-proxy --since '10 minutes ago' --no-pager
curl --fail http://10.157.1.115:8788/__proxy_health
sudo systemctl restart pf1007l-proxy
```

Recovery markers wait for the health endpoint, not merely `systemctl start`.

The proxy uses validated HTTPS upstream, fixed host/client/origin restrictions,
no request/access logging, bounded connections and a 15-second upstream timeout.
Failed document requests show a retry page that refreshes after 10 seconds.
Systemd restarts crashes after five seconds, limits CPU to 10% of one core and
memory to 128 MiB (64 MiB high watermark). Restart bursts are bounded. Boot
activation is configured after `network-online.target`; DHCP/address changes,
DNS outages, exhausted restart limits and Cloudflare outages remain possible.
Keep server/frame addresses reserved; monitor the restricted health route and
systemd failed state. No reboot of this shared server is part of acceptance.

## Rollback

Restore the separate kiosk's existing USB dashboard first, if needed. HomeHQ
and the saved USB kiosk URL are preserved. Restore forwarding on the Mac with
`adb -d reverse tcp:5173 tcp:5173` while its existing local dashboard is running.

On the server, stop and disable only the project units:

```sh
sudo systemctl disable --now pf1007l-proxy.service
sudo systemctl disable --now pf1007l-proxy-firewall.service
```

Stopping the guard deletes only `inet pf1007l_proxy`. Leave the protected files
in place for reversible rollback; removal is unnecessary. Do not flush nftables,
iptables or change global firewall defaults. Do not restart Jellyfin, Tailscale,
NordVPN, mounts or networking. No Cloudflare changes are involved.

## Validation

`python3 -m unittest discover -s deploy/lan-proxy/tests -v`: 18 tests passed,
covering missing/failed/unloaded units, ordering, fresh/repeated runtime setup,
unchanged files, credential rejection/acceptance, and SSH/tee failure propagation and readiness retries.
Physical acceptance passed Home, Calendar week/month/navigation, invented task
add/complete, Focus start/pause/reset, Settings, light/dark themes, Wi-Fi reload
with USB reverse removed, actual proxy stop/restart, and app-scoped offline
recovery. Observed samples: Home 58.2, Calendar 58.8, Tasks 59.8, Focus 60.0 FPS.
One Home sample had an 83 ms frame; the other samples had no frames above 50 ms.
No page exceptions were recorded. Connection-refused/disconnected errors were
expected during deliberate interruption/offline tests; navigation also aborted
in-flight requests.

Proxy RSS was approximately 66.7 MiB during UI testing and CPU averaged 0.45% of
one core. After the controlled restart, systemd reported approximately 20.5 MiB
charged memory and zero automatic restarts. RSS and cgroup memory use different
accounting. Upstream HTTPS responses all passed certificate validation; the
separate backend authentication check returned 200. Demo APIs are served locally
and live API/WebSocket access remains blocked.

The non-allowlisted Mac timed out at the firewall; the server's health-only
identity received 403 for dashboard APIs. Jellyfin PID 459473 and Tailscale PID
468133 remained unchanged; existing mount/filter checks passed. No reboot was
performed. Startup configuration is verified, not reboot-tested.

Private evidence: `diagnostics/pf1007l/mint-install/verified-install-state.json`,
`frame-LAN-proxy-results.json`, screenshots, and Terminal log. Do not publish the
private staging directory or any credential backups.


See [deployment finalization](pf1007l-deployment-finalization.md) for the subsequent
read-only health review, remaining stability gaps, prepared saved-URL procedure,
and encrypted transport comparison. No permanent kiosk URL change has been made.
