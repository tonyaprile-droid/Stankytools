from __future__ import annotations

import os
import shutil
from pathlib import Path
from time import time

APPDATA = Path(os.getenv("APPDATA") or (Path.home() / "AppData" / "Roaming")) / "StankyTools"
CACHE_DIR = APPDATA / "cache"
MAPS_DIR = CACHE_DIR / "maps"
GUILD_DIR = CACHE_DIR / "guild"
DATABASE_DIR = APPDATA / "database"
UPDATES_DIR = APPDATA / "updates"
SYNC_STATE_DIR = APPDATA / "sync_state"
LOG_DIR = APPDATA / "logs"

for folder in (APPDATA, CACHE_DIR, MAPS_DIR, GUILD_DIR, DATABASE_DIR, UPDATES_DIR, SYNC_STATE_DIR, LOG_DIR):
    folder.mkdir(parents=True, exist_ok=True)


class CacheManager:
    def __init__(self, root: Path = APPDATA) -> None:
        self.root = root

    def path(self, *parts: str) -> Path:
        p = self.root.joinpath(*parts)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def save_bytes(self, relative_path: str, data: bytes) -> Path:
        target = self.path(relative_path)
        target.write_bytes(data)
        return target

    def read_bytes(self, relative_path: str) -> bytes | None:
        target = self.path(relative_path)
        if not target.exists():
            return None
        return target.read_bytes()

    def cleanup_old_files(self, folder: Path, *, keep_newest: int = 3, max_age_days: int | None = None) -> int:
        if not folder.exists():
            return 0
        files = [p for p in folder.iterdir() if p.is_file()]
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        removed = 0
        cutoff = None if max_age_days is None else time() - (max_age_days * 86400)
        for idx, file in enumerate(files):
            too_many = idx >= keep_newest
            too_old = cutoff is not None and file.stat().st_mtime < cutoff
            if too_many or too_old:
                try:
                    file.unlink()
                    removed += 1
                except Exception:
                    pass
        return removed

    def clear_guild_cache(self, guild_id: str) -> None:
        target = GUILD_DIR / guild_id
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)


cache_manager = CacheManager()
