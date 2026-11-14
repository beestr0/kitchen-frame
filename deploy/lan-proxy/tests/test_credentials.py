import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

PROXY=Path(__file__).resolve().parents[3]/'scripts/pf1007l-lan-proxy.mjs'
class CredentialChecks(unittest.TestCase):
    def check(self,systemd,file_mode,directory_mode):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);creds=root/'credentials';creds.mkdir();key=creds/'dashboard-key'
            key.write_text('invented-test-value-with-at-least-32-characters');key.chmod(file_mode)
            config={'bindAddress':'10.1.2.3','allowedClients':['10.1.2.4']}
            env=dict(os.environ);env.pop('CREDENTIALS_DIRECTORY',None)
            if systemd:env['CREDENTIALS_DIRECTORY']=str(creds)
            else:config['keyFile']=str(key)
            path=root/'config.json';path.write_text(json.dumps(config));creds.chmod(directory_mode)
            try:return subprocess.run(['node',str(PROXY),str(path),'--check-config'],capture_output=True,text=True,env=env)
            finally:creds.chmod(0o700);key.chmod(0o600)
    def test_private_source_credential(self):self.assertEqual(self.check(False,0o600,0o700).returncode,0)
    def test_readable_source_credential_rejected(self):self.assertNotEqual(self.check(False,0o644,0o700).returncode,0)
    def mount_policy(self, directory, mode, mount):
        source=PROXY.read_text();start=source.index('function isProtectedSystemdCredential(')
        end=source.index('\n// Ordinary key files',start)
        code=source[start:end]+'\nconsole.log(isProtectedSystemdCredential('+json.dumps(directory)+',{mode:'+str(mode)+'},'+json.dumps(mount)+'));'
        return subprocess.check_output(['node','-e',code],text=True).strip()=='true'
    def test_systemd_readonly_ram_mount(self):
        self.assertTrue(self.mount_policy('/run/credentials/example.service',0o444,'44 33 0:2 / /run/credentials/example.service ro,nosuid,nodev,noexec - ramfs ramfs rw'))
    def test_writable_mount_rejected(self):
        self.assertFalse(self.mount_policy('/run/credentials/example.service',0o444,'44 33 0:2 / /run/credentials/example.service rw - ramfs ramfs rw'))
    def test_arbitrary_directory_rejected(self):
        self.assertFalse(self.mount_policy('/tmp/example',0o444,'44 33 0:2 / /tmp/example ro - ramfs ramfs rw'))
    def test_writable_credential_rejected(self):
        self.assertFalse(self.mount_policy('/run/credentials/example.service',0o644,'44 33 0:2 / /run/credentials/example.service ro - tmpfs tmpfs rw'))
    def test_unprotected_systemd_directory_rejected(self):
        self.assertNotEqual(self.check(True,0o444,0o755).returncode,0)
if __name__=='__main__':unittest.main()
