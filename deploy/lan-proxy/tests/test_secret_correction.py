import base64
import configparser
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tls'))
import prepare_secrets

class CorrectionTests(unittest.TestCase):
    def test_replaces_only_eab_and_preserves_valid_dns_profile_email(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);host='fixture-only.duckdns.org';token='invented-test-token-0123456789'
            profile=json.dumps({'hostname':host,'address':'10.157.1.115'})
            ini='server = https://acme.zerossl.com/v2/DV90\ndomains = '+host+'\nemail = fixture@example.test\neab-kid = previous-fixture-id\neab-hmac-key = previous-fixture-key\n'
            for name,value in [('profile.json',profile),('duckdns-token',token),('acme.ini',ini)]:
                (root/name).write_text(value);(root/name).chmod(0o600)
            kid='new-fixture-id';hmac=base64.urlsafe_b64encode(b't'*32).decode().rstrip('=');output=io.StringIO()
            with patch.object(prepare_secrets,'ROOT',root),patch.object(prepare_secrets.getpass,'getpass',side_effect=[kid,hmac]) as prompt,contextlib.redirect_stdout(output):
                prepare_secrets.collect(host,True)
            self.assertEqual(prompt.call_count,2)
            self.assertEqual((root/'duckdns-token').read_text(),token);self.assertEqual((root/'profile.json').read_text(),profile)
            cfg=configparser.ConfigParser();cfg.read_string('[acme]\n'+(root/'acme.ini').read_text())
            self.assertEqual(cfg['acme']['email'],'fixture@example.test');self.assertEqual(cfg['acme']['eab-kid'],kid);self.assertEqual(cfg['acme']['eab-hmac-key'],hmac)
            self.assertNotIn('previous-fixture-key',(root/'acme.ini').read_text());self.assertNotIn(hmac,output.getvalue());self.assertNotIn(token,output.getvalue())
    def test_interrupted_eab_keeps_saved_dns_and_email(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'duckdns-token').write_text('invented-test-token-0123456789');(root/'duckdns-token').chmod(0o600)
            with patch.object(prepare_secrets,'ROOT',root),patch.object(prepare_secrets.getpass,'getpass',side_effect=['fixture@example.test',KeyboardInterrupt()]),contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(KeyboardInterrupt):prepare_secrets.collect('fixture-only.duckdns.org',True)
            self.assertTrue((root/'duckdns-token').exists());self.assertEqual((root/'account-email').read_text().strip(),'fixture@example.test');self.assertFalse((root/'acme.ini').exists())
    def test_hmac_encoding_normalizes_same_bytes(self):
        value=bytes(range(32));standard=base64.b64encode(value).decode();url=base64.urlsafe_b64encode(value).decode().rstrip('=')
        self.assertEqual(prepare_secrets.normalized_hmac(standard),url)
        with self.assertRaises(ValueError):prepare_secrets.normalized_hmac('not-valid!')

if __name__=='__main__':unittest.main()
