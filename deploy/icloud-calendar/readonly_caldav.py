"""Inactive CalDAV discovery/read primitives. No CLI, scheduler or implicit I/O.

Credentials and results must remain Linux-local. Nothing here is imported by the
running proxy. Live account testing requires a separate owner-approved step.
"""
import base64
from datetime import datetime, timezone
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

BASE = 'https://caldav.icloud.com/'
D = '{DAV:}'
C = '{urn:ietf:params:xml:ns:caldav}'
A = '{http://apple.com/ns/ical/}'
MAX_BYTES = 5 * 1024 * 1024

class CalendarError(Exception):
    """Only fixed safe messages, never upstream XML, URLs, credentials or titles."""


def approved_url(value, base=BASE):
    if not isinstance(value, str) or any(ord(c) < 33 or ord(c) > 126 for c in value):
        raise CalendarError('Invalid calendar endpoint')
    url = urllib.parse.urljoin(base, value)
    try:
        parsed = urllib.parse.urlsplit(url)
        if (parsed.scheme != 'https' or parsed.username is not None or parsed.password is not None
                or parsed.port not in (None, 443) or parsed.query or parsed.fragment
                or not re.fullmatch(r'(?:p[0-9]{1,3}-)?caldav\.icloud\.com', parsed.hostname or '')
                or '\\' in parsed.path):
            raise ValueError()
    except ValueError:
        raise CalendarError('Unapproved calendar endpoint') from None
    return url


def xml(data):
    if not isinstance(data, bytes) or len(data) > MAX_BYTES or b'\x00' in data:
        raise CalendarError('Invalid calendar XML')
    try:
        text = data.decode('utf-8-sig')
        if re.search(r'<!\s*(DOCTYPE|ENTITY)\b', text, re.I):
            raise ValueError()
        return ET.fromstring(text)
    except (ValueError, ET.ParseError):
        raise CalendarError('Invalid calendar XML') from None


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs): return None


class ReadonlyCalDAV:
    def __init__(self, username, app_password):
        if not username or ':' in username or any(c in username + app_password for c in '\r\n') or not app_password:
            raise CalendarError('Invalid calendar credentials')
        self._authorization = 'Basic ' + base64.b64encode((username + ':' + app_password).encode()).decode()
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        # Explicit direct transport: never inherit an ambient HTTP proxy that could
        # capture authorization. No debug handlers, cookie jar or HTTP fallback.
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(),
                                                  urllib.request.HTTPSHandler(context=context))

    def __repr__(self): return '<ReadonlyCalDAV credentials=protected>'

    def _request(self, method, endpoint, body=b'', depth='0'):
        if method not in ('PROPFIND', 'REPORT'):
            raise CalendarError('Calendar writes are forbidden')
        if depth not in ('0', '1') or not isinstance(body, bytes) or len(body) > MAX_BYTES:
            raise CalendarError('Invalid calendar request')
        endpoint = approved_url(endpoint)
        for _ in range(4):
            request = urllib.request.Request(endpoint, data=body, method=method, headers={
                'Authorization': self._authorization, 'Depth': depth,
                'Content-Type': 'application/xml; charset=utf-8',
                'Accept': 'application/xml', 'User-Agent': 'PF1007L-readonly-calendar/1',
            })
            try:
                with self._opener.open(request, timeout=20) as response:
                    if response.status not in (200, 207): raise CalendarError('Calendar read failed')
                    data = response.read(MAX_BYTES + 1)
                    if len(data) > MAX_BYTES: raise CalendarError('Calendar response too large')
                    return endpoint, xml(data)
            except urllib.error.HTTPError as error:
                code = error.code
                location = error.headers.get('Location')
                error.close()
                if code in (301, 302, 307, 308) and location:
                    endpoint = approved_url(location, endpoint)
                    continue
                if code in (401, 403): raise CalendarError('Calendar authorization required') from None
                if code == 429: raise CalendarError('Calendar rate limited') from None
                raise CalendarError('Calendar read failed') from None
            except CalendarError:
                raise
            except Exception:
                raise CalendarError('Calendar transport unavailable') from None
        raise CalendarError('Calendar redirect limit exceeded')

    def _props(self, endpoint, names, depth='0'):
        root = ET.Element(D + 'propfind');prop = ET.SubElement(root, D + 'prop')
        for name in names: ET.SubElement(prop, name)
        return self._request('PROPFIND', endpoint, ET.tostring(root, encoding='utf-8'), depth)

    @staticmethod
    def _successful_props(root):
        if root.tag != D + 'multistatus': raise CalendarError('Invalid calendar multistatus')
        for response in root.findall(D + 'response'):
            props = []
            for ps in response.findall(D + 'propstat'):
                if re.fullmatch(r'HTTP/\S+ 200(?: .*)?', ps.findtext(D + 'status', '')):
                    p = ps.find(D + 'prop')
                    if p is not None: props.extend(list(p))
            yield response.findtext(D + 'href', ''), props

    def discover(self):
        # Discovery lists names/identifiers only. Event REPORTs are a separate step.
        current, root = self._props(BASE, [D + 'current-user-principal'])
        principals = [p.findtext(D + 'href') for _, props in self._successful_props(root)
                      for p in props if p.tag == D + 'current-user-principal']
        if len(principals) != 1 or not principals[0]: raise CalendarError('Calendar principal unavailable')
        principal = approved_url(principals[0], current)
        current, root = self._props(principal, [C + 'calendar-home-set'])
        homes = [h.text for _, props in self._successful_props(root) for p in props
                 if p.tag == C + 'calendar-home-set' for h in p.findall(D + 'href')]
        if not homes or len(homes) > 4: raise CalendarError('Calendar home unavailable')
        calendars = {}
        for home in homes:
            home = approved_url(home, current)
            effective, root = self._props(home, [D + 'resourcetype', D + 'displayname', A + 'calendar-color', C + 'supported-calendar-component-set'], '1')
            for href, props in self._successful_props(root):
                prop = {p.tag: p for p in props}
                kind = prop.get(D + 'resourcetype')
                if kind is None or kind.find(C + 'calendar') is None: continue
                components = prop.get(C + 'supported-calendar-component-set')
                if components is not None and not any(c.attrib.get('name') == 'VEVENT' for c in components): continue
                endpoint = approved_url(href, effective)
                if not href or not endpoint.endswith('/'): raise CalendarError('Invalid calendar collection')
                name = prop.get(D + 'displayname');color = prop.get(A + 'calendar-color')
                color = color.text if color is not None else ''
                calendars[endpoint] = {'href': endpoint, 'name': (name.text or 'Calendar')[:120] if name is not None else 'Calendar',
                                       'color': color[:7] if re.fullmatch(r'#[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?', color or '') else None}
                if len(calendars) > 100: raise CalendarError('Too many calendar collections')
        return list(calendars.values())

    def query_events(self, collection, start, end):
        # Query selected collections only; never schedule, subscribe, create or edit.
        if not all(isinstance(t, datetime) and t.tzinfo is not None for t in (start, end)) or not 0 < (end-start).total_seconds() <= 366*86400:
            raise CalendarError('Bounded calendar window required')
        collection = approved_url(collection)
        if not collection.endswith('/'):
            raise CalendarError('Invalid calendar collection')
        root = ET.Element(C + 'calendar-query');prop = ET.SubElement(root, D + 'prop')
        ET.SubElement(prop, D + 'getetag');ET.SubElement(prop, C + 'calendar-data')
        filt = ET.SubElement(root, C + 'filter');cal = ET.SubElement(filt, C + 'comp-filter', {'name':'VCALENDAR'})
        event = ET.SubElement(cal, C + 'comp-filter', {'name':'VEVENT'})
        stamp = lambda t: t.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        ET.SubElement(event, C + 'time-range', {'start':stamp(start),'end':stamp(end)})
        effective, response = self._request('REPORT', collection, ET.tostring(root, encoding='utf-8'), '1')
        rows = []
        for href, props in self._successful_props(response):
            data = next((p.text for p in props if p.tag == C + 'calendar-data'), None)
            if data is None: raise CalendarError('Incomplete calendar response')
            if not href: raise CalendarError('Incomplete calendar response')
            endpoint = approved_url(href, effective)
            prefix = urllib.parse.urlsplit(effective).path.rstrip('/') + '/'
            if urllib.parse.urlsplit(endpoint).netloc != urllib.parse.urlsplit(effective).netloc or not urllib.parse.urlsplit(endpoint).path.startswith(prefix):
                raise CalendarError('Unexpected calendar object')
            rows.append({'ical': data, 'etag': next((p.text for p in props if p.tag == D + 'getetag'), None)})
        return rows
