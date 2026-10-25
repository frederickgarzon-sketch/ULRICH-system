# Credentials, Access, and Recovery

This document inventories every credential without copying live secrets. **Never place an actual password, access key, session secret, or SSH private key in documentation, screenshots, source control, or research exports.**

## Credential inventory

| Purpose | Account/key | Stored/configured at | Safe recovery or rotation |
|---|---|---|---|
| Researcher web login | `RESEARCHER_ACCESS_KEY` | Main laptop `.env` | Stop server, replace with a long random value, restart, invalidate old browser session |
| Browser session signing | `SESSION_SECRET` | Main laptop `.env` | Replace with a random 32+ character secret and restart; all logins are invalidated |
| Raspberry Pi SSH | user `piadmin` | Password is held by the authorized operator, not this repo | SSH to Pi, run `passwd`; prefer key-only authentication after validation |
| Dedicated Pi SSH key | public/private key pair | Windows user `.ssh\adhd_camera_node_ed25519*` | Create replacement key, add only the public key to Pi, test, then revoke old public key |
| Pi service configuration | non-secret camera/network settings | Pi service environment/config | Edit over SSH, restart camera service, verify `/health` |
| Database | no separate password for local SQLite | `data\behavioral_monitoring.db` | Protect with Windows account permissions and encrypted backups |
| Named-user six-digit PIN | encrypted recoverable value | Local database, encrypted with a key derived from `SESSION_SECRET` | Owner/Admin may view or replace it; rotating the session secret requires issuing new PINs |
| Participant-screen pairing | short-lived random capability token | Server memory and the participant URL/QR code | Generate a new pairing from the operator screen; the previous token is invalidated and tokens expire automatically |

The main `.env` and SSH private key must never be committed. `.env.example` files contain placeholders and safe defaults only.

## Finding the current researcher key

On the server laptop, an authorized administrator can inspect the local `.env` entry named `RESEARCHER_ACCESS_KEY`. The startup script may display the key locally for setup convenience; do not photograph or share that terminal. Prefer rotating it if it has been exposed.

## Required rotation now

Any password or access key previously pasted into chat, screenshots, tickets, or shared documents must be treated as exposed:

1. Change the Pi password with `passwd`.
2. Replace `RESEARCHER_ACCESS_KEY` and `SESSION_SECRET` in `.env`.
3. Restart the main server.
4. Verify the old access key no longer signs in.
5. Review Pi `~/.ssh/authorized_keys`; remove unknown keys only after verifying the new key works.

## Minimum operational controls

- Keep the system on a trusted private LAN; do not port-forward 8000 or 8090 to the internet.
- A public VPS is not suitable for direct raw camera streaming. If remote access is later required, use a VPN, TLS reverse proxy, strict authentication, encrypted storage, firewall allowlists, and an approved privacy/ethics plan.
- Use coded participant IDs and least-privilege accounts.
- Store backup ZIP files only on BitLocker or another approved encrypted location, define retention/deletion policy, and run `python scripts/verify_backup.py <backup.zip>` after every material backup or restore test.
- Treat participant pairing links and QR codes as temporary credentials. Do not photograph, publish, or reuse them for another session.
- Never store credentials in calibration profiles, notes, participant records, or exported reports.
- Rotate credentials after staff departure, suspected exposure, device loss, or handover.
