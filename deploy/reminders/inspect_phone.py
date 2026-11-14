import json
from pathlib import Path
import xml.etree.ElementTree as ET
import vobject
from install_demo import request


def execute(stage):
    account = json.loads(Path('/etc/pf1007l-reminders-demo/demo-account.json').read_text())
    query = b'''<C:calendar-query xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav"><D:prop><D:getetag/><C:calendar-data/></D:prop><C:filter><C:comp-filter name="VCALENDAR"><C:comp-filter name="VTODO"/></C:comp-filter></C:filter></C:calendar-query>'''
    code, _, data = request('REPORT', '/pf1007l-demo/pf1007l-test/', account['password'], query, {'Content-Type': 'application/xml', 'Depth': '1'})
    if code != 207:
        raise RuntimeError('Demo query failed')
    matches = []
    count = 0
    for text in ET.fromstring(data).iter('{urn:ietf:params:xml:ns:caldav}calendar-data'):
        cal = vobject.readOne(text.text)
        for task in cal.contents.get('vtodo', []):
            count += 1
            title = str(task.summary.value) if hasattr(task, 'summary') else ''
            if str(task.uid.value) == 'pf1007l-demo-undated' or title == 'Undated dashboard pilot' or title.startswith('Test dashboard sync') or title.startswith('Siri dashboard pilot'):
                due = task.due.value if hasattr(task, 'due') else None
                matches.append({'title': title, 'uid': str(task.uid.value),
                                'due': due.isoformat() if due is not None else None,
                                'dueType': type(due).__name__,
                                'dueTZID': task.due.params.get('TZID') if due is not None else None,
                                'status': str(task.status.value) if hasattr(task, 'status') else 'NEEDS-ACTION',
                                'completed': hasattr(task, 'completed') or (hasattr(task, 'status') and task.status.value == 'COMPLETED'),
                                'completionFields': {name: [{'value': str(p.value), 'params': p.params} for p in task.contents.get(name, [])]
                                                     for name in ('status', 'percent-complete', 'completed', 'dtstamp', 'last-modified', 'sequence')}})
    # Read-only protocol check that completed items remain queryable rather than
    # disappearing from the CalDAV collection or being represented as deletions.
    completed_query = b'''<C:calendar-query xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav"><D:prop><D:getetag/></D:prop><C:filter><C:comp-filter name="VCALENDAR"><C:comp-filter name="VTODO"><C:prop-filter name="STATUS"><C:text-match collation="i;ascii-casemap">COMPLETED</C:text-match></C:prop-filter></C:comp-filter></C:comp-filter></C:filter></C:calendar-query>'''
    completed_code, _, completed_data = request('REPORT', '/pf1007l-demo/pf1007l-test/', account['password'], completed_query, {'Content-Type': 'application/xml', 'Depth': '1'})
    completed_hrefs = [x.text for x in ET.fromstring(completed_data).iter('{DAV:}href')] if completed_code == 207 else []
    return {'collectionCount': count, 'matches': matches, 'completedQueryStatus': completed_code,
            'phoneReminderReturnedByCompletedQuery': '/pf1007l-demo/pf1007l-test/pf1007l-demo-undated.ics' in completed_hrefs}
