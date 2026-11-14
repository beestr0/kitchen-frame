import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import activation

class ActivationTests(unittest.TestCase):
 def test_public_source_overlay_is_traversable_under_private_umask_and_index_last(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);runtime=root/'runtime';runtime.mkdir(mode=0o700)
   source=root/'source';(source/'nested').mkdir(parents=True);(source/'nested/module.py').write_text('invented')
   (source/'index.html').write_text('new index')
   task=activation.Activation(root/'work');order=[];writer=activation.atomic
   def record(path,data,mode=0o644):order.append(path.name);writer(path,data,mode)
   previous=os.umask(0o077)
   try:
    with patch.object(activation,'RUNTIME',runtime),patch.object(activation,'atomic',side_effect=record):task.overlay(source,runtime/'deploy/calendar')
   finally:os.umask(previous)
   self.assertEqual(runtime.stat().st_mode&0o777,0o755)
   self.assertEqual((runtime/'deploy').stat().st_mode&0o777,0o755)
   self.assertEqual((runtime/'deploy/calendar/nested').stat().st_mode&0o777,0o755)
   self.assertEqual((runtime/'deploy/calendar/nested/module.py').stat().st_mode&0o777,0o644)
   self.assertEqual(order[-1],'index.html')
 def test_atomic_source_writer_refuses_symlink(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);p=root/'keep';p.write_text('preserve');link=root/'link';link.symlink_to(p)
   with self.assertRaises(RuntimeError):activation.atomic(link,b'new')
   self.assertEqual(p.read_text(),'preserve')
 def test_manifest_freeze_rejects_changed_bytes_and_symlinked_parent(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);stage=root/'stage';stage.mkdir();(stage/'deploy').mkdir();(stage/'deploy/source.py').write_bytes(b'invented')
   data=json.dumps({'files':{'deploy/source.py':hashlib.sha256(b'invented').hexdigest()}}).encode()
   (stage/'manifest.json').write_bytes(data)
   fake=SimpleNamespace(pw_uid=os.getuid())
   with patch.object(activation,'STAGE',stage),patch.object(activation,'MANIFEST',hashlib.sha256(data).hexdigest()),patch.object(activation.pwd,'getpwnam',return_value=fake):
    output=root/'frozen';output.mkdir();activation.freeze(output);self.assertEqual((output/'deploy/source.py').read_bytes(),b'invented')
    (stage/'deploy/source.py').write_bytes(b'changed')
    with self.assertRaises(RuntimeError):activation.freeze(root/'rejected')
    (stage/'deploy/source.py').unlink();(stage/'deploy').rmdir();(stage/'deploy').symlink_to(output/'deploy')
    with self.assertRaises(OSError):activation.freeze(root/'symlink-rejected')
 def test_rollback_preserves_new_database_and_restarts_only_project_units(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);ui=root/'ui';ui.mkdir();(ui/'index.html').write_text('candidate')
   paths={name:root/name for name in activation.FILE_MAP}
   for p in paths.values():p.write_text('candidate')
   task=activation.Activation(root/'work');task.backup.mkdir(parents=True);(task.backup/'ui').mkdir();(task.backup/'ui/index.html').write_text('original')
   inventory={name:name in ('bridge.py','proxy.mjs') for name in paths}
   for name in ('bridge.py','proxy.mjs'):(task.backup/name).write_text('original')
   (task.backup/'inventory.json').write_text(json.dumps(inventory));task.mutated=True;task.bridge_changed=True;task.proxy_changed=True
   db=root/'current.sqlite';db.write_bytes(b'new completion history');calls=[]
   with patch.object(activation,'FILE_MAP',paths),patch.object(activation,'UI',ui),patch.object(activation,'DATABASE',db),patch.object(activation,'run',side_effect=lambda args:calls.append(args) or ''),patch.object(activation,'publish'),patch.object(activation,'wait_healthy'):
    task.rollback()
   self.assertEqual(db.read_bytes(),b'new completion history');self.assertEqual((ui/'index.html').read_text(),'original')
   self.assertEqual([call[2] for call in calls if call[:2]==['systemctl','restart']],[activation.BRIDGE,activation.PROXY])
   self.assertFalse(paths['calendar.conf'].exists())

 def test_resume_verifies_original_backup_and_installed_candidate_before_reuse(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);runtime=root/'runtime';runtime.mkdir(mode=0o700);ui=root/'ui';ui.mkdir();(ui/'index.html').write_text('original')
   task=activation.Activation(root/'work');task.backup.mkdir(parents=True);task.frozen.mkdir()
   (task.backup/'ui').mkdir();(task.backup/'ui/index.html').write_text('original')
   paths={name:root/name for name in activation.FILE_MAP};inventory={name:name in ('bridge.py','proxy.mjs') for name in paths}
   for name in ('bridge.py','proxy.mjs'):
    paths[name].write_text('original');(task.backup/name).write_text('original')
   (task.backup/'inventory.json').write_text(json.dumps(inventory));(task.backup/'protected-hashes.json').write_text('{}')
   relative='deploy/icloud-calendar/service.py';source=task.frozen/relative;source.parent.mkdir(parents=True);source.write_text('reviewed')
   installed=runtime/relative;installed.parent.mkdir(parents=True);installed.write_text('reviewed')
   raw=json.dumps({'files':{relative:hashlib.sha256(source.read_bytes()).hexdigest()}}).encode();(task.frozen/'manifest.json').write_bytes(raw)
   with patch.object(activation,'RUNTIME',runtime),patch.object(activation,'UI',ui),patch.object(activation,'FILE_MAP',paths),patch.object(activation,'MANIFEST',hashlib.sha256(raw).hexdigest()),patch.object(activation,'health'),patch.object(activation,'private_permissions'),patch.object(activation,'publish'):
    task.resume();self.assertFalse(task.mutated)
    installed.write_text('unexpected')
    with self.assertRaises(RuntimeError):task.resume()
