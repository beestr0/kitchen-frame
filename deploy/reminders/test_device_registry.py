import json
from pathlib import Path
import tempfile
import unittest

from device_auth import device_id
from device_registry import change, save, validate
import test_device_auth as fixtures


class RegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): fixtures.DeviceAuthenticationTests.setUpClass.__func__(cls)
    @classmethod
    def tearDownClass(cls): fixtures.DeviceAuthenticationTests.tearDownClass.__func__(cls)

    def setUp(self):
        self.empty={'version':1,'devices':[]}
        self.identifier=device_id(self.public[0])
        self.registry=change(self.empty,'enroll',self.identifier,self.public[0])

    def test_enroll_checks_physical_fingerprint_and_does_not_mutate_input(self):
        self.assertEqual(self.empty['devices'],[])
        self.assertEqual(self.registry['devices'][0]['id'],self.identifier)
        with self.assertRaises(ValueError):change(self.empty,'enroll','f'*64,self.public[0])

    def test_revoke_and_rotation_increase_epoch_without_replacing_public_identity(self):
        revoked=change(self.registry,'revoke',self.identifier)
        self.assertFalse(revoked['devices'][0]['enabled']);self.assertEqual(revoked['devices'][0]['epoch'],2)
        rotated=change(revoked,'rotate',self.identifier)
        self.assertTrue(rotated['devices'][0]['enabled']);self.assertEqual(rotated['devices'][0]['epoch'],3)
        self.assertEqual(rotated['devices'][0]['publicKey'],self.public[0])

    def test_unknown_and_duplicate_changes_fail(self):
        with self.assertRaises(ValueError):change(self.registry,'enroll',self.identifier,self.public[0])
        with self.assertRaises(ValueError):change(self.registry,'revoke','f'*64)
        with self.assertRaises(ValueError):change(self.registry,'delete',self.identifier)

    def test_atomic_save_has_private_permissions_and_valid_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'registry.json'
            save(path,self.registry)
            self.assertEqual(path.stat().st_mode & 0o777,0o600)
            self.assertEqual(json.loads(path.read_text()),self.registry)
            save(path,change(self.registry,'revoke',self.identifier))
            self.assertFalse(json.loads(path.read_text())['devices'][0]['enabled'])
            self.assertEqual(len(list(Path(directory).iterdir())),1)

    def test_symlink_or_world_readable_registry_is_rejected_without_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'target';target.write_text('preserve')
            link=Path(directory)/'registry.json';link.symlink_to(target)
            with self.assertRaises(ValueError):save(link,self.registry)
            self.assertEqual(target.read_text(),'preserve')
            link.unlink();target.chmod(0o644)
            with self.assertRaises(ValueError):save(target,self.registry)
            self.assertEqual(target.read_text(),'preserve')

    def test_invalid_registry_never_replaces_last_good(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'registry.json';save(path,self.registry)
            before=path.read_bytes()
            with self.assertRaises(ValueError):save(path,{'version':1,'devices':[{}]})
            self.assertEqual(path.read_bytes(),before)


if __name__=='__main__':unittest.main()
