"""Shared, non-logging validation for this deployment's private certificate state."""
import json
import os
from pathlib import Path
import re

ROOT = Path('/etc/pf1007l-tls')
ACME = Path('/var/lib/pf1007l-acme')
HOST = re.compile(r'^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.duckdns\.org$')


def private_read(path):
    path = Path(path)
    info = path.lstat()
    if path.is_symlink() or info.st_mode & 0o077 or info.st_uid != os.geteuid():
        raise ValueError('Credential must be an owner-private regular file')
    if not path.is_file():
        raise ValueError('Credential must be a regular file')
    return path.read_text()


def profile(path=ROOT / 'profile.json'):
    value = json.loads(Path(path).read_text())
    if not HOST.fullmatch(value.get('hostname', '')) or value.get('address') != '10.157.1.115':
        raise ValueError('Configure one registered DuckDNS hostname and the reviewed LAN address')
    return value
