from __future__ import annotations

from pathlib import Path

from .cache import UPDATES


class UpdateCleanup:
    """Keeps downloaded update packages from growing forever."""

    def __init__(self, root: Path = UPDATES):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def keep_latest(self, keep: int = 2) -> int:
        packages = sorted(
            [p for p in self.root.glob("*.zip") if p.is_file()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        removed = 0
        for package in packages[keep:]:
            try:
                package.unlink(missing_ok=True)
                removed += 1
            except OSError:
                pass
        return removed
