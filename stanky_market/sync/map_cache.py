from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from .cache import MAPS


class MapCache:
    """Stores the current Deep Desert map and rotates older map captures."""

    CURRENT_NAME = "deep_desert_latest.webp"

    def __init__(self, root: Path = MAPS):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    @property
    def current_map(self) -> Path:
        return self.root / self.CURRENT_NAME

    def save_current(self, source: str | Path) -> Path:
        source = Path(source)
        if not source.exists():
            raise FileNotFoundError(source)
        self.archive_current()
        shutil.copy2(source, self.current_map)
        return self.current_map

    def archive_current(self) -> Path | None:
        if not self.current_map.exists():
            return None
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archived = self.root / f"deep_desert_{stamp}{self.current_map.suffix}"
        shutil.copy2(self.current_map, archived)
        return archived

    def latest(self) -> Path | None:
        if self.current_map.exists():
            return self.current_map
        maps = sorted(self.root.glob("deep_desert*.*"), key=lambda p: p.stat().st_mtime, reverse=True)
        return maps[0] if maps else None
