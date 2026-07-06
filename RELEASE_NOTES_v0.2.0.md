# StankyTools v0.2.0 — Phase 2 + Phase 4 Preview

## What's new
- Fixed startup crash caused by escaped QSS/style braces.
- Added local Guild System support so the app works before Supabase is configured.
- Added guild profile, guild news, and wider news table layout.
- Improved Guild News columns: Latest News | Poster | Date.
- Added Deep Desert page foundation with embedded Method.gg map support.
- Added map filter persistence and Tuesday refresh framework.
- Reduced/suppressed harmless Qt WebEngine console spam from embedded web content.
- Added safe font sizing to avoid QFont point-size warnings.

## Known notes
- Some embedded-map warnings may still appear depending on Method.gg/Google ad scripts. These are not app crashes.
- Windows EXE release should be built by GitHub Actions or PyInstaller on Windows.

## Run from source
```powershell
pip install -r requirements.txt
py main.py
```

## Build release from GitHub
Push this version to `main`, then create a version tag:
```powershell
git add .
git commit -m "Release StankyTools v0.2.0"
git tag v0.2.0
git push origin main --tags
```

The included GitHub Actions workflow will build `StankyTools-Windows.zip` and attach it to the GitHub Release when the tag is pushed.
