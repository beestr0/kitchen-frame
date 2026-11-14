import contextlib
import io
import http.client
import importlib.util
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import unittest

BASE=Path(__file__).resolve().parents[1]
TLS=BASE/'tls'
sys.path.insert(0,str(TLS))
import activate_certificate as activation
import dns_hook
import run_acme

OPENSSL='/opt/homebrew/bin/openssl' if Path('/opt/homebrew/bin/openssl').exists() else 'openssl'
def openssl(*args):
    return subprocess.check_output([OPENSSL,*args],stderr=subprocess.DEVNULL)

class Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
        cls.ca=cls.root/'ca.pem';cls.ca_key=cls.root/'ca.key'
        openssl('req','-x509','-newkey','rsa:2048','-nodes','-days','90','-subj','/CN=Invented Test CA',
                '-keyout',str(cls.ca_key),'-out',str(cls.ca),'-addext','basicConstraints=critical,CA:TRUE','-addext','keyUsage=critical,keyCertSign,cRLSign')
        cls.first=cls.make_leaf('first');cls.second=cls.make_leaf('second')
        cls.backend=cls.root/'backend-key';cls.backend.write_text('invented-test-only-backend-key-32-characters');cls.backend.chmod(0o600)
    @classmethod
    def make_leaf(cls,name,days=60):
        folder=cls.root/name;folder.mkdir();key=folder/'privkey.pem';csr=folder/'req.pem';cert=folder/'cert.pem'
        openssl('req','-new','-newkey','rsa:2048','-nodes','-subj','/CN=desk.example.test','-addext','subjectAltName=DNS:desk.example.test','-keyout',str(key),'-out',str(csr))
        openssl('x509','-req','-in',str(csr),'-CA',str(cls.ca),'-CAkey',str(cls.ca_key),'-CAcreateserial','-days',str(days),'-copy_extensions','copy','-out',str(cert))
        (folder/'fullchain.pem').write_bytes(cert.read_bytes()+cls.ca.read_bytes());key.chmod(0o600)
        return folder
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def check_command(self,args):return activation.command([OPENSSL,*args[1:]])

class ActivationTests(Fixture):
    def test_real_chain_hostname_and_pair(self):
        activation.validate(self.first,'desk.example.test',self.ca,self.check_command)
        with self.assertRaises(ValueError):activation.validate(self.first,'wrong.example.test',self.ca,self.check_command)
    def test_private_key_mismatch_and_near_expiry_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);(path/'fullchain.pem').write_bytes((self.first/'fullchain.pem').read_bytes())
            (path/'privkey.pem').write_bytes((self.second/'privkey.pem').read_bytes());(path/'privkey.pem').chmod(0o600)
            with self.assertRaises(ValueError):activation.validate(path,'desk.example.test',self.ca,self.check_command)
        short=self.make_leaf('short-'+self.__class__.__name__,days=1)
        with self.assertRaises(ValueError):activation.validate(short,'desk.example.test',self.ca,self.check_command)

    def test_untrusted_chain_rejected(self):
        empty=self.root/'untrusted.pem';empty.write_text('not a root')
        with self.assertRaises(ValueError):activation.validate(self.first,'desk.example.test',empty,self.check_command)
    def test_renewal_activation_and_failed_restart_rollback(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)/'certs';calls=[]
            activation.activate(self.first,'desk.example.test',self.ca,base,lambda:calls.append('restart'),lambda:None,self.check_command)
            original=(base/'current').readlink()
            def fail():raise RuntimeError('simulated health failure')
            attempts=iter([False,True])
            def probe():
                if not next(attempts):fail()
            with self.assertRaises(ValueError):
                activation.activate(self.second,'desk.example.test',self.ca,base,lambda:calls.append('restart'),probe,self.check_command)
            self.assertEqual((base/'current').readlink(),original)
            activation.activate(self.second,'desk.example.test',self.ca,base,lambda:None,lambda:None,self.check_command)
            self.assertNotEqual((base/'current').readlink(),original)
            self.assertEqual((base/'previous').readlink(),original)
            self.assertEqual((base/'current/tls-key').stat().st_mode&0o777,0o600)
    def test_first_activation_failure_stops_only_new_listener(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)/'certs';stopped=[]
            def fail():raise RuntimeError('simulated restart failure')
            with self.assertRaises(ValueError):activation.activate(self.first,'desk.example.test',self.ca,base,fail,lambda:None,self.check_command,lambda:stopped.append(True))
            self.assertEqual(stopped,[True]);self.assertFalse((base/'current').exists())

class DnsTests(unittest.TestCase):
    def test_only_txt_parameters_and_no_ip(self):
        from unittest.mock import patch,MagicMock
        response=MagicMock();response.__enter__.return_value.read.return_value=b'OK'
        opener=MagicMock();opener.open.return_value=response
        with patch.object(dns_hook.urllib.request,'build_opener',return_value=opener):dns_hook.update('desk','invented-token','challenge')
        url=opener.open.call_args.args[0];self.assertTrue(url.startswith('https://www.duckdns.org/update?'))
        self.assertNotIn('&ip=',url);self.assertIn('&txt=challenge',url)
    def test_conflicting_txt_never_overwritten(self):
        calls=[]
        def query(name,kind,server=None):return {'ns.example'} if kind=='NS' else {'unrelated-challenge'}
        with self.assertRaises(ValueError):dns_hook.apply('auth','desk.duckdns.org','a'*43,'invented',query,lambda *a,**k:calls.append(a))
        self.assertEqual(calls,[])
    def test_auth_and_cleanup_preserve_other_records(self):
        calls=[];txt=set()
        def query(name,kind,server=None):return {'ns.example'} if kind=='NS' else txt
        def writer(label,token,value,**kw):
            calls.append((label,value,kw));txt.clear()
            if value:txt.add(value)
        dns_hook.apply('auth','desk.duckdns.org','a'*43,'invented',query,writer)
        dns_hook.apply('cleanup','desk.duckdns.org','a'*43,'invented',query,writer)
        self.assertEqual(calls,[('desk','a'*43,{}),('desk','',{'clear':True})])
    def test_wrong_validation_and_no_nameserver_fail(self):
        with self.assertRaises(ValueError):dns_hook.apply('auth','desk.duckdns.org','bad','invented')
        with self.assertRaises(ValueError):dns_hook.apply('auth','desk.duckdns.org','a'*43,'invented',lambda *a:set())
    def test_dns_errors_do_not_expose_token(self):
        from unittest.mock import patch
        token='invented-test-token-0123456789';output=io.StringIO()
        with patch.object(dns_hook,'profile',return_value={'hostname':'desk.duckdns.org'}), patch.object(dns_hook,'private_read',return_value=token), patch.dict(os.environ,{'CERTBOT_IDENTIFIER':'desk.duckdns.org','CERTBOT_ALL_IDENTIFIERS':'desk.duckdns.org','CERTBOT_VALIDATION':'a'*43}), patch.object(dns_hook,'apply',side_effect=RuntimeError('https://provider/?token='+token)), contextlib.redirect_stderr(output):
            self.assertEqual(dns_hook.main(),1)
        self.assertNotIn(token,output.getvalue());self.assertNotIn('https://provider',output.getvalue())

    def test_acme_commands_are_project_scoped_and_secret_free(self):
        for action in ['issue','renew']:
            args=run_acme.arguments(action,'desk.duckdns.org')
            self.assertIn('/etc/pf1007l-tls/acme.ini',args);self.assertIn('pf1007l-desk',args)
            self.assertNotIn('--force-renewal',args);self.assertNotIn('--dry-run',args);self.assertNotIn('--eab-hmac-key',args)

class HttpsListenerTests(Fixture):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        code="JSON.stringify(Object.values(require('os').networkInterfaces()).flat().filter(x=>x.family==='IPv4'&&!x.internal).map(x=>x.address))"
        ips=json.loads(subprocess.check_output(['node','-p',code],text=True))
        cls.address=next((x for x in ips if x.startswith(('10.','192.168.','172.'))),None)
        if not cls.address:raise unittest.SkipTest('No private LAN IPv4 available for restricted listener test')
        sock=socket.socket();sock.bind((cls.address,0));cls.port=sock.getsockname()[1];sock.close()
        bridge=socket.socket();bridge.bind((cls.address,0));cls.bridge_port=bridge.getsockname()[1];bridge.close()
        cls.config=cls.root/'config.json';cls.config.write_text(json.dumps({'bindAddress':cls.address,'port':cls.port,'allowedClients':[cls.address],
            'demoOnly':True,'allowApiWrites':False,'keyFile':str(cls.backend),'tls':{'hostname':'desk.example.test','connectProxyPort':cls.bridge_port,'keyFile':str(cls.first/'privkey.pem'),'chainFile':str(cls.first/'fullchain.pem')}}))
        cls.runtime=cls.root/'runtime';cls.runtime.mkdir(mode=0o700)
        env=dict(os.environ,RUNTIME_DIRECTORY=str(cls.runtime))
        cls.process=subprocess.Popen(['node',str(BASE.parents[1]/'scripts/pf1007l-lan-proxy.mjs'),str(cls.config)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
        for _ in range(60):
            try:
                with socket.create_connection((cls.address,cls.port),timeout=.2):break
            except OSError:time.sleep(.1)
        else:
            cls.process.terminate();raise RuntimeError('HTTPS fixture failed to start')
    @classmethod
    def tearDownClass(cls):
        if hasattr(cls,'process'):
            cls.process.terminate();cls.process.communicate(timeout=5)
        super().tearDownClass()
    def request(self,host='desk.example.test',origin=None,trust=True):
        ctx=ssl.create_default_context(cafile=str(self.ca)) if trust else ssl.create_default_context()
        raw=socket.create_connection((self.address,self.port),timeout=2)
        try:wrapped=ctx.wrap_socket(raw,server_hostname=host)
        except Exception:raw.close();raise
        connection=http.client.HTTPConnection(self.address,self.port,timeout=2);connection.sock=wrapped
        headers={'Host':f'{host}:{self.port}'}
        if origin:headers['Origin']=origin
        connection.request('GET','/api/calendar',headers=headers);r=connection.getresponse();body=r.read();headers=dict(r.getheaders());connection.close();return r.status,headers,body
    def test_validated_tls_same_origin_demo_api(self):
        code,headers,body=self.request();self.assertEqual(code,200);self.assertTrue(json.loads(body)['demo'])
        csp=headers['Content-Security-Policy'];self.assertIn('wss://desk.example.test:',csp);self.assertNotIn(' ws://',csp)
        self.assertNotIn(self.backend.read_text().encode(),body)
    def test_wrong_hostname_rejected_by_normal_tls(self):
        with self.assertRaises(ssl.SSLCertVerificationError):self.request(host='wrong.example.test')
    def test_untrusted_ca_rejected_by_normal_tls(self):
        with self.assertRaises(ssl.SSLCertVerificationError):self.request(trust=False)
    def test_foreign_origin_rejected(self):self.assertEqual(self.request(origin='https://foreign.example')[0],403)
    def test_hot_reload_retains_process_and_rejects_invalid_material(self):
        def load(key,chain):
            raw=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);raw.settimeout(3);raw.connect(str(self.runtime/'reload.sock'))
            connection=http.client.HTTPConnection('localhost',timeout=3);connection.sock=raw
            connection.request('POST','/reload',json.dumps({'key':key,'chain':chain}),{'Content-Type':'application/json'})
            response=connection.getresponse();response.read();code=response.status;connection.close();return code
        original=self.process.pid
        def peer():
            context=ssl.create_default_context(cafile=str(self.ca))
            with socket.create_connection((self.address,self.port),timeout=2) as raw:
                with context.wrap_socket(raw,server_hostname='desk.example.test') as client:
                    return client.getpeercert(binary_form=True)
        first_peer=peer()
        self.assertEqual(load((self.second/'privkey.pem').read_text(),(self.second/'fullchain.pem').read_text()),200)
        self.assertEqual(self.request()[0],200)
        second_peer=peer();self.assertNotEqual(first_peer,second_peer)
        self.assertEqual(load('invalid-private-key',(self.first/'fullchain.pem').read_text()),400)
        self.assertEqual(self.request()[0],200)
        self.assertEqual(peer(),second_peer)
        self.assertEqual(self.process.pid,original);self.assertIsNone(self.process.poll())
        self.assertEqual((self.runtime/'reload.sock').stat().st_mode&0o777,0o600)
        self.assertEqual(load((self.first/'privkey.pem').read_text(),(self.first/'fullchain.pem').read_text()),200)
        self.assertEqual(peer(),first_peer)

    def test_single_target_connect_preserves_normal_tls(self):
        context=ssl.create_default_context(cafile=str(self.ca))
        conn=http.client.HTTPSConnection(self.address,self.bridge_port,context=context,timeout=3)
        conn.set_tunnel('desk.example.test',self.port)
        try:
            conn.request('GET','/api/calendar',headers={'Host':f'desk.example.test:{self.port}'})
            response=conn.getresponse();body=response.read();self.assertEqual(response.status,200);self.assertTrue(json.loads(body)['demo'])
        finally:conn.close()
    def test_connect_rejects_arbitrary_targets_and_plaintext(self):
        connection=http.client.HTTPConnection(self.address,self.bridge_port,timeout=2)
        connection.request('CONNECT','foreign.example:443',headers={'Host':'foreign.example:443'})
        response=connection.getresponse();response.read();self.assertEqual(response.status,403);connection.close()
        connection=http.client.HTTPConnection(self.address,self.bridge_port,timeout=2);connection.request('GET','/api/calendar');response=connection.getresponse();response.read();self.assertEqual(response.status,403);connection.close()

    def test_existing_http_mode_still_works(self):
        cfg=json.loads(self.config.read_text());cfg.pop('tls');cfg['liveWeather']=True
        sock=socket.socket();sock.bind((self.address,0));cfg['port']=sock.getsockname()[1];sock.close()
        path=self.root/'http-config.json';path.write_text(json.dumps(cfg))
        proc=subprocess.Popen(['node',str(BASE.parents[1]/'scripts/pf1007l-lan-proxy.mjs'),str(path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            for _ in range(40):
                try:
                    c=http.client.HTTPConnection(self.address,cfg['port'],timeout=.5);c.request('GET','/api/calendar');r=c.getresponse();body=r.read();c.close();break
                except OSError:time.sleep(.1)
            else:self.fail('HTTP fixture did not start')
            self.assertEqual(r.status,200);self.assertTrue(json.loads(body)['demo'])
            c=http.client.HTTPConnection(self.address,cfg['port'],timeout=.5);c.request('GET','/api/weather');r=c.getresponse();body=r.read();c.close()
            self.assertEqual(r.status,200);self.assertTrue(json.loads(body)['demo'])
        finally:proc.terminate();proc.communicate(timeout=5)

    def test_cleartext_cannot_load_https_listener(self):
        c=http.client.HTTPConnection(self.address,self.port,timeout=2)
        with self.assertRaises((http.client.RemoteDisconnected,ConnectionResetError)):
            c.request('GET','/api/calendar');c.getresponse()
        c.close()

if __name__=='__main__':unittest.main()
