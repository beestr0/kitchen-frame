#!/usr/bin/env python3
"""Project-only issuance/renewal. No staging/force-renewal or default CA fallback."""
import fcntl
import configparser
import json
import time
import os
from pathlib import Path
import socket
import signal
import urllib.request
import urllib.parse
import subprocess
import sys
from acme_common import ROOT, ACME, profile, private_read


def arguments(action, hostname):
    common = ['/opt/pf1007l-tls/venv/bin/certbot', '--config', str(ROOT / 'acme.ini'),
              '--config-dir', str(ACME / 'config'), '--work-dir', str(ACME / 'work'),
              '--logs-dir', str(ACME / 'logs'), '--cert-name', 'pf1007l-desk',
              '--deploy-hook', '/opt/pf1007l-tls/activate_certificate.py']
    if action == 'issue':
        return common + ['certonly', '--authenticator', 'manual', '--preferred-challenges', 'dns-01',
                         '--manual-auth-hook', '/opt/pf1007l-tls/dns_hook.py auth',
                         '--manual-cleanup-hook', '/opt/pf1007l-tls/dns_hook.py cleanup',
                         '--domains', hostname]
    if action == 'renew':
        return common + ['renew']
    raise ValueError('Only issue or renew is allowed')


def published_lan_address(cfg):
    # Query only this project's public records over validated HTTPS when the
    # gateway filters RFC1918 answers. Do not alter Linux/router resolver settings.
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(cfg['hostname'], 8789, type=socket.SOCK_STREAM)}
        if addresses == {cfg['address']}: return True
    except OSError: pass
    records={}
    for kind in ['A','AAAA']:
        url='https://dns.google/resolve?'+urllib.parse.urlencode({'name':cfg['hostname'],'type':kind})
        with urllib.request.urlopen(url,timeout=12) as response: value=json.load(response)
        if value.get('Status')!=0: return False
        records[kind]={answer['data'] for answer in value.get('Answer',[]) if answer.get('type')==(1 if kind=='A' else 28)}
    return records['A']=={cfg['address']} and not records['AAAA']


def run_client(args):
    started=time.time();deadline=time.monotonic()+840
    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    while time.monotonic()<deadline:
        try:
            stdout,stderr=process.communicate(timeout=2)
            return subprocess.CompletedProcess(args,process.returncode,stdout,stderr)
        except subprocess.TimeoutExpired:
            status=ROOT/'dns-hook-status.json'
            if status.exists() and status.stat().st_mtime>=started:break
    os.killpg(process.pid,signal.SIGTERM)
    try:stdout,stderr=process.communicate(timeout=15)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid,signal.SIGKILL);stdout,stderr=process.communicate()
    return subprocess.CompletedProcess(args,1,stdout,stderr+b'\nCertificate operation stopped after DNS-hook failure or deadline.\n')


def main():
    try:
        os.umask(0o077)
        if os.geteuid() != 0:
            raise ValueError('Root required for private certificate state')
        cfg = profile()
        ini = private_read(ROOT / 'acme.ini')
        parsed = configparser.ConfigParser(interpolation=None)
        parsed.read_string('[acme]\n' + ini)
        if parsed['acme'].get('server') != 'https://acme.zerossl.com/v2/DV90' or parsed['acme'].get('domains') != cfg['hostname']:
            raise ValueError('Explicit ZeroSSL ACME and single hostname configuration required')
        if not published_lan_address(cfg):
            raise ValueError('Published hostname must point only to the reviewed LAN address')
        ACME.mkdir(mode=0o700, parents=True, exist_ok=True)
        if ACME.is_symlink() or ACME.stat().st_uid != 0 or ACME.stat().st_mode & 0o077:
            raise ValueError('ACME state directory must be root-private')
        with (ACME / 'run.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # DNS hook prints only sanitized errors. Certbot config has credentials,
            # never arguments; all client logs remain in the private state directory.
            result = run_client(arguments(sys.argv[1], cfg['hostname']))
            (ACME / 'last-run.log').write_bytes(result.stdout + result.stderr)
            (ACME / 'last-run.log').chmod(0o600)
            if result.returncode:
                raise ValueError('Certificate client failed')
        # Certbot/hook exit behavior must not conceal a failed deployment.
        issued = ACME / 'config/live/pf1007l-desk/fullchain.pem'
        active = ROOT / 'certificates/current/tls-chain'
        if issued.read_bytes() != active.read_bytes():
            raise ValueError('Issued certificate is not the active certificate')
        fresh = subprocess.run(['openssl', 'x509', '-in', str(active), '-checkend', str(21 * 86400), '-noout'], capture_output=True)
        if fresh.returncode:
            raise ValueError('Active certificate expiry needs attention')
        receipt = ACME / 'run-status.json'
        receipt.write_text(json.dumps({'checkedAt': time.time(), 'success': True}))
        receipt.chmod(0o600)
        print('PF1007L ACME completed; active certificate and expiry verified.')
        return 0
    except Exception:
        if ACME.is_dir():
            receipt = ACME / 'run-status.json'
            receipt.write_text(json.dumps({'checkedAt': time.time(), 'success': False}))
            receipt.chmod(0o600)
        print('PF1007L ACME failed; private logs retained. No HTTP fallback or TLS bypass.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
