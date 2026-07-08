# Phase 4 Sprint A13 - Intelligent Patch Delivery

This package adds the production patch-delivery foundation for StankyTools.

## Included

- Manifest v2 parser/writer
- Differential patch plan engine
- SHA-256 integrity verification
- Resumable download manager
- Bandwidth throttling support
- Stable/Beta/Dev update channels
- Background update service
- Restart manager
- Launcher updater client
- Update settings model

## Intended integration

1. Generate `manifest_v2.json` during GitHub Actions release builds.
2. Upload changed application files and the manifest as release assets.
3. Launcher fetches the manifest before starting StankyTools.
4. Patch engine compares local files to the manifest.
5. Downloader retrieves only changed files.
6. Integrity verifier checks SHA-256.
7. Patch engine replaces changed files.
8. Restart manager launches the updated app.

## Notes

This sprint is infrastructure. Existing StankyTools code still needs to be wired into these modules.
