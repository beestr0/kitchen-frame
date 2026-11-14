import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import start_authorization as launcher
from authorize import write_new

class AuthorizationTests(unittest.TestCase):
 def test_frozen_native_command_verifies_each_root_owned_helper_before_execution(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);files={}
   for name in ['authorize.py','prepare_credentials.py','readonly_caldav.py']:
    relative='deploy/icloud-calendar/'+name;p=root/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('invented fixture')
    files[relative]=hashlib.sha256(p.read_bytes()).hexdigest()
   raw=json.dumps({'files':files}).encode();(root/'manifest.json').write_bytes(raw)
   with patch.object(launcher,'BUNDLE',root),patch.object(launcher,'MANIFEST',hashlib.sha256(raw).hexdigest()):
    cmd=launcher.command();self.assertEqual(cmd[:3],['ssh','-t','pf1007l-mint'])
    self.assertIn('sha256sum -c -',cmd[-1]);self.assertIn('--approved-discovery',cmd[-1]);self.assertIn('/root/pf1007l-calendar-authorization-',cmd[-1])
    self.assertNotIn('invented fixture',cmd[-1]);self.assertNotIn('appPassword',cmd[-1])
 def test_selection_writer_preserves_existing_files_and_uses_private_permissions(self):
  with tempfile.TemporaryDirectory() as directory:
   p=Path(directory)/'config.json';write_new(p,'invented')
   self.assertEqual(p.stat().st_mode&0o777,0o600)
   with self.assertRaises(ValueError):write_new(p,'replace')
   self.assertEqual(p.read_text(),'invented')


class RetryTests(unittest.TestCase):
 def test_bad_reentry_does_not_touch_existing_credential(self):
  from authorize import store_entry
  from prepare_credentials import save
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'private';save(path,'invented@example.invalid','abcd-efgh-ijkl-mnop')
   original=(path/'apple.json').read_bytes()
   with self.assertRaises(ValueError):store_entry(path,'invented@example.invalid','mistyped',True)
   self.assertEqual((path/'apple.json').read_bytes(),original)
 def test_explicit_retry_retains_old_entry_privately_and_preserves_selection(self):
  from authorize import store_entry
  from prepare_credentials import save
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'private';save(path,'invented@example.invalid','abcd-efgh-ijkl-mnop');original=(path/'apple.json').read_bytes()
   (path/'config.json').write_text('preserve selection')
   store_entry(path,'corrected@example.invalid','qrst-uvwx-yzab-cdef',True)
   self.assertEqual((path/'apple.json').stat().st_mode&0o777,0o600)
   self.assertEqual((path/'config.json').read_text(),'preserve selection')
   backups=list(path.glob('.mistyped-entry-*'));self.assertEqual(len(backups),1);self.assertEqual(backups[0].read_bytes(),original)
   self.assertEqual(backups[0].stat().st_mode&0o777,0o600)
