import base64
from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import threading
import unittest

from device_auth import DeviceAuth, AuthError, device_id, public_der, verify_signature, cookie_token, SESSION_SECONDS

ORIGIN = 'https://beestr0.duckdns.org:8789'


class DeviceAuthenticationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.keys = tempfile.TemporaryDirectory(prefix='pf1007l-invented-key-fixtures-')
        cls.private = []
        cls.public = []
        previous = os.umask(0o077)
        try:
            for number in range(2):
                path = Path(cls.keys.name) / ('invented-' + str(number) + '.pem')
                subprocess.run(['openssl','ecparam','-name','prime256v1','-genkey','-noout','-out',str(path)],check=True,capture_output=True)
                path.chmod(0o600)
                public = subprocess.run(['openssl','pkey','-in',str(path),'-pubout','-outform','DER'],check=True,capture_output=True).stdout
                cls.private.append(path); cls.public.append(base64.b64encode(public).decode())
        finally: os.umask(previous)

    @classmethod
    def tearDownClass(cls): cls.keys.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'invented.sqlite'
        self.db = sqlite3.connect(self.path)
        self.now = 1000.0
        self.identifier = device_id(self.public[0])
        self.registry = {'version':1,'devices':[{'id':self.identifier,'publicKey':self.public[0],'enabled':True,'epoch':1}]}
        self.auth = DeviceAuth(self.db,self.registry,ORIGIN,'invented-csrf-secret-'*4,clock=lambda:self.now)

    def tearDown(self): self.db.close(); self.temp.cleanup()

    def sign(self, challenge, key=0, message=None):
        proof = subprocess.run(['openssl','dgst','-sha256','-sign',str(self.private[key])],input=(message or challenge['message']).encode(),check=True,capture_output=True).stdout
        return base64.b64encode(proof).decode()

    def login(self):
        challenge=self.auth.challenge(self.identifier)
        return self.auth.prove(self.identifier,challenge['id'],self.sign(challenge))

    def test_registered_key_proof_and_hash_only_session_storage(self):
        token, session = self.login()
        self.assertEqual(session['mode'],'device-v1');self.assertEqual(session['expiresIn'],900)
        self.assertEqual(self.auth.authenticate('pf1007l-device='+token)['csrf'],session['csrf'])
        self.assertIn('Secure; HttpOnly; SameSite=Strict',self.auth.cookie(token))
        hashes=[row[0] for row in self.db.execute('SELECT hash FROM device_sessions')]
        self.assertNotIn(token,hashes);self.assertIn(hashlib.sha256(token.encode()).hexdigest(),hashes)

    def test_unregistered_device_cannot_enroll_itself(self):
        for value in [device_id(self.public[1]),None,{},'bad-id']:
            with self.assertRaises(AuthError):self.auth.challenge(value)

    def test_wrong_key_and_wrong_audience_fail_without_consuming_valid_proof(self):
        challenge=self.auth.challenge(self.identifier)
        for signature in [self.sign(challenge,key=1),self.sign(challenge,message=challenge['message'].replace(ORIGIN,'https://unrelated.example'))]:
            with self.assertRaises(AuthError):self.auth.prove(self.identifier,challenge['id'],signature)
        token,_=self.auth.prove(self.identifier,challenge['id'],self.sign(challenge))
        self.assertTrue(self.auth.session(token))

    def test_nonce_replay_and_expiry_are_rejected(self):
        challenge=self.auth.challenge(self.identifier); proof=self.sign(challenge)
        self.auth.prove(self.identifier,challenge['id'],proof)
        with self.assertRaises(AuthError):self.auth.prove(self.identifier,challenge['id'],proof)
        challenge=self.auth.challenge(self.identifier);proof=self.sign(challenge);self.now+=61
        with self.assertRaises(AuthError):self.auth.prove(self.identifier,challenge['id'],proof)

    def test_expired_cookie_recovers_with_fresh_device_proof(self):
        token,_=self.login();self.now+=SESSION_SECONDS
        with self.assertRaises(AuthError):self.auth.session(token)
        replacement,_=self.login();self.assertNotEqual(token,replacement)
        self.assertTrue(self.auth.session(replacement))

    def test_revocation_and_epoch_rotation_invalidate_sessions_and_challenges(self):
        token,_=self.login();challenge=self.auth.challenge(self.identifier);proof=self.sign(challenge)
        revoked=copy.deepcopy(self.registry);revoked['devices'][0]['enabled']=False
        self.auth.sync_registry(revoked)
        with self.assertRaises(AuthError):self.auth.session(token)
        with self.assertRaises(AuthError):self.auth.challenge(self.identifier)
        enabled=copy.deepcopy(self.registry);enabled['devices'][0]['epoch']=2
        self.auth.sync_registry(enabled)
        with self.assertRaises(AuthError):self.auth.prove(self.identifier,challenge['id'],proof)
        self.assertTrue(self.login()[1])

    def test_removed_device_is_revoked(self):
        token,_=self.login();self.auth.sync_registry({'version':1,'devices':[]})
        with self.assertRaises(AuthError):self.auth.session(token)

    def test_restart_preserves_valid_session_and_consumed_nonce(self):
        challenge=self.auth.challenge(self.identifier);proof=self.sign(challenge)
        token,session=self.auth.prove(self.identifier,challenge['id'],proof)
        self.db.close();self.db=sqlite3.connect(self.path)
        self.auth=DeviceAuth(self.db,self.registry,ORIGIN,'invented-csrf-secret-'*4,clock=lambda:self.now)
        self.assertEqual(self.auth.session(token)['csrf'],session['csrf'])
        with self.assertRaises(AuthError):self.auth.prove(self.identifier,challenge['id'],proof)

    def test_duplicate_and_legacy_cookies_are_not_device_credentials(self):
        token,_=self.login()
        for header in ['', 'pf1007l-demo='+token,'pf1007l-device='+token+'; pf1007l-device='+token,'pf1007l-device=bad']:
            with self.assertRaises(AuthError):cookie_token(header)

    def test_clock_rollback_does_not_extend_a_session(self):
        token,_=self.login();self.now-=1
        with self.assertRaises(AuthError):self.auth.session(token)

    def test_challenge_rate_limit_and_recovery(self):
        for _ in range(5):self.auth.challenge(self.identifier)
        with self.assertRaises(AuthError) as error:self.auth.challenge(self.identifier)
        self.assertEqual(error.exception.status,429)
        self.now+=61;self.assertTrue(self.auth.challenge(self.identifier))

    def test_invalid_proof_work_is_bounded_per_nonce(self):
        challenge=self.auth.challenge(self.identifier)
        for _ in range(3):
            with self.assertRaises(AuthError):self.auth.prove(self.identifier,challenge['id'],self.sign(challenge,key=1))
        with self.assertRaises(AuthError) as error:self.auth.prove(self.identifier,challenge['id'],self.sign(challenge))
        self.assertEqual(error.exception.status,429)
        self.assertTrue(self.login()[1])

    def test_session_count_is_bounded(self):
        tokens=[]
        for _ in range(7):
            tokens.append(self.login()[0]);self.now+=13
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM device_sessions').fetchone()[0],3)
        with self.assertRaises(AuthError):self.auth.session(tokens[0])
        self.assertTrue(self.auth.session(tokens[-1]))

    def test_invalid_registry_does_not_revoke_working_keys(self):
        token,_=self.login()
        duplicate=copy.deepcopy(self.registry);duplicate['devices']*=2
        with self.assertRaises(ValueError):self.auth.sync_registry(duplicate)
        self.assertTrue(self.auth.session(token))
        with self.assertRaises(ValueError):public_der(base64.b64encode(b'not-a-public-key').decode())

    def test_parallel_replay_can_issue_only_one_session(self):
        barrier=threading.Barrier(2)
        def verifier(key,message,signature):
            result=verify_signature(key,message,signature);barrier.wait(timeout=5);return result
        # Construct connections in their worker threads, but synchronize after both
        # have loaded the same approved registry and before issuing the challenge.
        ready=threading.Barrier(3)
        event=threading.Event(); shared={}
        def worker():
            db=sqlite3.connect(self.path,timeout=10)
            auth=DeviceAuth(db,self.registry,ORIGIN,'invented-csrf-secret-'*4,clock=lambda:self.now,verifier=verifier)
            ready.wait(timeout=5);event.wait(timeout=5)
            try:
                auth.prove(self.identifier,shared['challenge']['id'],shared['proof']);return True
            except AuthError:return False
            finally:db.close()
        with ThreadPoolExecutor(2) as pool:
            a=pool.submit(worker);b=pool.submit(worker);ready.wait(timeout=5)
            shared['challenge']=self.auth.challenge(self.identifier);shared['proof']=self.sign(shared['challenge']);event.set()
            self.assertEqual(sorted([a.result(timeout=10),b.result(timeout=10)]),[False,True])


if __name__=='__main__':unittest.main()
