#!/usr/bin/env python3
"""Read-only CalDAV discovery diagnosis; no raw credentials/XML/events in report."""
import base64
import json
import os
from pathlib import Path
import ssl
import sys
import urllib.parse
import xml.etree.ElementTree as ET

from verify_https import TailnetHTTPS, HOST

STAGE = Path(__file__).resolve().parent
D = '{DAV:}'
C = '{urn:ietf:params:xml:ns:caldav}'
ORIGIN = 'https://' + HOST


def request(method, path, password=None, body=b'', depth='0'):
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    connection = TailnetHTTPS(HOST, timeout=15, context=context)
    headers = {'Depth': depth, 'User-Agent': 'PF1007L-DAV-discovery-diagnostic/1'}
    if body:
        headers['Content-Type'] = 'application/xml; charset=utf-8'
    if password:
        headers['Authorization'] = 'Basic ' + base64.b64encode(('pf1007l-demo:' + password).encode()).decode()
    try:
        connection.request(method, path, body or None, headers)
        response = connection.getresponse()
        data = response.read(2 * 1024 * 1024 + 1)
        if len(data) > 2 * 1024 * 1024:
            raise RuntimeError('Response limit exceeded')
        return response.status, dict(response.getheaders()), data
    finally:
        connection.close()


def propfind(path, names, password, depth='0'):
    root = ET.Element(D + 'propfind')
    props = ET.SubElement(root, D + 'prop')
    for name in names:
        ET.SubElement(props, name)
    code, headers, data = request('PROPFIND', path, password, ET.tostring(root), depth)
    if code != 207:
        raise RuntimeError('PROPFIND did not return multistatus: ' + str(code))
    root = ET.fromstring(data)
    if root.tag != D + 'multistatus':
        raise RuntimeError('Invalid multistatus')
    rows = []
    for row in root.findall(D + 'response'):
        successful, failed = {}, []
        for stat in row.findall(D + 'propstat'):
            props = stat.find(D + 'prop')
            if props is None:
                continue
            if ' 200 ' in stat.findtext(D + 'status', ''):
                successful.update({p.tag: p for p in props})
            else:
                failed.extend([p.tag for p in props])
        rows.append((row.findtext(D + 'href', ''), successful, failed))
    return headers, rows


def same_origin_path(value, base='/'):
    parsed = urllib.parse.urlsplit(urllib.parse.urljoin(ORIGIN + base, value))
    if parsed.scheme != 'https' or parsed.hostname != HOST or parsed.port not in (None, 443) or parsed.query or parsed.fragment or parsed.username is not None or parsed.password is not None:
        raise RuntimeError('Discovery escaped approved HTTPS origin')
    return parsed.path


def write_report(report):
    temp = STAGE / '.discovery-status.new'
    temp.write_text(json.dumps(report, indent=2))
    temp.chmod(0o644)
    temp.replace(STAGE / 'discovery-status.json')


def main():
    if os.geteuid() != 0 or not os.isatty(0):
        raise RuntimeError('Private native sudo SSH TTY required')
    os.umask(0o077)
    account = json.loads(Path('/etc/pf1007l-reminders-demo/demo-account.json').read_text())
    if account.get('username') != 'pf1007l-demo':
        raise RuntimeError('Unexpected demo account')
    password = account['password']
    report = {'phase': 'authenticated-discovery-running', 'readOnly': True}
    write_report(report)
    # No automatic following: validate each Location before sending credentials.
    for method in ('GET', 'PROPFIND'):
        code, headers, _ = request(method, '/.well-known/caldav')
        location = next((v for k, v in headers.items() if k.lower() == 'location'), '')
        report['wellKnown' + method] = {'status': code, 'location': location,
                                      'resolvedPath': same_origin_path(location)}
        if code not in (301, 302, 307, 308) or not location:
            raise RuntimeError('Well-known discovery redirect missing')
    code, headers, _ = request('OPTIONS', '/', password)
    report['options'] = {'status': code, 'DAV': headers.get('DAV', headers.get('Dav', '')),
                         'Allow': headers.get('Allow', '')}
    _, rows = propfind('/', [D + 'current-user-principal', D + 'resourcetype'], password)
    principals = [p[D + 'current-user-principal'].findtext(D + 'href')
                  for _, p, _ in rows if D + 'current-user-principal' in p]
    if len(principals) != 1 or not principals[0]:
        raise RuntimeError('Principal not discovered')
    principal = same_origin_path(principals[0])
    report['principalPath'] = principal
    _, rows = propfind(principal, [C + 'calendar-home-set', D + 'principal-URL',
                                  D + 'current-user-privilege-set', C + 'calendar-user-address-set'], password)
    homes = [p[C + 'calendar-home-set'].findtext(D + 'href')
             for _, p, _ in rows if C + 'calendar-home-set' in p]
    if len(homes) != 1 or not homes[0]:
        raise RuntimeError('Calendar home not discovered')
    home = same_origin_path(homes[0], principal)
    report['calendarHomePath'] = home
    _, rows = propfind(home, [D + 'resourcetype', D + 'displayname',
                             C + 'supported-calendar-component-set', D + 'current-user-privilege-set',
                             D + 'supported-report-set'], password, '1')
    collections = []
    target = None
    for href, props, failed in rows:
        kind = props.get(D + 'resourcetype')
        if kind is None or kind.find(C + 'calendar') is None:
            continue
        collection = same_origin_path(href, home)
        components = props.get(C + 'supported-calendar-component-set')
        names = [x.attrib.get('name') for x in components] if components is not None else []
        privilege = props.get(D + 'current-user-privilege-set')
        privileges = [x.tag for p in privilege for x in p] if privilege is not None else []
        collections.append({'path': collection, 'components': names, 'privileges': privileges,
                            'unsupportedProperties': failed})
        if collection == '/pf1007l-demo/pf1007l-test/':
            target = collection
            if 'VTODO' not in names:
                raise RuntimeError('Test collection does not advertise VTODO')
    report['collections'] = collections
    if not target:
        raise RuntimeError('Test collection not discoverable through home')
    query = b'''<C:calendar-query xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav"><D:prop><D:getetag/></D:prop><C:filter><C:comp-filter name="VCALENDAR"><C:comp-filter name="VTODO"/></C:comp-filter></C:filter></C:calendar-query>'''
    code, _, body = request('REPORT', target, password, query, '1')
    report['vtodoQueryStatus'] = code
    if code != 207:
        raise RuntimeError('VTODO REPORT failed')
    report['vtodoResourceCount'] = len(ET.fromstring(body).findall(D + 'response'))
    # Slash normalization must remain relative or same-origin HTTPS as well.
    code, headers, _ = request('PROPFIND', principal.rstrip('/'), password,
                              b'<D:propfind xmlns:D="DAV:"><D:prop><D:resourcetype/></D:prop></D:propfind>')
    report['principalWithoutSlashStatus'] = code
    location = next((v for k, v in headers.items() if k.lower() == 'location'), None)
    if location:
        report['principalWithoutSlashRedirect'] = same_origin_path(location, principal.rstrip('/'))
    report['phase'] = 'authenticated-discovery-passed'
    write_report(report)
    print('PF1007L_AUTHENTICATED_DISCOVERY_PASSED', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        import traceback
        private = Path('/root/pf1007l-reminders-discovery-failure.txt')
        private.write_text(traceback.format_exc())
        private.chmod(0o600)
        safe = str(error) if type(error) is RuntimeError else 'Details retained privately on Mint'
        write_report({'phase': 'discovery-failed', 'error': safe, 'exceptionType': type(error).__name__})
        print('Discovery diagnostic stopped: ' + safe, file=sys.stderr)
        sys.exit(1)
