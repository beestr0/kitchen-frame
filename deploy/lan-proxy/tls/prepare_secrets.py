#!/usr/bin/env python3
"""Linux native-TTY credential entry; preserve valid fields, replace EAB on request."""
import argparse
import base64
import configparser
import getpass
import json
import os
from pathlib import Path
import re
import sys
from acme_common import ROOT, HOST, private_read


def save(path, text):
    if path.is_symlink():raise ValueError('Unexpected credential symlink')
    temporary=path.with_name(path.name+'.new')
    with temporary.open('x') as stream:stream.write(text)
    temporary.chmod(0o600);temporary.replace(path)


def hidden(prompt, valid, transform=lambda value:value):
    while True:
        value=getpass.getpass(prompt).strip()
        try:
            value=transform(value)
            if valid(value):return value
        except (ValueError,TypeError):pass
        print('Format not accepted. Copy this field again; its value has not been displayed.')


def normalized_hmac(value):
    if not re.fullmatch(r'[A-Za-z0-9_+/=-]+',value):raise ValueError('Invalid HMAC encoding')
    decoded=base64.b64decode(value.replace('-','+').replace('_','/')+'='*((-len(value))%4),validate=True)
    if not 16<=len(decoded)<=256:raise ValueError('Invalid HMAC length')
    return base64.urlsafe_b64encode(decoded).decode().rstrip('=')


def collect(hostname,correct_eab):
    os.umask(0o077);ROOT.mkdir(mode=0o700,parents=True,exist_ok=True)
    if ROOT.is_symlink() or ROOT.stat().st_uid!=os.geteuid() or ROOT.stat().st_mode&0o077:
        raise SystemExit('Configuration directory must be root-private.')
    expected={'hostname':hostname,'address':'10.157.1.115'}
    if (ROOT/'profile.json').exists():
        if json.loads(private_read(ROOT/'profile.json'))!=expected:raise SystemExit('Existing profile differs; refusing to overwrite it.')
    else:save(ROOT/'profile.json',json.dumps(expected,indent=2))
    print('Approved hostname: '+hostname+'; existing working services remain untouched.',flush=True)
    ini=ROOT/'acme.ini';cfg={}
    if ini.exists():
        parsed=configparser.ConfigParser(interpolation=None);parsed.read_string('[acme]\n'+private_read(ini));cfg=dict(parsed['acme'])
        if cfg.get('server')!='https://acme.zerossl.com/v2/DV90' or cfg.get('domains')!=hostname:
            raise SystemExit('Existing certificate profile differs; refusing unrelated changes.')
    if correct_eab and ini.exists():
        cfg.pop('eab-kid',None);cfg.pop('eab-hmac-key',None)
        save(ini,'\n'.join(k+' = '+v for k,v in cfg.items())+'\n')
        print('Previous EAB pair discarded; other configuration preserved.',flush=True)
    token=ROOT/'duckdns-token'
    if token.exists():
        if not re.fullmatch(r'[A-Za-z0-9-]{16,128}',private_read(token).strip()):raise SystemExit('Existing DNS token needs separate correction; not overwritten.')
        print('Existing DuckDNS token preserved.',flush=True)
    else:
        value=hidden('DuckDNS token (hidden; saved immediately): ',lambda x:bool(re.fullmatch(r'[A-Za-z0-9-]{16,128}',x)))
        save(token,value+'\n')
    email_file=ROOT/'account-email'
    email=cfg.get('email') or (private_read(email_file).strip() if email_file.exists() else None)
    if not email:
        email=hidden('ZeroSSL account email (hidden): ',lambda x:bool(re.fullmatch(r'[^\s=@]+@[^\s=]+\.[^\s=]+',x)))
        save(email_file,email+'\n')
    else:print('Existing account email preserved.',flush=True)
    if not correct_eab and cfg.get('eab-kid') and cfg.get('eab-hmac-key'):
        print('Existing EAB pair preserved; no credential changes needed.');return
    kid=hidden('Correct ZeroSSL ACME EAB Key ID (hidden): ',lambda x:bool(re.fullmatch(r'[A-Za-z0-9_./:=+-]{1,1024}',x)))
    hmac=hidden('Matching ZeroSSL ACME EAB HMAC key (hidden): ',lambda x:bool(x),normalized_hmac)
    cfg.update({'server':'https://acme.zerossl.com/v2/DV90','email':email,'eab-kid':kid,'eab-hmac-key':hmac,
        'agree-tos':'true','non-interactive':'true','key-type':'rsa','rsa-key-size':'2048','domains':hostname})
    save(ini,'\n'.join(k+' = '+v for k,v in cfg.items())+'\n')
    print('Corrected EAB pair saved privately. No DNS, certificate or service operation was run by this collector.',flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--hostname',default='beestr0.duckdns.org');parser.add_argument('--correct-eab',action='store_true');args=parser.parse_args()
    if sys.platform!='linux' or os.geteuid()!=0 or not os.isatty(0):
        raise SystemExit('Use interactive native Terminal sudo on Linux.')
    hostname=args.hostname.strip().lower()
    if not HOST.fullmatch(hostname):raise SystemExit('Invalid approved hostname.')
    collect(hostname,args.correct_eab)


if __name__=='__main__':
    try:main()
    except KeyboardInterrupt:
        print('\nSecure entry cancelled; previously saved valid fields are preserved.');raise SystemExit(130)
