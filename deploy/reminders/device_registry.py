#!/usr/bin/env python3
"""Offline public-key registry editor; no networking, enrollment endpoint or secrets."""
import argparse
import copy
import json
import os
from pathlib import Path
import sqlite3
import tempfile

from device_auth import DeviceAuth, device_id


def validate(registry):
    database = sqlite3.connect(':memory:')
    try:
        DeviceAuth(database, registry, 'https://registry-validation.invalid', 'validation-only-not-a-session-secret'*2)
    finally: database.close()
    return registry


def change(registry, action, fingerprint, public_key=None):
    validate(registry)
    updated = copy.deepcopy(registry)
    entry = next((x for x in updated['devices'] if x['id'] == fingerprint), None)
    if action == 'enroll':
        if device_id(public_key) != fingerprint:
            raise ValueError('Public-key fingerprint does not match the physical device')
        if entry:
            raise ValueError('Device already registered; use rotate to re-enable explicitly')
        updated['devices'].append({'id':fingerprint, 'publicKey':public_key, 'enabled':True, 'epoch':1})
    elif action in ('revoke', 'rotate'):
        if entry is None: raise ValueError('Device is not registered')
        entry['enabled'] = action == 'rotate'
        entry['epoch'] = entry.get('epoch',1) + 1
    else: raise ValueError('Unknown registry action')
    return validate(updated)


def save(path, registry):
    validate(registry)
    path = Path(path)
    if path.is_symlink() or (path.exists() and (not path.is_file() or path.stat().st_mode & 0o077 or path.stat().st_uid != os.geteuid())):
        raise ValueError('Registry must be a regular owner-private file')
    if path.parent.is_symlink() or not path.parent.is_dir() or path.parent.stat().st_mode & 0o077 or path.parent.stat().st_uid != os.geteuid():
        raise ValueError('Registry directory must be owner-private')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', prefix='.registry-', dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            os.fchmod(stream.fileno(),0o600)
            json.dump(registry, stream, indent=2); stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary,path)
        directory = os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try: os.fsync(directory)
        finally: os.close(directory)
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['enroll','revoke','rotate'])
    parser.add_argument('--registry',type=Path,required=True)
    parser.add_argument('--fingerprint',required=True,help='SHA256 SPKI fingerprint checked on physical frame')
    parser.add_argument('--public-key-file',type=Path,help='Public SPKI base64 only; never a private key')
    args = parser.parse_args()
    if args.registry.is_symlink(): raise ValueError('Registry symlinks are forbidden')
    if args.registry.exists() and args.registry.stat().st_mode & 0o077:
        raise ValueError('Existing registry permissions are too broad')
    registry = json.loads(args.registry.read_text()) if args.registry.exists() else {'version':1,'devices':[]}
    public_key = args.public_key_file.read_text().strip() if args.public_key_file else None
    save(args.registry,change(registry,args.action,args.fingerprint,public_key))
    print('Public registry updated. Reload only the demo bridge to apply revocation/enrollment.')


if __name__ == '__main__': main()
