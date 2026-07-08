from __future__ import annotations

import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .cache import CACHE, MAPS, UPDATES, GUILD


@dataclass(slots=True)
class CleanupResult:
    files_removed: int = 0
    bytes_removed: int = 0
    folders_removed: int = 0

    def add_file(self, path: Path) -> None:
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        self.files_removed += 1
        self.bytes_removed += size


class CacheCleanup:
    """Safe cache cleanup for runtime files stored under AppData.

    This class never touches the application install folder. It only removes
    cache/update/map files under the StankyTools AppData cache paths.
    """

    def __init__(self, cache_root: Path = CACHE):
        self.cache_root = Path(cache_root)

    def run_startup_cleanup(self) -> CleanupResult:
        result = CleanupResult()
        self.remove_old_update_packages(result=result)
        self.rotate_weekly_maps(keep=3, result=result)
        self.remove_temp_files(result=result)
        self.remove_empty_folders(result=result)
        return result

    def remove_old_update_packages(self, keep: int = 2, result: CleanupResult | None = None) -> CleanupResult:
        result = result or CleanupResult()
        packages = sorted(
            [p for p in UPDATES.glob("*.zip") if p.is_file()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for package in packages[keep:]:
            self._delete_file(package, result)
        return result

    def rotate_weekly_maps(self, keep: int = 4, result: CleanupResult | None = None) -> CleanupResult:
        result = result or CleanupResult()
        maps = sorted(
            [p for p in MAPS.glob("deep_desert*.webp") if p.is_file()] +
            [p for p in MAPS.glob("deep_desert*.png") if p.is_file()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for old_map in maps[keep:]:
            self._delete_file(old_map, result)
        return result

    def remove_temp_files(self, max_age_hours: int = 24, result: CleanupResult | None = None) -> CleanupResult:
        result = result or CleanupResult()
        cutoff = time.time() - (max_age_hours * 3600)
        patterns = ("*.tmp", "*.part", "*.download", "*.bak")
        for pattern in patterns:
            for path in self.cache_root.rglob(pattern):
                if path.is_file() and path.stat().st_mtime < cutoff:
                    self._delete_file(path, result)
        return result

    def remove_empty_folders(self, result: CleanupResult | None = None) -> CleanupResult:
        result = result or CleanupResult()
        for folder in sorted(self.cache_root.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            if folder.is_dir():
                try:
                    next(folder.iterdir())
                except StopIteration:
                    try:
                        folder.rmdir()
                        result.folders_removed += 1
                    except OSError:
                        pass
                except OSError:
                    pass
        return result

    def purge_guild_cache(self, guild_id: str) -> CleanupResult:
        result = CleanupResult()
        safe_id = str(guild_id).strip()
        if not safe_id:
            return result
        target = GUILD / safe_id
        if target.exists() and target.is_dir():
            bytes_removed = self._folder_size(target)
            shutil.rmtree(target, ignore_errors=True)
            result.folders_removed += 1
            result.bytes_removed += bytes_removed
        return result

    def cache_size_bytes(self) -> int:
        return self._folder_size(self.cache_root)

    @staticmethod
    def _folder_size(folder: Path) -> int:
        total = 0
        if not folder.exists():
            return total
        for path in folder.rglob("*"):
            if path.is_file():
                try:
                    total += path.stat().st_size
                except OSError:
                    pass
        return total

    @staticmethod
    def _delete_file(path: Path, result: CleanupResult) -> None:
        try:
            result.add_file(path)
            path.unlink(missing_ok=True)
        except OSError:
            pass
