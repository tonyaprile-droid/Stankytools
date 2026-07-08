from __future__ import annotations

import os
from pathlib import Path


def app_root() -> Path:
    return Path(getattr(__import__('sys'), '_MEIPASS', Path.cwd())).resolve()


def user_data_root() -> Path:
    base = os.environ.get("APPDATA")
    if base:
        root = Path(base) / "StankyTools"
    else:
        root = Path.home() / ".stankytools"
    root.mkdir(parents=True, exist_ok=True)
    return root


def updates_dir() -> Path:
    p = user_data_root() / "updates"
    p.mkdir(parents=True, exist_ok=True)
    return p


def backup_dir(version: str) -> Path:
    p = user_data_root() / "backups" / version
    p.mkdir(parents=True, exist_ok=True)
    return p
