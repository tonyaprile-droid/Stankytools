\
from __future__ import annotations

import shutil
import time
from pathlib import Path


class HealthMonitor:
    def __init__(self, appdata_dir: Path | None = None):
        self.appdata_dir = appdata_dir or Path.home() / "AppData" / "Roaming" / "StankyTools"
        self.started_at = time.time()

    def cache_size_bytes(self) -> int:
        cache = self.appdata_dir / "cache"
        if not cache.exists():
            return 0

        total = 0
        for p in cache.rglob("*"):
            if p.is_file():
                try:
                    total += p.stat().st_size
                except OSError:
                    pass
        return total

    def free_disk_bytes(self) -> int:
        usage = shutil.disk_usage(self.appdata_dir if self.appdata_dir.exists() else Path.home())
        return usage.free

    def uptime_seconds(self) -> int:
        return int(time.time() - self.started_at)

    def snapshot(self) -> dict:
        return {
            "appdata_dir": str(self.appdata_dir),
            "cache_size_bytes": self.cache_size_bytes(),
            "free_disk_bytes": self.free_disk_bytes(),
            "uptime_seconds": self.uptime_seconds(),
        }
