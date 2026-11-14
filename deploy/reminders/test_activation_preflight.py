import contextlib
import io
import json
import os
from pathlib import Path
import sqlite3
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import activation_preflight as preflight


class PreflightTests(unittest.TestCase):
    def test_no_root_or_no_native_tty_refuses_before_reading_files(self):
        for uid,tty in [(501,True),(0,False)]:
            with patch.object(preflight.os,'geteuid',return_value=uid), patch.object(preflight.os,'isatty',return_value=tty), patch.object(preflight,'Path') as paths:
                with self.assertRaises(SystemExit):preflight.main()
                paths.assert_not_called()

    def run_fixture(self, private=True):
        with tempfile.TemporaryDirectory() as directory:
            database=Path(directory)/'fixture.sqlite'
            db=sqlite3.connect(database)
            db.executescript('CREATE TABLE operations(result TEXT); INSERT INTO operations VALUES ("pending"); CREATE TABLE device_sessions(hash TEXT,issued REAL,expires REAL); INSERT INTO device_sessions VALUES ("invented-private-session-hash",1000,1900); CREATE TABLE device_keys(active INTEGER); INSERT INTO device_keys VALUES (1);')
            db.commit(); before='\n'.join(db.iterdump()); db.close()
            def path(name):
                if name.endswith('tasks.sqlite'):return database
                mode=stat.S_IFDIR|0o700 if name.endswith('reminders-bridge') else stat.S_IFREG|(0o600 if private else 0o644)
                return SimpleNamespace(lstat=lambda:SimpleNamespace(st_mode=mode,st_uid=0),read_text=lambda:json.dumps({'authMode':'device-v1','csrf':'invented-sensitive-csrf','session':'invented-sensitive-cookie','password':'invented-sensitive-password'}))
            output=io.StringIO()
            original_connect=sqlite3.connect
            def connect(database_uri,**kwargs):
                self.assertTrue(database_uri.endswith('?mode=ro')); self.assertTrue(kwargs['uri'])
                return original_connect(database_uri,**kwargs)
            with patch.object(preflight.os,'geteuid',return_value=0), patch.object(preflight.os,'isatty',return_value=True), patch.object(preflight,'Path',side_effect=path), patch.object(preflight.subprocess,'run',return_value=SimpleNamespace(stdout='active\n')), patch.object(preflight.sqlite3,'connect',side_effect=connect), contextlib.redirect_stdout(output):
                if private:preflight.main()
                else:
                    with self.assertRaises(SystemExit):preflight.main()
            db=original_connect(database); self.assertEqual('\n'.join(db.iterdump()),before); db.close()
            text=output.getvalue()
            for secret in ['invented-private-session-hash','invented-sensitive-csrf','invented-sensitive-cookie','invented-sensitive-password']:
                self.assertNotIn(secret,text)
            return json.loads(text)

    def test_read_only_status_exposes_only_aggregate_session_metadata(self):
        report=self.run_fixture()
        self.assertEqual(report['sessions'],{'count':1,'latestIssuedUnix':1000,'latestExpiryUnix':1900})
        self.assertEqual(report['activeDeviceCount'],1)
        self.assertTrue(report['databaseHealthy'])

    def test_broad_permissions_fail_without_mutation_or_secret_output(self):
        self.assertFalse(all(self.run_fixture(False)['privatePermissions'].values()))


if __name__=='__main__':unittest.main()
