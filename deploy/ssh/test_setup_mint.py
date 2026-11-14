import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('setup_mint', Path(__file__).with_name('setup_mint.py'))
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class ConfigTests(unittest.TestCase):
    def test_preserves_unrelated_config_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            original = 'Host elsewhere\n    HostName 192.0.2.1\n\nHost *\n    ServerAliveInterval 60\n'
            config = directory / 'config'
            config.write_text(original)
            result = subprocess.CompletedProcess([], 0, 'hostname pf1007l-mint\n', '')
            with patch.object(setup.subprocess, 'run', return_value=result):
                setup.configure(directory)
                first = config.read_bytes()
                setup.configure(directory)
            self.assertEqual(config.read_bytes(), first)
            self.assertTrue(config.read_text().endswith(original))
            self.assertEqual((directory / 'config.before-pf1007l').read_text(), original)
            self.assertEqual(config.stat().st_mode & 0o777, 0o600)
            self.assertEqual(directory.stat().st_mode & 0o777, 0o700)

    def test_existing_alias_is_not_shadowed(self):
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.CompletedProcess([], 0, 'hostname other.example\n', '')
            with patch.object(setup.subprocess, 'run', return_value=result):
                with self.assertRaisesRegex(ValueError, 'already configured'):
                    setup.configure(Path(temp))
            self.assertFalse((Path(temp) / 'config').exists())

    def test_symlinked_config_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            target = directory / 'original'
            target.write_text('preserve me')
            (directory / 'config').symlink_to(target)
            with self.assertRaisesRegex(ValueError, 'symlinked'):
                setup.configure(directory)
            self.assertEqual(target.read_text(), 'preserve me')


if __name__ == '__main__':
    unittest.main()
