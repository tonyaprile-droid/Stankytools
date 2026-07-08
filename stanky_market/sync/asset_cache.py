from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from .cache import GUILD


class AssetCache:
    """Caches guild logos, banners, and small downloaded assets in AppData."""

    def __init__(self, root: Path = GUILD):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def guild_folder(self, guild_id: str) -> Path:
        folder = self.root / str(guild_id)
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def save_guild_asset(self, guild_id: str, name: str, source: str | Path) -> Path:
        source = Path(source)
        if not source.exists():
            raise FileNotFoundError(source)
        suffix = source.suffix.lower() or ".webp"
        target = self.guild_folder(guild_id) / f"{name}{suffix}"
        shutil.copy2(source, target)
        return target

    def asset_path(self, guild_id: str, name: str) -> Path | None:
        folder = self.guild_folder(guild_id)
        matches = list(folder.glob(f"{name}.*"))
        return matches[0] if matches else None

    @staticmethod
    def sha256(path: str | Path) -> str:
        h = hashlib.sha256()
        with Path(path).open("rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                h.update(block)
        return h.hexdigest()
