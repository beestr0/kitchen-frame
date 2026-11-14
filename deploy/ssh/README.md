# Persistent Mint SSH access

Use `ssh pf1007l-mint` for native Terminal and
`ssh -o BatchMode=yes pf1007l-mint 'id -un'` for unattended verification.
Do not depend on the old `/private/tmp/pf1007l-server-ssh/control` socket.

`setup_mint.py` runs only in a native Mac Terminal. It creates or reuses the dedicated
`~/.ssh/id_ed25519_pf1007l_mint` key, prompts privately for a passphrase, adds the key
to the macOS agent/Keychain, preserves unrelated SSH config, and installs only the
matching public key with `ssh-copy-id`. It never reads private key contents. The
private key remains on this Mac, mode 0600, inside a 0700 SSH directory. No key is
stored in the repository. Existing keys and server daemon settings stay unchanged.

The alias sets the fixed Mint IP/user/port, `IdentitiesOnly yes`, strict host-key
checking and Keychain support. Password authentication on Mint is not disabled.
macOS login Keychain must remain available for a passphrase-protected key after
agent restart; locking the Keychain, revoking the authorized key, changing the host
key or moving to another Mac may require owner interaction. An expired temporary
socket alone no longer prevents authentication.

Native setup (if not already complete):

```sh
python3 /Users/beestrother/Projects/kitchen-frame/deploy/ssh/setup_mint.py
```

Enter passwords only in that Terminal; do not record/tee the session. A host-key
mismatch must be investigated rather than bypassed. Confirm final success marker
and then independently verify BatchMode from the agent environment. Never copy the
private key to Linux. Sudo is separate and may still require a private password.
