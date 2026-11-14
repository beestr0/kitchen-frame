#!/usr/bin/env python3
"""Verify existing private Serve without reinstalling or changing any configuration."""
import base64
import http.client
import json
import os
from pathlib import Path
import runpy
import socket
import ssl
import sys
import xml.etree.ElementTree as ET

import install_demo as pilot

HOST = 'hub-inspiron-5570.tailb76e1b.ts.net'
ADDRESS = '100.76.50.37'
PATH = '/pf1007l-demo/pf1007l-test/'


class TailnetHTTPS(http.client.HTTPSConnection):
    def connect(self):
        # Tailscale 1.104+ intentionally binds Serve to tailscale0. Same-host
        # checks must also bind their client socket, rather than weaken Serve.
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.settimeout(self.timeout)
        try:
            transport.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, b'tailscale0\0')
            transport.connect((ADDRESS, 443))
            self.sock = self._context.wrap_socket(transport, server_hostname=HOST)
        except BaseException:
            transport.close()
            raise


def dav(method, path, password=None):
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    connection = TailnetHTTPS(HOST, timeout=15, context=context)
    headers = {'Depth': '0'}
    if password:
        headers['Authorization'] = 'Basic ' + base64.b64encode(('pf1007l-demo:' + password).encode()).decode()
    body = b'<D:propfind xmlns:D="DAV:"><D:prop><D:displayname/><D:resourcetype/></D:prop></D:propfind>'
    try:
        connection.connect()
        certificate = connection.sock.getpeercert()
        tls = connection.sock.version()
        connection.request(method, path, body, headers)
        response = connection.getresponse()
        data = response.read(2 * 1024 * 1024 + 1)
        if len(data) > 2 * 1024 * 1024:
            raise RuntimeError('Bounded verification response exceeded')
        return response.status, data, certificate, tls
    finally:
        connection.close()


def main():
    if os.geteuid() != 0 or not os.isatty(0):
        raise RuntimeError('Private native SSH sudo TTY required')
    account = json.loads((pilot.ETC / 'demo-account.json').read_text())
    if account.get('username') != 'pf1007l-demo':
        raise RuntimeError('Unexpected demo account')
    serve = json.loads(pilot.run(['tailscale', 'serve', 'status', '--json']))
    if any(serve.get('AllowFunnel', {}).values()):
        raise RuntimeError('Unexpected Funnel configuration')
    proxy = serve.get('Web', {}).get(HOST + ':443', {}).get('Handlers', {}).get('/', {}).get('Proxy')
    if proxy != 'http://127.0.0.1:5238':
        raise RuntimeError('Unexpected private Serve mapping')
    for credential in (None, 'incorrect-demo-verification-password'):
        if dav('PROPFIND', PATH, credential)[0] != 401:
            raise RuntimeError('Unauthorized CalDAV access not rejected')
    code, body, cert, tls = dav('PROPFIND', PATH, account['password'])
    if code != 207:
        raise RuntimeError('Authenticated CalDAV check failed')
    xml = ET.fromstring(body)
    if not any(p.text == 'PF1007L Test' for p in xml.iter('{DAV:}displayname')):
        raise RuntimeError('Expected demo collection unavailable')
    denied = dav('PROPFIND', '/another-user/', account['password'])[0]
    if denied not in (403, 404):
        raise RuntimeError('Collection-owner isolation failed')
    for service in [pilot.UNIT, 'pf1007l-proxy.service', 'pf1007l-proxy-https.service', 'jellyfin', 'tailscaled']:
        if pilot.run(['systemctl', 'is-active', service]).strip() != 'active':
            raise RuntimeError('Existing service baseline changed')
    pilot.status('tailnet-https-demo-ready', hostname=HOST, port=443, username='pf1007l-demo',
                 accountPath='/pf1007l-demo/', collection='PF1007L Test',
                 tls='system-CA-and-hostname-verified', tlsVersion=tls,
                 certificateExpires=cert.get('notAfter'),
                 missingAndWrongPasswordRejected=True, ownerIsolation=True, funnel=False,
                 existingListPreserved=True, iphone='not-configured')
    print('PF1007L_PRIVATE_HTTPS_VERIFIED', flush=True)
    if '--show-account' in sys.argv:
        runpy.run_path(str(pilot.STAGE / 'show_demo_account.py'), run_name='__main__')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        import traceback
        private = Path('/root/pf1007l-reminders-verify-failure.txt')
        private.write_text(traceback.format_exc())
        private.chmod(0o600)
        safe = str(error) if type(error) is RuntimeError else 'Private diagnostics retained on Mint'
        pilot.status('https-verification-failed', error=safe, exceptionType=type(error).__name__)
        print('Verification stopped: ' + safe, file=sys.stderr)
        sys.exit(1)
