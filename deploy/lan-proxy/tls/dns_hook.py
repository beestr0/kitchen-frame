#!/usr/bin/env python3
"""Certbot DNS-01 hook: only one reviewed DuckDNS hostname; no IP updates/log URLs."""
import os
import json
import hashlib
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from acme_common import ROOT, private_read, profile


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('DNS API redirects are forbidden')


def dig(name, kind, server=None):
    args = ['dig', '+time=3', '+tries=1', '+noall', '+comments', '+answer']
    if server:
        args.append('@' + server)
    result = subprocess.run(args + [name, kind], capture_output=True, text=True, timeout=8)
    status = re.search(r'status: ([A-Z]+)', result.stdout)
    if result.returncode or not status or status[1] not in ['NOERROR', 'NXDOMAIN']:
        raise ValueError('DNS query failed')
    values = []
    for line in result.stdout.splitlines():
        if line.startswith(';') or not line.strip():
            continue
        fields = shlex.split(line)
        if len(fields) >= 5 and fields[3] == kind:
            values.append(''.join(fields[4:]) if kind == 'TXT' else fields[4].rstrip('.'))
    return set(values)


def public_txt(name, kind, server):
    if kind != 'TXT': raise ValueError('Only challenge TXT lookups are allowed')
    endpoints={'google':'https://dns.google/resolve','cloudflare':'https://cloudflare-dns.com/dns-query'}
    url=endpoints[server]+'?'+urllib.parse.urlencode({'name':name,'type':'TXT'})
    request=urllib.request.Request(url,headers={'Accept':'application/dns-json'})
    with urllib.request.build_opener(NoRedirect()).open(request,timeout=12) as response:value=json.load(response)
    if value.get('Status') not in (0,3): raise ValueError('Public TXT lookup failed')
    return {''.join(shlex.split(answer['data'])) for answer in value.get('Answer',[]) if answer.get('type')==16}


def update(label, token, txt, clear=False):
    query = {'domains': label, 'token': token, 'txt': txt}
    if clear:
        query['clear'] = 'true'
    # Token is confined to an authenticated HTTPS request; never a subprocess argument.
    url = 'https://www.duckdns.org/update?' + urllib.parse.urlencode(query)
    opener = urllib.request.build_opener(NoRedirect())
    with opener.open(url, timeout=15) as response:
        if response.read(128).decode().strip() != 'OK':
            raise ValueError('DNS provider refused update')


def apply(action, hostname, validation, token, query=dig, writer=update, timeout=600, resolvers=None, owned_hashes=None):
    if action not in ('auth', 'cleanup') or not re.fullmatch(r'[A-Za-z0-9_-]{43}', validation):
        raise ValueError('Invalid DNS challenge')
    authorities = sorted(resolvers or query('duckdns.org', 'NS'))
    if not authorities:
        raise ValueError('No authoritative DNS servers found')
    name = '_acme-challenge.' + hostname
    values = [query(name, 'TXT', server) for server in authorities]
    owned_hashes=set(owned_hashes or [])
    if any(any(item!=validation and hashlib.sha256(item.encode()).hexdigest() not in owned_hashes for item in value) for value in values):
        raise ValueError('Refusing to overwrite another TXT challenge')
    if action == 'cleanup':
        # No clear of A/AAAA: the TXT API is explicitly selected by the txt parameter.
        if any(value-{validation} for value in values): return
        if any(validation in value for value in values):
            writer(hostname.split('.')[0], token, '', clear=True)
        return
    writer(hostname.split('.')[0], token, validation)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if all(query(name, 'TXT', server) == {validation} for server in authorities):
            return
        time.sleep(5)
    raise ValueError('Authoritative TXT propagation deadline exceeded')


def main():
    try:
        cfg = profile()
        hostname = os.environ.get('CERTBOT_IDENTIFIER', os.environ.get('CERTBOT_DOMAIN', ''))
        identifiers = os.environ.get('CERTBOT_ALL_IDENTIFIERS', os.environ.get('CERTBOT_ALL_DOMAINS', ''))
        if hostname != cfg['hostname'] or {item.strip() for item in identifiers.split(',') if item.strip()} != {hostname}:
            raise ValueError('Only the reviewed single hostname is allowed')
        token = private_read(ROOT / 'duckdns-token').strip()
        if not re.fullmatch(r'[A-Za-z0-9-]{16,128}', token):
            raise ValueError('Invalid DNS credential format')
        ownership=ROOT/'challenge-ownership.json'
        owned=json.loads(ownership.read_text()) if ownership.exists() else []
        validation=os.environ.get('CERTBOT_VALIDATION','')
        if re.fullmatch(r'[A-Za-z0-9_-]{43}',validation):
            owned=list(dict.fromkeys([*owned,hashlib.sha256(validation.encode()).hexdigest()]))[-16:]
            ownership.write_text(json.dumps(owned));ownership.chmod(0o600)
        apply(sys.argv[1], hostname, validation, token,
              query=public_txt, resolvers=['google','cloudflare'],owned_hashes=owned)
        return 0
    except Exception as error:
        safe={'Only the reviewed single hostname is allowed','Invalid DNS credential format','Invalid DNS challenge','No authoritative DNS servers found','Refusing to overwrite another TXT challenge','Authoritative TXT propagation deadline exceeded','DNS provider refused update','DNS API redirects are forbidden','Public TXT lookup failed'}
        reason=str(error) if str(error) in safe else type(error).__name__
        status={'error':reason,'identifierMatches':os.environ.get('CERTBOT_IDENTIFIER',os.environ.get('CERTBOT_DOMAIN',''))==locals().get('cfg',{}).get('hostname'),'identifierCount':len(os.environ.get('CERTBOT_ALL_IDENTIFIERS',os.environ.get('CERTBOT_ALL_DOMAINS','')).split(',')),'validationLength':len(os.environ.get('CERTBOT_VALIDATION',''))}
        try:
            if ROOT.is_dir():
                (ROOT/'dns-hook-status.json').write_text(json.dumps(status));(ROOT/'dns-hook-status.json').chmod(0o600)
        except OSError: pass
        # urllib exceptions can include the credential-bearing URL. Never print them.
        print('PF1007L DNS hook failed; check account/configuration/DNS, without verbose logging.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
