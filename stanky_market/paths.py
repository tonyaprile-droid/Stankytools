from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def app_root() -> Path:
    """Return the application/install folder."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def local_app_data_dir() -> Path:
    """Return the persistent per-user data folder.

    This folder is outside the install/project directory so updates cannot
    remove guild membership, settings, POIs, downloaded artwork, videos,
    or the local database.
    """
    base = os.environ.get("LOCALAPPDATA")
    root = Path(base) / "StankyTools" if base else Path.home() / ".stankytools"
    root.mkdir(parents=True, exist_ok=True)
    return root


def bundled_root() -> Path:
    """Return where PyInstaller placed bundled read-only resources."""
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass).resolve()
        internal = app_root() / "_internal"
        if internal.exists():
            return internal
    return app_root()


def resource_path(*parts: str) -> Path:
    """Find a resource in install folder first, then bundled assets."""
    local = app_root().joinpath(*parts)
    if local.exists():
        return local
    bundled = bundled_root().joinpath(*parts)
    if bundled.exists():
        return bundled
    return local


def asset_dir() -> Path:
    return resource_path("assets")


def bundled_data_dir() -> Path:
    return resource_path("data")


def _copy_missing_tree(source: Path, target: Path) -> None:
    if not source.exists():
        return
    target.mkdir(parents=True, exist_ok=True)
    for item in source.rglob("*"):
        rel = item.relative_to(source)
        dest = target / rel
        if item.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
        elif not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(item, dest)
            except Exception:
                pass


def migrate_legacy_user_data() -> None:
    """Move/copy old install-folder user data to LocalAppData once.

    Older builds used <install>/data and <install>/logs. That caused users
    to lose guild membership after replacing the app folder during updates.
    This migration preserves existing files while never overwriting newer
    LocalAppData user files.
    """
    root = local_app_data_dir()
    marker = root / "config" / "migration_v1_complete.txt"
    if marker.exists():
        return
    try:
        for folder in ("data", "logs"):
            legacy = app_root() / folder
            target = root / folder
            _copy_missing_tree(legacy, target)
        (root / "config").mkdir(parents=True, exist_ok=True)
        marker.write_text("ok", encoding="utf-8")
    except Exception:
        # Migration failure should never block launch.
        pass


def data_dir() -> Path:
    """Return persistent user data folder for DBs, POIs, guild state, and caches."""
    migrate_legacy_user_data()
    target = local_app_data_dir() / "data"
    target.mkdir(parents=True, exist_ok=True)
    # Seed missing read-only defaults from bundled/project data without overwriting user files.
    for source in (bundled_root() / "data", app_root() / "data"):
        try:
            _copy_missing_tree(source, target)
        except Exception:
            pass
    return target


def cache_dir() -> Path:
    path = local_app_data_dir() / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_dir() -> Path:
    path = local_app_data_dir() / "config"
    path.mkdir(parents=True, exist_ok=True)
    return path


def logs_dir() -> Path:
    path = local_app_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path
