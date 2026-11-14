#!/usr/bin/env python3
"""Prepare/run a native Terminal SSH installer command without hiding failures."""
import argparse
from pathlib import Path
import shlex
import subprocess
import time


def terminal_script(ssh_args, log_path, tee='/usr/bin/tee'):
    return '\n'.join([
        '#!/bin/bash', 'set -uo pipefail', 'umask 077',
        shlex.join(ssh_args) + ' | ' + shlex.quote(tee) + ' ' + shlex.quote(str(log_path)),
        'pipeline_status=("${PIPESTATUS[@]}")',
        'ssh_status="${pipeline_status[0]}"', 'tee_status="${pipeline_status[1]}"',
        'printf "\\nPF1007L_SSH_EXIT=%s PF1007L_TEE_EXIT=%s\\n" "$ssh_status" "$tee_status"',
        'if [ "$ssh_status" -ne 0 ]; then exit "$ssh_status"; fi',
        'exit "$tee_status"', '',
    ])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', required=True)
    parser.add_argument('--output-directory', type=Path, required=True)
    parser.add_argument('--open-terminal', action='store_true')
    args = parser.parse_args()
    output = args.output_directory.resolve(); output.mkdir(mode=0o700, parents=True, exist_ok=True)
    remote = shlex.join(['sudo', '--', 'python3', args.stage + '/install_host.py',
                         '--stage', args.stage, '--adopt-existing', '--coordinate-proof'])
    ssh = ['ssh', '-tt', '-S', '/private/tmp/pf1007l-server-ssh/control',
           '-o', 'StrictHostKeyChecking=yes', 'hub@10.157.1.115', remote]
    log = output / 'corrected-installer-terminal.txt'
    if log.exists():
        archive = log.with_name('corrected-installer-terminal-' + str(time.time_ns()) + '.txt')
        archive.write_bytes(log.read_bytes()); archive.chmod(0o600)
    script = output / 'run-corrected-installer.sh'
    script.write_text(terminal_script(ssh, output / 'corrected-installer-terminal.txt')); script.chmod(0o700)
    print('Prepared:', script)
    if args.open_terminal:
        command = shlex.join(['/bin/bash', str(script)])
        apple = 'tell application "Terminal"\nactivate\ndo script "' + command.replace('\\', '\\\\').replace('"', '\\"') + '"\nend tell'
        subprocess.run(['osascript', '-e', apple], check=True)


if __name__ == '__main__':
    main()
