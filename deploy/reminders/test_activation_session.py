import json
from pathlib import Path
import sqlite3
import tarfile
import tempfile
import unittest
import subprocess
from unittest.mock import patch

import activation_session as deploy
import test_device_auth as fixtures
from device_auth import device_id


class ActivationSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):fixtures.DeviceAuthenticationTests.setUpClass.__func__(cls)
    @classmethod
    def tearDownClass(cls):fixtures.DeviceAuthenticationTests.tearDownClass.__func__(cls)

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.base=Path(self.temp.name);self.root=self.base/'root';self.root.mkdir()
        self.frozen=self.base/'frozen';self.frozen.mkdir()
        self.backup=self.base/'backup';self.commands=[]
        self.settings={'apiKey':'invented-backend','session':'invented-session','csrf':'invented-csrf','frameIP':'192.0.2.23'}
        for name,path in deploy.FILE_MAP.items():
            if name in ('device_auth.py','device_registry.py','device-registry.json','device-auth.conf'):continue
            p=self.root/path.lstrip('/');p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(json.dumps(self.settings) if name=='settings.json' else 'original-'+name)
            p.chmod(0o600 if name=='settings.json' else 0o644)
        (self.root/'etc/pf1007l-reminders-bridge').chmod(0o700)
        for path in [deploy.ACCOUNT,'/opt/pf1007l-tls/proxy.mjs','/etc/pf1007l-proxy-https/config.json','/etc/pf1007l-reminders-bridge/proxy-key']:
            p=self.root/path.lstrip('/');p.parent.mkdir(parents=True,exist_ok=True);p.write_text('preserve-protected')
        ui=self.root/deploy.UI.lstrip('/');ui.mkdir();(ui/'index.html').write_text('original-ui')
        dbpath=self.root/deploy.DATABASE.lstrip('/');dbpath.parent.mkdir(parents=True)
        db=sqlite3.connect(dbpath);db.execute('CREATE TABLE operations(key TEXT,result TEXT)');db.execute('INSERT INTO operations VALUES (?,?)',('old','done'));db.commit();db.close()
        for name in ('device_auth.py','device_registry.py','task_bridge.py','pf1007l-reminders-bridge.service','reminders-demo-proxy.mjs'):(self.frozen/name).write_text('new-'+name)
        (self.frozen/'device-auth.conf').write_text('[Service]\nLoadCredential=device-registry:/etc/pf1007l-reminders-bridge/device-registry.json\n')
        src=self.base/'ui';src.mkdir();(src/'index.html').write_text('new-ui')
        with tarfile.open(self.frozen/'reminders-ui.tar.gz','w:gz') as archive:archive.add(src/'index.html',arcname='index.html')
        def runner(args):
            self.commands.append(args)
            if args[:3]==['tailscale','serve','status']:
                return json.dumps({'Web':{'hub-inspiron-5570.tailb76e1b.ts.net:443':{'Handlers':{'/':{'Proxy':'http://127.0.0.1:5238'}}}}})
            if args[0]=='curl':return json.dumps({'upstreamErrors':0})
            return 'active\n'
        self.session=deploy.Activation(self.frozen,self.backup,self.root,runner)
        self.state={'items':[{'id':'invented-id','title':'Invented reminder','due':None,'completed':False}]}
        self.session.snapshot=lambda:self.state
        self.session.make_backup()

    def tearDown(self):self.temp.cleanup()

    def test_consistent_private_backup_and_rollback_keep_new_operation_history(self):
        self.assertEqual(self.backup.stat().st_mode & 0o777,0o700)
        db=sqlite3.connect(self.backup/'tasks.sqlite');self.assertEqual(db.execute('SELECT COUNT(*) FROM operations').fetchone()[0],1);db.close()
        db=sqlite3.connect(self.session.p(deploy.DATABASE));db.execute('INSERT INTO operations VALUES (?,?)',('new','done'));db.commit();db.close()
        self.session.compat(True);self.session.rollback()
        db=sqlite3.connect(self.session.p(deploy.DATABASE));self.assertEqual(db.execute('SELECT COUNT(*) FROM operations').fetchone()[0],2);db.close()
        self.assertEqual(self.session.settings(),self.settings)
        self.assertEqual((self.session.p(deploy.UI)/'index.html').read_text(),'original-ui')
        self.assertFalse(self.session.p(deploy.FILE_MAP['device_auth.py']).exists())

    def test_proxy_restart_must_be_approved_before_mutating(self):
        with self.assertRaises(RuntimeError):self.session.compat(False)
        self.assertFalse(self.session.mutated)
        self.assertEqual(self.session.p(deploy.FILE_MAP['task_bridge.py']).read_text(),'original-task_bridge.py')

    def test_compatibility_preserves_auth_and_only_restarts_project_services(self):
        result=self.session.compat(True)
        self.assertTrue(result['taskStatePreserved']);self.assertEqual(self.session.settings(),self.settings)
        restarts=[args[2] for args in self.commands if args[:2]==['systemctl','restart']]
        self.assertEqual(restarts,[deploy.BRIDGE,deploy.PROXY])

    def test_enrollment_checks_fingerprint_and_activation_changes_only_auth_mode(self):
        self.session.compat(True)
        with self.assertRaises(ValueError):self.session.enroll({'publicKey':self.public[0],'fingerprint':'a'*64})
        self.assertFalse(self.session.p(deploy.FILE_MAP['device-registry.json']).exists())
        identifier=device_id(self.public[0])
        self.session.enroll({'publicKey':self.public[0],'fingerprint':identifier})
        self.assertEqual(self.session.settings(),self.settings)
        self.session.activate()
        self.assertEqual(self.session.settings(),{**self.settings,'authMode':'device-v1'})
        self.assertEqual(self.session.p(deploy.FILE_MAP['device-registry.json']).stat().st_mode & 0o777,0o600)
        self.assertEqual(self.session.p(deploy.FILE_MAP['settings.json']).stat().st_mode & 0o777,0o600)
        self.session.registry_action('revoke');self.session.registry_action('rotate')
        self.assertTrue(json.loads(self.session.p(deploy.FILE_MAP['device-registry.json']).read_text())['devices'][0]['enabled'])
        self.session.rollback();self.assertEqual(self.session.settings(),self.settings)

    def test_failed_task_state_gate_can_restore_baseline(self):
        self.session.snapshot=lambda:{'items':[]}
        with self.assertRaises(RuntimeError):self.session.compat(True)
        self.session.rollback()
        self.assertEqual(self.session.p(deploy.FILE_MAP['task_bridge.py']).read_text(),'original-task_bridge.py')

    def test_protected_account_configuration_tampering_is_detected(self):
        self.session.p(deploy.ACCOUNT).write_text('invented-change')
        with self.assertRaises(RuntimeError):self.session.protected_ok()

    def test_atomic_writer_refuses_symlink_without_touching_target(self):
        target=self.base/'preserve';target.write_text('preserve')
        link=self.base/'link';link.symlink_to(target)
        with self.assertRaises(RuntimeError):deploy.atomic(link,b'new')
        self.assertEqual(target.read_text(),'preserve')

    def test_https_listener_binding_is_awaited_without_another_restart(self):
        before=list(self.commands)
        failure=subprocess.CalledProcessError(7,['curl'])
        with patch.object(self.session,'health',side_effect=[failure,failure,None]) as health, patch.object(deploy.time,'sleep') as sleep:
            self.session.wait_healthy()
        self.assertEqual(health.call_count,3);self.assertEqual(sleep.call_count,2)
        self.assertEqual(self.commands,before)

    def test_readiness_failure_stays_bounded_and_does_not_bypass_checks(self):
        with patch.object(self.session,'health',side_effect=RuntimeError('invented failed gate')), patch.object(deploy.time,'monotonic',side_effect=[0,31]):
            with self.assertRaises(RuntimeError):self.session.wait_healthy()

    def test_recovery_verifies_restored_files_and_detects_ui_damage(self):
        self.session.compat(True);self.session.rollback()
        self.assertTrue(self.session.verify_restored()['baselineFilesAndUIVerified'])
        (self.session.p(deploy.UI)/'index.html').write_text('invented incorrect UI')
        with self.assertRaises(RuntimeError):self.session.verify_restored()

    def test_old_queued_action_is_consumed_at_session_start(self):
        with patch.object(deploy,'read_action',return_value={'id':'already-failed-action','action':'compat'}):
            self.assertIn('already-failed-action',deploy.initial_seen())
        with patch.object(deploy,'read_action',return_value=None):self.assertEqual(deploy.initial_seen(),set())

    def test_private_diagnostic_summary_never_returns_exception_payloads(self):
        (self.frozen/'failure.txt').write_text("subprocess.CalledProcessError: Command '['curl', 'invented-sensitive-argument']' returned non-zero exit status 7.\n")
        (self.frozen/'rollback-failure.txt').write_text('RuntimeError: invented-sensitive-payload\n')
        summary=deploy.diagnostic_summary(self.frozen)
        self.assertEqual(summary['failure.txt']['exitStatus'],7)
        self.assertNotIn('invented-sensitive',json.dumps(summary))


if __name__=='__main__':unittest.main()
