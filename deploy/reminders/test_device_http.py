"""Real HTTP boundary tests on an ephemeral loopback port, with invented keys."""
import http.client
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest

from device_auth import device_id
from task_bridge import Bridge, handler, ORIGIN, PREFIX
import test_device_auth as fixtures


class DeviceHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): fixtures.DeviceAuthenticationTests.setUpClass.__func__(cls)
    @classmethod
    def tearDownClass(cls): fixtures.DeviceAuthenticationTests.tearDownClass.__func__(cls)
    sign = fixtures.DeviceAuthenticationTests.sign

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.identifier = device_id(self.public[0])
        self.registry = {'version':1, 'devices':[{'id':self.identifier, 'publicKey':self.public[0], 'enabled':True, 'epoch':1}]}
        self.bridge = Bridge({'username':'pf1007l-demo', 'password':'invented'},
            {'apiKey':'invented-backend-key', 'csrf':'invented-strong-csrf-secret-'*3, 'frameIP':'192.0.2.23', 'authMode':'device-v1'},
            Path(self.temp.name)/'state.sqlite', device_registry=self.registry)
        self.now = 1000
        self.bridge.device_auth.clock = lambda: self.now
        self.writes = 0
        self.bridge.snapshot = lambda: {'items':[], 'stale':False}
        def complete(*args): self.writes += 1; return {'completed':True}
        self.bridge.complete = complete
        self.server = ThreadingHTTPServer(('127.0.0.1',0), handler(self.bridge))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=2)
        self.bridge.db.close(); self.temp.cleanup()

    def request(self, route, method='GET', value=None, headers=None):
        fields = {'X-Pilot-Key':'invented-backend-key', 'X-Pilot-Client':'192.0.2.23', 'Origin':ORIGIN}
        if value is not None: fields['Content-Type'] = 'application/json'
        fields.update(headers or {})
        fields = {k:v for k,v in fields.items() if v is not None}
        conn = http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
        conn.request(method, PREFIX+route, body=json.dumps(value).encode() if value is not None else None, headers=fields)
        response = conn.getresponse(); data = json.loads(response.read()); output=(response.status,dict(response.getheaders()),data)
        conn.close(); return output

    def login(self):
        status, _, challenge = self.request('device/challenge','POST',{'device':self.identifier})
        self.assertEqual(status,200)
        status, headers, session = self.request('device/prove','POST',{'device':self.identifier, 'challenge':challenge['id'], 'signature':self.sign(challenge)})
        self.assertEqual(status,200); self.assertNotIn('token',session)
        return headers['Set-Cookie'].split(';')[0], session

    def test_full_cold_session_snapshot_and_completion_csrf_flow(self):
        status, _, denied = self.request('session')
        self.assertEqual(status,401); self.assertEqual(denied['code'],'device_auth_required')
        cookie, session = self.login()
        self.assertEqual(self.request('session',headers={'Cookie':cookie})[2]['csrf'],session['csrf'])
        self.assertEqual(self.request('snapshot',headers={'Cookie':cookie})[0],200)
        body={'id':'invented','version':'invented','operation':'invented-operation'}
        self.assertEqual(self.request('complete','POST',body,{'Cookie':cookie})[0],403)
        self.assertEqual(self.writes,0)
        self.assertEqual(self.request('complete','POST',body,{'Cookie':cookie,'X-Pilot-CSRF':session['csrf']})[0],200)
        self.assertEqual(self.writes,1)

    def test_backend_key_frame_origin_and_content_type_enforced(self):
        for headers in [{'X-Pilot-Key':'wrong'}, {'X-Pilot-Client':'192.0.2.24'}, {'Origin':'https://other.example'},
                        {'Origin':None}, {'Content-Type':'text/plain'}]:
            self.assertIn(self.request('device/challenge','POST',{'device':self.identifier},headers)[0],(403,415))
        self.assertEqual(self.bridge.db.execute('SELECT COUNT(*) FROM device_challenges').fetchone()[0],0)

    def test_legacy_cookie_cannot_bootstrap_device_mode(self):
        for route in ['session','snapshot']:
            self.assertEqual(self.request(route,headers={'Cookie':'pf1007l-demo=invented'})[0],401)
        self.assertFalse(self.bridge.load('provisioned',False))

    def test_expired_session_and_revocation_deny_before_task_write(self):
        cookie, session = self.login(); self.now += 901
        body={'id':'invented','version':'invented','operation':'invented-operation'}
        status, _, denied = self.request('complete','POST',body,{'Cookie':cookie,'X-Pilot-CSRF':session['csrf']})
        self.assertEqual(status,401);self.assertEqual(denied['code'],'device_auth_required'); self.assertEqual(self.writes,0)
        cookie,_=self.login()
        self.bridge.device_auth.sync_registry({'version':1,'devices':[]})
        self.assertEqual(self.request('snapshot',headers={'Cookie':cookie})[0],401)
        self.assertEqual(self.request('device/challenge','POST',{'device':self.identifier})[0],403)

    def test_old_csrf_cannot_be_reused_with_new_session(self):
        _, old = self.login(); cookie, new = self.login()
        self.assertNotEqual(old['csrf'],new['csrf'])
        self.assertEqual(self.request('complete','POST',{}, {'Cookie':cookie,'X-Pilot-CSRF':old['csrf']})[0],403)
        self.assertEqual(self.writes,0)

    def test_private_calendar_uses_same_device_auth_and_cannot_write(self):
        self.assertEqual(self.request('calendar')[0],401)
        cookie,_=self.login()
        self.bridge.calendar_snapshot=lambda:{'source':'private-caldav','events':[], 'stale':False}
        self.assertEqual(self.request('calendar',headers={'Cookie':cookie})[0],200)
        self.assertEqual(self.request('calendar',headers={'Cookie':cookie,'Origin':'https://unrelated.example'})[0],403)
        self.assertEqual(self.request('calendar?arbitrary=path',headers={'Cookie':cookie})[0],404)
        self.assertEqual(self.request('calendar','POST',{}, {'Cookie':cookie})[0],404)
        self.assertEqual(self.writes,0)

    def test_invalid_or_oversized_device_bodies_fail_closed(self):
        for value in [[], None, {'device':'x'*2100}]:
            self.assertIn(self.request('device/challenge','POST',value)[0],(400,413,415))
        self.assertEqual(self.request('device/challenge','GET')[0],401)
        self.assertEqual(self.request('device/challenge','POST',{'device':'f'*64})[0],403)


if __name__=='__main__': unittest.main()
