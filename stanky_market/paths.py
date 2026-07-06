from __future__ import annotations

import sys
from pathlib import Path


def app_root() -> Path:
    """Return the installed application root.

    In development this is the project folder. In a PyInstaller one-folder
    build this is the folder next to StankyTools.exe, not _internal.
    That keeps data/, logs/, and user settings outside bundled code so
    updates never overwrite guild membership or local cache.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def asset_dir() -> Path:
    return app_root() / "assets"


def data_dir() -> Path:
    return app_root() / "data"


def logs_dir() -> Path:
    return app_root() / "logs"
