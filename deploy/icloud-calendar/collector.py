"""Private selected-calendar collector. No I/O on import; no Apple write operations."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import time

from readonly_caldav import CalendarError, approved_url


def selected(config):
    if config.get('enabled') is not True or config.get('readOnly') is not True or config.get('allowCloudUpload') is not False:
        raise CalendarError('Calendar source is disabled')
    calendars = config.get('selectedCalendars')
    if not isinstance(calendars,list) or not 1<=len(calendars)<=20:
        raise CalendarError('Select one to twenty calendars')
    result=[]; ids=set(); urls=set()
    for item in calendars:
        href=approved_url(item.get('href'))
        identifier=item.get('id','');name=item.get('name','');color=item.get('color','')
        if (not href.endswith('/') or href in urls or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',identifier)
                or identifier in ids or not isinstance(name,str) or not 0<len(name)<=120
                or not re.fullmatch(r'#[a-fA-F0-9]{6}',color)):
            raise CalendarError('Invalid selected calendar')
        ids.add(identifier);urls.add(href);result.append(dict(id=identifier,href=href,name=name,color=color))
    return result


def normalize(rows, calendar, start, end, zone):
    payload={'rows':rows,'calendar':{k:calendar[k] for k in ('id','name','color')},
             'from':start.isoformat().replace('+00:00','Z'),'to':end.isoformat().replace('+00:00','Z'),'timezone':zone}
    data=json.dumps(payload).encode()
    if len(data)>5*1024*1024:raise CalendarError('Calendar response too large')
    try:
        run=subprocess.run(['/opt/pf1007l-proxy/node/bin/node',str(Path(__file__).with_name('normalize.mjs'))],input=data,
                           capture_output=True,timeout=25,check=True)
        if len(run.stdout)>2*1024*1024:raise ValueError()
        events=json.loads(run.stdout)
        if not isinstance(events,list) or len(events)>2000:raise ValueError()
        return events
    except Exception:raise CalendarError('Calendar normalization failed') from None


class Collector:
    def __init__(self, config, client, database, normalizer=normalize, clock=time.time):
        self.calendars=selected(config);self.zone=config.get('timezone','America/Indiana/Indianapolis')
        self.client,self.normalizer,self.clock=client,normalizer,clock
        self.period=int(config.get('syncMinutes',5))*60
        if not 60<=self.period<=3600:raise CalendarError('Invalid calendar refresh interval')
        self.db=sqlite3.connect(database,check_same_thread=False,timeout=5)
        self.db.execute('CREATE TABLE IF NOT EXISTS calendars(id TEXT PRIMARY KEY,binding TEXT,payload TEXT)')
        keep={c['id'] for c in self.calendars}
        for (identifier,) in self.db.execute('SELECT id FROM calendars').fetchall():
            if identifier not in keep:self.db.execute('DELETE FROM calendars WHERE id=?',(identifier,))
        self.db.commit();self.retry={};self.failures={};self.blocked=False

    @staticmethod
    def binding(calendar):return hashlib.sha256(calendar['href'].encode()).hexdigest()

    def load(self,c):
        row=self.db.execute('SELECT binding,payload FROM calendars WHERE id=?',(c['id'],)).fetchone()
        return json.loads(row[1]) if row and row[0]==self.binding(c) else None

    def save(self,c,value):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO calendars VALUES (?,?,?)',(c['id'],self.binding(c),json.dumps(value)))

    def refresh(self):
        now=self.clock();start=datetime.fromtimestamp(now,timezone.utc)-timedelta(days=31)
        end=datetime.fromtimestamp(now,timezone.utc)+timedelta(days=180)
        for c in self.calendars:
            if self.blocked or now<self.retry.get(c['id'],0):continue
            old=self.load(c) or {'events':[],'lastSuccess':None}
            try:
                rows=self.client.query_events(c['href'],start,end)
                events=self.normalizer(rows,c,start,end,self.zone)
                value={'events':events,'lastSuccess':now,'lastAttempt':now,'stale':False,
                       'from':start.isoformat(),'to':end.isoformat()}
                self.failures[c['id']]=0;self.retry[c['id']]=now+self.period
            except Exception as error:
                if isinstance(error,CalendarError) and str(error)=='Calendar authorization required':self.blocked=True
                failures=self.failures.get(c['id'],0)+1;self.failures[c['id']]=failures
                self.retry[c['id']]=now+min(3600,self.period*2**min(failures-1,4))
                value={**old,'lastAttempt':now,'stale':True,'error':'Calendar authorization needs attention' if self.blocked else 'Calendar refresh unavailable'}
            self.save(c,value)
        return self.snapshot()

    def snapshot(self):
        now=self.clock();events=[];calendars=[];success=[];starts=[];ends=[];failed=False
        for c in self.calendars:
            value=self.load(c) or {};last=value.get('lastSuccess')
            failed = failed or bool(value.get('error'))
            stale=value.get('stale',True) or last is None or now-last>max(900,self.period*2)
            calendars.append({k:c[k] for k in ('id','name','color')} | {'stale':stale,'lastSuccess':last})
            for event in value.get('events',[]):
                # Metadata changes apply immediately; stale cache never retains a removed alias/color.
                events.append({**event,'calendarName':c['name'],'color':c['color'],'calendarId':c['id']})
            if last is not None:success.append(last)
            if value.get('from'):starts.append(value['from']);ends.append(value['to'])
        events.sort(key=lambda e:(e['start'],e['uid']))
        if len(events)>4000:raise CalendarError('Calendar display limit exceeded')
        return {'source':'private-caldav','events':events,'calendars':calendars,
                'updated':datetime.fromtimestamp(min(success),timezone.utc).isoformat() if success else None,
                'stale':self.blocked or any(c['stale'] for c in calendars),
                'error':'Calendar authorization needs attention' if self.blocked else 'Calendar refresh unavailable' if failed else None,
                'window':{'from':max(starts),'to':min(ends)} if starts else None}
