import tempfile
from pathlib import Path
import unittest
from repair_network import replacements,transaction,atomic,OLD,NEW
class RepairTests(unittest.TestCase):
 def test_only_exact_frame_guards_change_and_keys_stay_intact(self):
  proxy={'allowedClients':[OLD],'healthClients':['10.157.1.115'],'other':'preserve'}
  settings={'frameIP':OLD,'authMode':'device-v1','csrf':'invented','apiKey':'invented-key'}
  firewall='table inet pf1007l_proxy_tls { ip saddr '+OLD+' accept; }'
  p,s,f=replacements(proxy,settings,firewall)
  self.assertEqual(p,{**proxy,'allowedClients':[NEW]});self.assertEqual(s,{**settings,'frameIP':NEW})
  self.assertNotIn(OLD,f);self.assertIn(NEW,f);self.assertNotIn('/24',f)
 def test_unexpected_baseline_is_not_overwritten(self):
  with self.assertRaises(RuntimeError):replacements({'allowedClients':['192.0.2.1']},{},'')
 def test_firewall_transaction_does_not_touch_other_tables(self):
  text='table inet pf1007l_proxy_tls {}';t=transaction(text)
  self.assertEqual(t,'delete table inet pf1007l_proxy_tls\n'+text)
  self.assertEqual(transaction(t),t);self.assertNotIn('flush ruleset',t)
 def test_atomic_writer_preserves_private_mode_and_refuses_symlink(self):
  with tempfile.TemporaryDirectory() as directory:
   p=Path(directory)/'settings';atomic(p,b'invented',0o600);self.assertEqual(p.stat().st_mode&0o777,0o600)
   link=Path(directory)/'link';link.symlink_to(p)
   with self.assertRaises(RuntimeError):atomic(link,b'changed',0o600)
   self.assertEqual(p.read_bytes(),b'invented')
