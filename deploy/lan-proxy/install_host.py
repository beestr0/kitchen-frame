#!/usr/bin/env python3
"""State-aware installer for this project's dedicated demo proxy only.

Run as root from the private, checksum-verified staging directory. No package
manager, global firewall reset, VPN manipulation, or unrelated service restart.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import time
import urllib.request

UNITS = ('pf1007l-proxy-firewall.service', 'pf1007l-proxy.service')


class CommandFailure(RuntimeError):
    pass


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def command(args, check=True):
    result = subprocess.run(args, capture_output=True, text=True, timeout=60)
    if check and result.returncode:
        raise CommandFailure(f'{args!r} exited {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}')
    return result


def atomic_copy(source, destination, mode=0o644):
    """Preserve unchanged files/inodes; replace only a reviewed managed asset."""
    source, destination = Path(source), Path(destination)
    if destination.is_symlink():
        raise RuntimeError(f'Refusing symlink destination: {destination}')
    if destination.exists() and destination.read_bytes() == source.read_bytes():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_name(destination.name + '.pf1007l-new')
    if temp.exists():
        raise RuntimeError(f'Unexpected temporary file: {temp}')
    with temp.open('xb') as stream:
        stream.write(source.read_bytes())
    temp.chmod(mode)
    temp.replace(destination)
    return True


def unit_properties(unit, run=command):
    result = run(['systemctl', 'show', unit, '-p', 'LoadState', '-p', 'ActiveState',
                  '-p', 'FragmentPath', '-p', 'DropInPaths'], check=False)
    properties = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    if result.returncode and properties.get('LoadState') != 'not-found':
        raise CommandFailure(f'Cannot inspect {unit}: {result.stderr}')
    return properties


def reset_failed_if_needed(unit, run=command):
    properties = unit_properties(unit, run)
    if properties.get('LoadState') != 'loaded' or properties.get('ActiveState') != 'failed':
        return False
    result = run(['systemctl', 'reset-failed', unit], check=False)
    if result.returncode:
        # A stopped unit may be garbage-collected between show and reset-failed.
        current = unit_properties(unit, run)
        if current.get('LoadState') == 'not-found' or current.get('ActiveState') != 'failed':
            return False
        raise CommandFailure(f'Cannot reset failed state of {unit}: {result.stderr}')
    return True


def register_units(stage, directory, run=command):
    changed = []
    for unit in UNITS:
        if atomic_copy(Path(stage) / unit, Path(directory) / unit):
            changed.append(unit)
    # Always register after ALL unit files exist. No reset/start may precede this.
    run(['systemctl', 'daemon-reload'])
    for unit in UNITS:
        properties = unit_properties(unit, run)
        if properties.get('LoadState') != 'loaded' or properties.get('FragmentPath') != str(Path(directory) / unit):
            raise RuntimeError(f'Unit is not registered from the expected file: {unit}')
        if properties.get('DropInPaths'):
            raise RuntimeError(f'Unexpected drop-ins for {unit}; refusing to replace their behavior')
    return changed


def ensure_runtime(stage, project, meta, run=command):
    stage, project = Path(stage), Path(project)
    binary = project / 'node/bin/node'
    if binary.exists():
        if binary.is_symlink() or digest(binary) != meta['node_binary_sha256']:
            raise RuntimeError('Existing Node binary is not the verified project runtime')
        if run([str(binary), '--version']).stdout.strip() != meta['version']:
            raise RuntimeError('Installed Node version differs from the selected runtime')
        return False
    archive = stage / meta['archive']
    if digest(archive) != meta['sha256']:
        raise RuntimeError('Official Node archive checksum mismatch')
    project.mkdir(mode=0o755, parents=True, exist_ok=True)
    extracted = project / meta['directory']
    if extracted.exists() or (project / 'node').exists():
        raise RuntimeError('Incomplete runtime directory requires inspection; not deleting it')
    with tarfile.open(archive) as contents:
        for member in contents.getmembers():
            parts = Path(member.name).parts
            if Path(member.name).is_absolute() or '..' in parts or not parts or parts[0] != meta['directory']:
                raise RuntimeError('Unsafe runtime archive member')
        contents.extractall(project, filter='data')
    extracted.rename(project / 'node')
    if digest(binary) != meta['node_binary_sha256']:
        raise RuntimeError('Extracted Node binary checksum mismatch')
    run([str(binary), '--version'])
    return True


def wait_for_health(timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen('http://10.157.1.115:8788/__proxy_health', timeout=2) as response:
                return json.load(response)
        except Exception:
            time.sleep(0.25)
    raise RuntimeError('Proxy did not become healthy before the readiness deadline')


def unrelated_state(run=command):
    return {name: run(args).stdout for name, args in {
        'jellyfin': ['systemctl', 'show', 'jellyfin', '-p', 'MainPID', '-p', 'ActiveState'],
        'tailscale': ['systemctl', 'show', 'tailscaled', '-p', 'MainPID', '-p', 'ActiveState'],
        'mount': ['findmnt', '-n', '-o', 'TARGET,FSTYPE', '--target', '/mnt/media'],
        'iptables': ['iptables', '-S'], 'ip6tables': ['ip6tables', '-S'],
    }.items()}


def write_state(path, state):
    temp = path.with_name(path.name + '.new')
    temp.write_text(json.dumps(state, indent=2)); temp.chmod(0o644); temp.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--adopt-existing', action='store_true')
    parser.add_argument('--coordinate-proof', action='store_true')
    args = parser.parse_args()
    stage = args.stage.resolve()
    project, conf, unit_dir = Path('/opt/pf1007l-proxy'), Path('/etc/pf1007l-proxy'), Path('/etc/systemd/system')
    manifest_path = conf / 'install-manifest.json'
    state_path = stage / 'install-state.json'
    state = {'schema': 2, 'phases': [], 'before': unrelated_state()}
    started = False

    def checkpoint(phase):
        state['phases'].append(phase); write_state(state_path, state)
        print('PF1007L_PHASE: ' + phase, flush=True)

    try:
        if os.geteuid() != 0:
            raise RuntimeError('Secure sudo authentication is required')
        lock = open('/run/lock/pf1007l-proxy-install.lock', 'a+')
        os.chmod('/run/lock/pf1007l-proxy-install.lock', 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        meta = json.loads((stage / 'install-meta.json').read_text())
        assets = {'config.json': conf / 'config.json', 'firewall.nft': conf / 'firewall.nft',
                  **{unit: unit_dir / unit for unit in UNITS}}
        manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
        existing = project.exists() or conf.exists() or any(p.exists() for p in assets.values())
        if existing and not manifest and not args.adopt_existing:
            raise RuntimeError('Unmarked partial installation: explicitly inspect/adopt it first')
        if existing:
            for name, path in assets.items():
                if path.exists() and digest(path) != digest(stage / name):
                    raise RuntimeError(f'Existing managed configuration differs: {path}')
            installed_proxy = project / 'pf1007l-lan-proxy.mjs'
            accepted = [digest(stage / 'proxy.mjs'), *meta.get('accepted_previous_proxy_sha256', [])]
            if manifest:
                accepted.append(manifest.get('proxy_sha256'))
            if installed_proxy.exists() and digest(installed_proxy) not in accepted:
                raise RuntimeError('Existing proxy source is not a recognized project version')
        # Own table may already exist on a repeat invocation; an unmarked table may not.
        tables = command(['nft', 'list', 'tables']).stdout
        if 'table inet pf1007l_proxy' in tables and not existing:
            raise RuntimeError('Unowned firewall table collision')
        listeners = command(['ss', '-H', '-lnt', 'sport = :8788']).stdout
        if listeners.strip() and unit_properties(UNITS[1]).get('ActiveState') != 'active':
            raise RuntimeError('Port 8788 occupied by an unexpected process')
        checkpoint('preflight passed; prior artifacts recognized')
        state['runtime_installed_now'] = ensure_runtime(stage, project, meta)
        conf.mkdir(mode=0o755, parents=True, exist_ok=True)
        secret = conf / 'dashboard-key'
        if secret.exists():
            stat = secret.stat()
            if secret.is_symlink() or stat.st_uid != 0 or stat.st_mode & 0o077:
                raise RuntimeError('Existing source credential is not root-private')
        else:
            source = stage / 'dashboard-key'
            if not source.is_file():
                raise RuntimeError('No staged credential; existing credential will never be replaced automatically')
            atomic_copy(source, secret, 0o600)
        if (stage / 'dashboard-key').exists():
            (stage / 'dashboard-key').unlink()  # only this task's temporary copy
        changed = atomic_copy(stage / 'proxy.mjs', project / 'pf1007l-lan-proxy.mjs')
        for name in ['config.json', 'firewall.nft']:
            atomic_copy(stage / name, assets[name])
        config = json.loads((conf / 'config.json').read_text())
        if config.get('demoOnly') is not True or config.get('allowApiWrites') is not False:
            raise RuntimeError('Demo-only/read-only policy required')
        command([str(project / 'node/bin/node'), '--check', str(project / 'pf1007l-lan-proxy.mjs')])
        command(['nft', '--check', '--file', str(conf / 'firewall.nft')])
        checkpoint('runtime, source, protected credential, demo policy and firewall syntax verified')
        changed_units = register_units(stage, unit_dir)
        command(['systemd-analyze', 'verify', *[str(unit_dir / unit) for unit in UNITS]])
        checkpoint('all unit files registered and verified after daemon-reload')
        # Exercise LoadCredential with a transient project-only DynamicUser unit
        # before starting a listener. It auto-collects and does not enable a service.
        command(['systemd-run', '--unit=pf1007l-proxy-preflight-' + str(os.getpid()),
                 '--wait', '--collect', '--pipe', '-p', 'DynamicUser=yes',
                 '-p', 'LoadCredential=dashboard-key:' + str(secret),
                 '-p', 'ProtectSystem=strict', '-p', 'ProtectHome=yes',
                 str(project / 'node/bin/node'), str(project / 'pf1007l-lan-proxy.mjs'),
                 str(conf / 'config.json'), '--check-config'])
        checkpoint('actual systemd credential access verified without opening a port')
        new_manifest = {'schema': 1, 'node_version': meta['version'],
                        'node_binary_sha256': meta['node_binary_sha256'],
                        'proxy_sha256': digest(project / 'pf1007l-lan-proxy.mjs')}
        write_state(manifest_path, new_manifest); manifest_path.chmod(0o600)
        key = secret.read_text().strip()
        request = urllib.request.Request('https://pf1007l-desk-dashboard.pages.dev/api/calendar',
                    headers={'Authorization': 'Bearer ' + key, 'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(request, timeout=20) as response:
            state['backend_authenticated_status'] = response.status
        if state['backend_authenticated_status'] != 200:
            raise RuntimeError('Backend authentication check failed')
        for unit in UNITS:
            reset_failed_if_needed(unit)
        active = unit_properties(UNITS[1]).get('ActiveState') == 'active'
        action = 'restart' if active and (changed or changed_units) else 'start'
        # Set before start: a failed start can still activate its firewall dependency.
        started = True
        command(['systemctl', action, UNITS[1]])
        health = wait_for_health()
        if unrelated_state() != state['before']:
            raise RuntimeError('Unrelated service/mount/filter state changed')
        state['ready'] = True; state['initial_health'] = health
        checkpoint('service healthy; unrelated state unchanged')
        if args.coordinate_proof:
            for name in ['interrupt-request', 'interrupt-stopped', 'interrupt-recovered', 'proof-complete.json']:
                marker = stage / name
                if marker.exists():
                    marker.rename(stage / (name + '.previous-' + str(time.time_ns())))
        print('PF1007L_INSTALL_READY', flush=True)
        if args.coordinate_proof:
            deadline = time.monotonic() + 1200
            interrupted = False
            while time.monotonic() < deadline:
                if (stage / 'interrupt-request').exists() and not interrupted:
                    command(['systemctl', 'stop', UNITS[1]])
                    (stage / 'interrupt-stopped').write_text('stopped\n'); time.sleep(5)
                    command(['systemctl', 'start', UNITS[1]])
                    wait_for_health()
                    (stage / 'interrupt-recovered').write_text('healthy\n')
                    interrupted = True; checkpoint('authorized proxy interruption completed')
                proof = stage / 'proof-complete.json'
                if proof.exists():
                    if json.loads(proof.read_text()).get('success') is not True:
                        raise RuntimeError('Physical proof failed; refusing boot enablement')
                    state['proof_success'] = True; break
                time.sleep(1)
            else:
                raise RuntimeError('Proof deadline elapsed; refusing boot enablement')
        else:
            # Routine repeat: do not silently enable boot without the prior accepted proof.
            if not manifest or not manifest.get('proof_success'):
                raise RuntimeError('Boot enablement requires coordinated physical acceptance')
        if unrelated_state() != state['before']:
            raise RuntimeError('Unrelated state changed during proof')
        command(['systemctl', 'enable', *UNITS])
        new_manifest['proof_success'] = True
        write_state(manifest_path, new_manifest); manifest_path.chmod(0o600)
        state['enabled'] = True; checkpoint('accepted demo service and guard enabled for boot')
        print('PF1007L_INSTALL_COMPLETE', flush=True)
    except Exception as error:
        state['error'] = str(error)
        if started:
            command(['systemctl', 'stop', UNITS[1]], check=False)
            command(['systemctl', 'stop', UNITS[0]], check=False)
        state['journal'] = command(['journalctl', '-u', 'pf1007l-proxy', '--no-pager', '-n', '60'], check=False).stdout
        write_state(state_path, state)
        print('PF1007L_INSTALL_FAILED: ' + str(error), flush=True)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
