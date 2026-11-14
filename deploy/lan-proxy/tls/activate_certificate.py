#!/usr/bin/env python3
"""Validate then atomically activate; failed HTTPS restart restores prior bundle."""
import http.client
import socket
import json
import hashlib
import os
from pathlib import Path
import re
import ssl
import subprocess
import sys
import time
import urllib.request
from acme_common import ROOT, ACME, profile, private_read

UNIT = 'pf1007l-proxy-https.service'


def command(args):
    result = subprocess.run(args, capture_output=True, timeout=20)
    if result.returncode:
        raise ValueError('Certificate validation/service operation failed')
    return result.stdout


def validate(lineage, hostname, roots, run=command):
    lineage = Path(lineage)
    key = lineage / 'privkey.pem'
    # Certbot's live files are symlinks into its root-private archive.
    private_read(key.resolve())
    chain = lineage / 'fullchain.pem'
    if not roots.is_file():
        raise ValueError('Frame public root bundle is required')
    run(['openssl', 'x509', '-in', str(chain), '-checkend', str(30 * 86400), '-noout'])
    cert_public = run(['openssl', 'x509', '-in', str(chain), '-pubkey', '-noout'])
    key_public = run(['openssl', 'pkey', '-in', str(key), '-pubout'])
    if cert_public != key_public:
        raise ValueError('Certificate/private key mismatch')
    run(['openssl', 'verify', '-CAfile', str(roots), '-no-CApath', '-no-CAstore',
         '-purpose', 'sslserver', '-verify_hostname', hostname,
         '-untrusted', str(chain), str(chain)])


def switch(link, target):
    temporary = link.with_name(link.name + '.next')
    if temporary.exists() or temporary.is_symlink():
        raise ValueError('Unexpected activation temporary path')
    temporary.symlink_to(target)
    temporary.replace(link)


def activate(lineage, hostname, roots, base, restart, probe, run=command, stop=lambda: None):
    lineage, base = Path(lineage), Path(base)
    validate(lineage, hostname, Path(roots), run)
    base.mkdir(mode=0o700, parents=True, exist_ok=True)
    if base.is_symlink() or base.stat().st_mode & 0o077 or base.stat().st_uid != os.geteuid():
        raise ValueError('Certificate directory must be owner-private')
    version = hashlib.sha256((lineage / 'fullchain.pem').read_bytes()).hexdigest()
    bundle = base / version
    if not bundle.exists():
        bundle.mkdir(mode=0o700)
        for source, name in [('fullchain.pem', 'tls-chain'), ('privkey.pem', 'tls-key')]:
            path = bundle / name
            path.write_bytes((lineage / source).read_bytes()); path.chmod(0o600)
    else:
        if bundle.is_symlink() or any((bundle / name).read_bytes() != (lineage / source).read_bytes()
           for source, name in [('fullchain.pem', 'tls-chain'), ('privkey.pem', 'tls-key')]):
            raise ValueError('Existing bundle collision')
    current = base / 'current'
    if current.exists() and not current.is_symlink():
        raise ValueError('Current certificate is not a managed link')
    old = current.readlink() if current.is_symlink() else None
    if old is not None and (old.is_absolute() or old.name != str(old) or not re.fullmatch(r'[0-9a-f]{64}', str(old))):
        raise ValueError('Unexpected previous certificate link')
    if old == Path(version):
        # Retry a prior incomplete activation too; never declare success on the
        # link alone (the service might not have loaded this bundle yet).
        restart(); probe(); return
    switch(current, version)
    try:
        restart(); probe()
    except Exception:
        if old is None:
            stop()
            current.unlink()
        else:
            switch(current, old)
            restart(); probe()
        raise ValueError('Activation failed; previous certificate restored where available')
    if old is not None:
        switch(base / 'previous', old)


def apply_running_material():
    active = subprocess.run(['systemctl', 'is-active', '--quiet', UNIT]).returncode == 0
    path = Path('/run/pf1007l-proxy-https/reload.sock')
    if active and path.is_socket():
        body = json.dumps({'key': private_read(ROOT / 'certificates/current/tls-key'),
                           'chain': (ROOT / 'certificates/current/tls-chain').read_text()})
        connection = http.client.HTTPConnection('localhost', timeout=8)
        connection.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        connection.sock.settimeout(8); connection.sock.connect(str(path))
        try:
            connection.request('POST', '/reload', body, {'Content-Type': 'application/json'})
            response = connection.getresponse(); response.read()
            if response.status != 200: raise ValueError('Protected certificate reload rejected')
        finally: connection.close()
    else:
        command(['systemctl', 'restart', UNIT])


def main():
    try:
        if os.geteuid() != 0:
            raise ValueError('Root required')
        cfg = profile()
        expected = ACME / 'config/live/pf1007l-desk'
        lineage = Path(os.environ.get('RENEWED_LINEAGE', ''))
        if lineage != expected:
            raise ValueError('Unexpected certificate lineage')
        for name in ('fullchain.pem', 'privkey.pem'):
            if not (lineage / name).resolve().is_relative_to(ACME / 'config/archive/pf1007l-desk'):
                raise ValueError('Unexpected certificate source path')
        def restart():
            apply_running_material()
        def probe():
            context = ssl.create_default_context(cafile=str(ROOT / 'frame-roots.pem'))
            deadline = time.monotonic() + 35
            while time.monotonic() < deadline:
                try:
                    from monitor import endpoint
                    peer, health = endpoint(cfg)
                    expected = command(['openssl', 'x509', '-in', str(ROOT / 'certificates/current/tls-chain'), '-outform', 'DER'])
                    if hashlib.sha256(peer).digest() == hashlib.sha256(expected).digest(): return
                except Exception:
                    time.sleep(.5)
            raise ValueError('HTTPS health did not recover')
        activate(lineage, cfg['hostname'], ROOT / 'frame-roots.pem', ROOT / 'certificates', restart, probe,
                 stop=lambda: command(['systemctl', 'stop', UNIT]))
        print('PF1007L certificate activated; hostname, frame trust, key pair and HTTPS health verified.')
        return 0
    except Exception:
        # No certificate material, key details, URLs with tokens or client logs.
        print('PF1007L certificate activation failed; HTTP fallback unchanged.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
