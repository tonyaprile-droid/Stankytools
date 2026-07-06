# StankyTools tzdata hotfix

This hotfix prevents Windows/PyInstaller builds from crashing when the IANA timezone database is missing. It also adds `tzdata` to requirements and bundles it in `StankyTools.spec`.
