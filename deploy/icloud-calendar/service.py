#!/usr/bin/env python3
"""Loopback-only snapshot service; sole holder of Apple credential on Linux."""
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading

from collector import Collector
from readonly_caldav import ReadonlyCalDAV


def main():
    os.umask(0o077)
    credential=Path(os.environ['CREDENTIALS_DIRECTORY'])
    account=json.loads((credential/'apple-account').read_text())
    config=json.loads((credential/'calendar-config').read_text())
    key=(credential/'calendar-key').read_text().strip()
    if len(key)<40:raise ValueError('Calendar service credential required')
    collector=Collector(config,ReadonlyCalDAV(account['username'],account['appPassword']),
                        Path(os.environ['STATE_DIRECTORY'])/'calendar.sqlite')
    lock=threading.Lock()
    # Separate refresh worker: a slow Apple response never holds the task bridge lock.
    published={'value':collector.snapshot()}
    def refresh():
        while True:
            try:
                value=collector.refresh()
                with lock:published['value']=value
            except Exception:
                with lock:published['value']={**published['value'],'stale':True,'error':'Calendar refresh unavailable'}
            threading.Event().wait(30)
    threading.Thread(target=refresh,daemon=True).start()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            if self.path!='/snapshot' or not hmac.compare_digest(self.headers.get('X-Calendar-Key',''),key):
                self.send_error(403);return
            with lock:value=published['value']
            body=json.dumps(value).encode()
            self.send_response(200);self.send_header('Content-Type','application/json')
            self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)))
            self.end_headers();self.wfile.write(body)
    ThreadingHTTPServer(('127.0.0.1',5241),Handler).serve_forever()


if __name__=='__main__':main()
