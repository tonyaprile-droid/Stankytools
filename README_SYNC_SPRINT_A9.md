# StankyTools Phase 4 Sprint A9 — Launcher + Patch Client

Adds the first working patch-updater foundation:

- `stanky_market/launcher/launcher.py`
- `stanky_market/updater2/patch_client.py`
- Manifest model and SHA-256 verification
- Changed-file detection
- Staging, backup, and apply flow
- GitHub Actions manifest builder
- Uses new GitHub owner: `TheStankylegTools`

This is a foundation package. The next sprint wires launcher build output into PyInstaller and adds restart UX.
