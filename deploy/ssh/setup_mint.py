#!/usr/bin/env python3
"""Run in native Mac Terminal. Never reads or prints private key contents."""
import os
from pathlib import Path
import stat
import subprocess
import sys

ALIAS = 'pf1007l-mint'
KEY_NAME = 'id_ed25519_pf1007l_mint'


def run(args):
    subprocess.run(args, check=True)


def configure(directory):
    directory.mkdir(mode=0o700, exist_ok=True)
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise ValueError('SSH directory must be an owned real directory')
    directory.chmod(0o700)
    config = directory / 'config'
    marker = '# PF1007L dedicated Mint connection'
    block = f'''{marker}
Host {ALIAS}
    HostName 10.157.1.115
    User hub
    Port 22
    IdentityFile ~/.ssh/{KEY_NAME}
    IdentitiesOnly yes
    StrictHostKeyChecking yes
    AddKeysToAgent yes
    UseKeychain yes
    ControlMaster no
    ControlPath none
    ConnectTimeout 10
# End PF1007L dedicated Mint connection

'''
    if config.is_symlink():
        raise ValueError('Review symlinked SSH config manually')
    original = config.read_text() if config.exists() else ''
    if marker in original:
        if not original.startswith(block):
            raise ValueError('Existing project SSH block differs; review it before changing')
        return
    # Do not shadow an existing alias or pattern with an inferred replacement.
    effective = subprocess.run(['ssh', '-G', ALIAS], capture_output=True, text=True, check=True).stdout
    if f'hostname {ALIAS}\n' not in effective:
        raise ValueError('Alias already configured; review before changing')
    if original:
        backup = directory / 'config.before-pf1007l'
        fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as stream:
            stream.write(original)
    # Preserve unrelated contents exactly; prepend so a broad Host * cannot win first.
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(config, flags, 0o600)
    with os.fdopen(fd, 'w') as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(block + original)


def main():
    if sys.platform != 'darwin' or not sys.stdin.isatty() or not sys.stderr.isatty():
        raise SystemExit('Use a private native Mac Terminal, without recording or tee.')
    os.umask(0o077)
    directory = Path.home() / '.ssh'
    directory.mkdir(mode=0o700, exist_ok=True)
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise ValueError('SSH directory must be an owned real directory')
    directory.chmod(0o700)
    key = directory / KEY_NAME
    if key.is_symlink() or key.with_suffix('.pub').is_symlink():
        raise ValueError('Refusing symlinked project keys')
    if not key.exists():
        if key.with_suffix('.pub').exists():
            raise ValueError('Public key exists without private key; review manually')
        print('Create the dedicated key. A passphrase stored in macOS Keychain is recommended.', flush=True)
        run(['ssh-keygen', '-t', 'ed25519', '-a', '100', '-f', str(key), '-C', 'pf1007l-mint-project'])
    if not key.with_suffix('.pub').is_file():
        raise ValueError('Project public key missing; existing private key preserved')
    if key.stat().st_uid != os.getuid():
        raise ValueError('Project key must be owned by this Mac user')
    key.chmod(0o600)
    key.with_suffix('.pub').chmod(0o644)
    run(['ssh-keygen', '-l', '-f', str(key.with_suffix('.pub'))])
    configure(directory)
    print('Unlock only the project key and save its passphrase in the login Keychain.', flush=True)
    run(['ssh-add', '--apple-use-keychain', str(key)])
    print('Install only this public key. Enter the Mint account password here if requested.', flush=True)
    run(['ssh-copy-id', '-i', str(key.with_suffix('.pub')), ALIAS])
    run(['ssh', '-o', 'BatchMode=yes', ALIAS, 'id -un'])
    print('PF1007L_PERSISTENT_SSH_VERIFIED', flush=True)


if __name__ == '__main__':
    try:
        main()
    except (Exception, KeyboardInterrupt):
        print('Setup incomplete. Existing keys preserved; resolve the Terminal error before retrying.', file=sys.stderr)
        sys.exit(1)
