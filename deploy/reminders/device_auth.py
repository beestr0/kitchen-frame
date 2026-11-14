"""Opt-in device-v1 authentication: registered P-256 keys, one-use proof, expiring sessions.

No enrollment HTTP endpoint. An owner-reviewed registry is supplied separately.
The server stores public keys and session hashes, never device private keys.
"""
import base64
import hashlib
import hmac
import re
import secrets
import sqlite3
import subprocess
import tempfile
import time
from pathlib import Path

COOKIE = 'pf1007l-device'
PREFIX = '/__reminders-demo/'
SESSION_SECONDS = 900
CHALLENGE_SECONDS = 60
P256_SPKI_PREFIX = bytes.fromhex('3059301306072a8648ce3d020106082a8648ce3d03010703420004')


class AuthError(Exception):
    def __init__(self, status=401, code='device_auth_required'):
        self.status, self.code = status, code


def public_der(value):
    try:
        data = base64.b64decode(value, validate=True)
    except (ValueError, TypeError):
        raise ValueError('Invalid device public key') from None
    if len(data) != 91 or not data.startswith(P256_SPKI_PREFIX):
        raise ValueError('Only uncompressed P-256 SPKI public keys are supported')
    return data


def device_id(value):
    return hashlib.sha256(public_der(value)).hexdigest()


def verify_signature(key, message, signature):
    try:
        sig = base64.b64decode(signature, validate=True)
        if not 64 <= len(sig) <= 80:
            return False
        with tempfile.TemporaryDirectory(prefix='pf1007l-proof-') as temporary:
            directory = Path(temporary)
            public = directory / 'public.der'
            proof = directory / 'signature.der'
            public.write_bytes(public_der(key)); public.chmod(0o600)
            proof.write_bytes(sig); proof.chmod(0o600)
            # All secret/proof material stays out of process arguments and logs.
            result = subprocess.run(['openssl', 'dgst', '-sha256', '-keyform', 'DER',
                                     '-verify', str(public), '-signature', str(proof)],
                                    input=message.encode('ascii'), capture_output=True, timeout=5)
            return result.returncode == 0
    except (ValueError, OSError, subprocess.SubprocessError):
        return False


def cookie_token(header):
    values = []
    for field in (header or '').split(';'):
        name, separator, value = field.strip().partition('=')
        if separator and name == COOKIE:
            values.append(value)
    if len(values) != 1 or not re.fullmatch(r'[a-f0-9]{64}', values[0]):
        raise AuthError()
    return values[0]


class DeviceAuth:
    def __init__(self, database, registry, origin, csrf_secret, clock=time.time, verifier=verify_signature):
        if not origin.startswith('https://') or len(csrf_secret) < 32:
            raise ValueError('HTTPS audience and strong CSRF secret required')
        self.db, self.origin, self.csrf_secret = database, origin, csrf_secret
        self.clock, self.verifier = clock, verifier
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS device_keys (
            id TEXT PRIMARY KEY, public_key TEXT NOT NULL, active INTEGER NOT NULL, epoch INTEGER NOT NULL);
          CREATE TABLE IF NOT EXISTS device_challenges (
            id TEXT PRIMARY KEY, device TEXT NOT NULL, nonce TEXT NOT NULL,
            issued REAL NOT NULL, expires REAL NOT NULL, consumed INTEGER NOT NULL DEFAULT 0,
            epoch INTEGER NOT NULL DEFAULT 1);
          CREATE TABLE IF NOT EXISTS device_sessions (
            hash TEXT PRIMARY KEY, device TEXT NOT NULL, epoch INTEGER NOT NULL,
            issued REAL NOT NULL, expires REAL NOT NULL);
          CREATE TABLE IF NOT EXISTS device_rate (device TEXT PRIMARY KEY, window REAL, attempts INTEGER);
        ''')
        if 'epoch' not in {row[1] for row in self.db.execute('PRAGMA table_info(device_challenges)')}:
            self.db.execute('ALTER TABLE device_challenges ADD COLUMN epoch INTEGER NOT NULL DEFAULT 1')
        if 'attempts' not in {row[1] for row in self.db.execute('PRAGMA table_info(device_challenges)')}:
            self.db.execute('ALTER TABLE device_challenges ADD COLUMN attempts INTEGER NOT NULL DEFAULT 0')
        self.sync_registry(registry)

    def sync_registry(self, registry):
        if not isinstance(registry, dict) or type(registry.get('version')) is not int or registry.get('version') != 1 or not isinstance(registry.get('devices'), list):
            raise ValueError('Owner-provisioned device registry v1 required')
        devices = registry['devices']
        if len(devices) > 16:
            raise ValueError('Device registry limit exceeded')
        prepared, seen = [], set()
        for entry in devices:
            if not isinstance(entry, dict) or not {'publicKey', 'id', 'enabled'} <= entry.keys():
                raise ValueError('Invalid device registry entry')
            identifier = device_id(entry['publicKey'])
            if identifier != entry['id'] or identifier in seen or type(entry.get('enabled')) is not bool:
                raise ValueError('Invalid or duplicate device registry entry')
            epoch = entry.get('epoch', 1)
            if type(epoch) is not int or not 1 <= epoch <= 2147483647:
                raise ValueError('Invalid device credential epoch')
            seen.add(identifier)
            prepared.append((identifier, entry['publicKey'], int(entry['enabled']), epoch))
        # Validate everything before changing any authorization state.
        with self.db:
            self.db.execute('UPDATE device_keys SET active=0')
            self.db.executemany('INSERT INTO device_keys VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET public_key=excluded.public_key,active=excluded.active,epoch=excluded.epoch', prepared)
            self.db.execute('DELETE FROM device_sessions WHERE NOT EXISTS (SELECT 1 FROM device_keys k WHERE k.id=device_sessions.device AND k.active=1 AND k.epoch=device_sessions.epoch)')
            self.db.execute('DELETE FROM device_challenges WHERE NOT EXISTS (SELECT 1 FROM device_keys k WHERE k.id=device_challenges.device AND k.active=1 AND k.epoch=device_challenges.epoch)')

    def cleanup(self, now):
        self.db.execute('DELETE FROM device_challenges WHERE expires<? OR issued>?', (now - 60, now + 60))
        self.db.execute('DELETE FROM device_sessions WHERE expires<=? OR issued>?', (now, now + 60))
        self.db.execute('DELETE FROM device_rate WHERE window<?', (now - 3600,))

    def challenge(self, identifier):
        if not isinstance(identifier, str) or not re.fullmatch(r'[a-f0-9]{64}', identifier):
            raise AuthError(403, 'device_not_authorized')
        key = self.db.execute('SELECT active,epoch FROM device_keys WHERE id=?', (identifier,)).fetchone()
        if not key or key[0] != 1:
            raise AuthError(403, 'device_not_authorized')
        now = self.clock()
        with self.db:
            self.cleanup(now)
            rate = self.db.execute('SELECT window,attempts FROM device_rate WHERE device=?', (identifier,)).fetchone()
            start, attempts = rate if rate and 0 <= now - rate[0] < 60 else (now, 0)
            if attempts >= 5:
                raise AuthError(429, 'device_rate_limited')
            self.db.execute('INSERT OR REPLACE INTO device_rate VALUES (?,?,?)', (identifier, start, attempts + 1))
            identifier_challenge, nonce = secrets.token_hex(16), secrets.token_hex(32)
            self.db.execute('INSERT INTO device_challenges(id,device,nonce,issued,expires,epoch) VALUES (?,?,?,?,?,?)',
                            (identifier_challenge, identifier, nonce, now, now + CHALLENGE_SECONDS, key[1]))
        return {'id': identifier_challenge, 'device': identifier, 'nonce': nonce,
                'audience': self.origin, 'expiresIn': CHALLENGE_SECONDS, 'purpose': 'session',
                'message': self.message(identifier, identifier_challenge, nonce)}

    def message(self, identifier, challenge, nonce):
        return 'PF1007L-DEVICE-V1\n' + self.origin + '\nsession\n' + identifier + '\n' + challenge + '\n' + nonce

    def prove(self, identifier, challenge, signature):
        if not isinstance(identifier, str) or not re.fullmatch(r'[a-f0-9]{64}', identifier) or not isinstance(challenge, str) or not re.fullmatch(r'[a-f0-9]{32}', challenge) or not isinstance(signature, str) or len(signature) > 120:
            raise AuthError(400, 'invalid_device_proof')
        row = self.db.execute('SELECT device,nonce,issued,expires,consumed,epoch FROM device_challenges WHERE id=?', (challenge,)).fetchone()
        key = self.db.execute('SELECT public_key,active,epoch FROM device_keys WHERE id=?', (identifier,)).fetchone()
        now = self.clock()
        if not row or row[0] != identifier or row[4] or not row[2] <= now < row[3] or not key or key[1] != 1 or row[5] != key[2]:
            raise AuthError(401, 'invalid_device_proof')
        # Bound subprocess work even when one captured challenge is attacked.
        with self.db:
            attempt = self.db.execute('UPDATE device_challenges SET attempts=attempts+1 WHERE id=? AND consumed=0 AND attempts<3', (challenge,))
            if attempt.rowcount != 1:
                raise AuthError(429, 'device_rate_limited')
        if not self.verifier(key[0], self.message(identifier, challenge, row[1]), signature):
            raise AuthError(401, 'invalid_device_proof')
        token = secrets.token_hex(32)
        digest = hashlib.sha256(token.encode()).hexdigest()
        with self.db:
            current = self.db.execute('SELECT active,epoch FROM device_keys WHERE id=?', (identifier,)).fetchone()
            if not current or current[0] != 1 or current[1] != key[2]:
                raise AuthError(401, 'invalid_device_proof')
            # Consume atomically; replay and parallel proofs cannot issue another session.
            cursor = self.db.execute('UPDATE device_challenges SET consumed=1 WHERE id=? AND consumed=0 AND expires>?', (challenge, now))
            if cursor.rowcount != 1:
                raise AuthError(401, 'invalid_device_proof')
            self.db.execute('INSERT INTO device_sessions VALUES (?,?,?,?,?)', (digest, identifier, key[2], now, now + SESSION_SECONDS))
            self.cleanup(now)
            self.db.execute('DELETE FROM device_sessions WHERE device=? AND hash NOT IN (SELECT hash FROM device_sessions WHERE device=? ORDER BY issued DESC,rowid DESC LIMIT 3)', (identifier, identifier))
        return token, self.session(token)

    def session(self, token):
        if not isinstance(token, str) or not re.fullmatch(r'[a-f0-9]{64}', token):
            raise AuthError()
        now = self.clock()
        digest = hashlib.sha256(token.encode()).hexdigest()
        row = self.db.execute('SELECT s.device,s.issued,s.expires FROM device_sessions s JOIN device_keys k ON k.id=s.device WHERE s.hash=? AND s.epoch=k.epoch AND k.active=1', (digest,)).fetchone()
        if not row or not row[1] <= now < row[2]:
            raise AuthError()
        csrf = hmac.new(self.csrf_secret.encode(), (token + '\0' + row[0]).encode(), hashlib.sha256).hexdigest()
        return {'mode': 'device-v1', 'csrf': csrf, 'expiresIn': max(0, int(row[2] - now)), 'demo': True}

    def authenticate(self, header):
        return self.session(cookie_token(header))

    @staticmethod
    def cookie(token):
        return COOKIE + '=' + token + '; Path=' + PREFIX + '; Secure; HttpOnly; SameSite=Strict; Max-Age=' + str(SESSION_SECONDS)
