import hashlib
import importlib.util
import io
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
installer = load('installer', 'install_host.py')
launcher = load('launcher', 'launch_installer.py')

def result(args, stdout='', stderr='', code=0):
    return subprocess.CompletedProcess(args, code, stdout, stderr)

class InstallerTests(unittest.TestCase):
    def test_readiness_waits_through_connection_refusal(self):
        response=io.BytesIO(b'{"ready":true}')
        with patch.object(installer.urllib.request,'urlopen',side_effect=[ConnectionRefusedError(),response]) as request, patch.object(installer.time,'sleep'):
            self.assertEqual(installer.wait_for_health(),{'ready':True})
            self.assertEqual(request.call_count,2)

    def test_readiness_failure_is_reported(self):
        with self.assertRaisesRegex(RuntimeError,'readiness deadline'):
            installer.wait_for_health(timeout=0)

    def test_absent_and_inactive_units_skip_reset(self):
        for load_state, active in [('not-found', 'inactive'), ('loaded', 'inactive')]:
            calls=[]
            def run(args, check=True):
                calls.append(args)
                return result(args, f'LoadState={load_state}\nActiveState={active}\n')
            self.assertFalse(installer.reset_failed_if_needed('test.service', run))
            self.assertEqual(len(calls), 1)

    def test_loaded_failed_unit_is_reset(self):
        calls=[]
        def run(args, check=True):
            calls.append(args)
            return result(args, 'LoadState=loaded\nActiveState=failed\n' if args[1]=='show' else '')
        self.assertTrue(installer.reset_failed_if_needed('test.service', run))
        self.assertEqual(calls[-1], ['systemctl','reset-failed','test.service'])

    def test_garbage_collection_race_is_safe(self):
        shows=0
        def run(args, check=True):
            nonlocal shows
            if args[1]=='show':
                shows+=1
                return result(args, 'LoadState=loaded\nActiveState=failed\n' if shows==1 else 'LoadState=not-found\nActiveState=inactive\n')
            return result(args, stderr='Unit not loaded', code=1)
        self.assertFalse(installer.reset_failed_if_needed('test.service', run))

    def test_real_reset_failure_is_reported(self):
        def run(args, check=True):
            return result(args,'LoadState=loaded\nActiveState=failed\n') if args[1]=='show' else result(args,stderr='permission denied',code=1)
        with self.assertRaisesRegex(installer.CommandFailure,'permission denied'):
            installer.reset_failed_if_needed('test.service',run)

    def test_all_unit_files_precede_reload_and_registration(self):
        with tempfile.TemporaryDirectory() as temp:
            stage, units=Path(temp)/'stage',Path(temp)/'units'; stage.mkdir()
            for name in installer.UNITS:(stage/name).write_text('[Service]\nType=oneshot\n')
            calls=[]
            def run(args, check=True):
                calls.append(args)
                if args[1]=='daemon-reload':
                    self.assertTrue(all((units/name).is_file() for name in installer.UNITS));return result(args)
                self.assertIn(['systemctl','daemon-reload'],calls)
                return result(args,f'LoadState=loaded\nActiveState=inactive\nFragmentPath={units/args[2]}\nDropInPaths=\n')
            installer.register_units(stage,units,run)
            self.assertEqual(calls[0],['systemctl','daemon-reload'])
            self.assertFalse(any('reset-failed' in c for c in calls))

    def test_unchanged_file_is_not_rewritten(self):
        with tempfile.TemporaryDirectory() as temp:
            source,dest=Path(temp)/'source',Path(temp)/'dest';source.write_text('reviewed')
            self.assertTrue(installer.atomic_copy(source,dest))
            stamp=dest.stat().st_mtime_ns
            self.assertFalse(installer.atomic_copy(source,dest));self.assertEqual(stamp,dest.stat().st_mtime_ns)

    def test_fresh_runtime_creates_parents_and_repeat_needs_no_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            stage=Path(temp)/'stage';stage.mkdir();project=Path(temp)/'missing/opt/project'
            body=b'fake verified runtime';archive=stage/'runtime.tar'
            with tarfile.open(archive,'w') as output:
                info=tarfile.TarInfo('runtime/bin/node');info.size=len(body);info.mode=0o755;output.addfile(info,io.BytesIO(body))
            meta={'archive':'runtime.tar','directory':'runtime','sha256':installer.digest(archive),'node_binary_sha256':hashlib.sha256(body).hexdigest(),'version':'v-test'}
            run=lambda args,check=True:result(args,'v-test\n')
            self.assertTrue(installer.ensure_runtime(stage,project,meta,run));archive.unlink()
            self.assertFalse(installer.ensure_runtime(stage,project,meta,run))

    def test_tee_does_not_hide_remote_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            script=launcher.terminal_script(['/bin/bash','-c','printf remote-failure; exit 23'],Path(temp)/'log')
            r=subprocess.run(['/bin/bash','-c',script],capture_output=True,text=True)
            self.assertEqual(r.returncode,23);self.assertIn('PF1007L_SSH_EXIT=23 PF1007L_TEE_EXIT=0',r.stdout)
            self.assertEqual((Path(temp)/'log').read_text(),'remote-failure')

    def test_tee_failure_is_not_hidden(self):
        with tempfile.TemporaryDirectory() as temp:
            tee=Path(temp)/'broken-tee';tee.write_text('#!/bin/bash\ncat >/dev/null\nexit 5\n');tee.chmod(0o700)
            script=launcher.terminal_script(['/bin/echo','output'],Path(temp)/'log',str(tee))
            r=subprocess.run(['/bin/bash','-c',script],capture_output=True,text=True)
            self.assertEqual(r.returncode,5);self.assertIn('PF1007L_TEE_EXIT=5',r.stdout)

if __name__=='__main__':unittest.main()
