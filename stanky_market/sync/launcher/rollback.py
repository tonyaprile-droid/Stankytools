from __future__ import annotations

from pathlib import Path
import shutil
from datetime import datetime


class RollbackManager:
    def __init__(self, app_root: str | Path, backup_root: str | Path):
        self.app_root = Path(app_root)
        self.backup_root = Path(backup_root)
        self.backup_root.mkdir(parents=True, exist_ok=True)

    def create_backup(self, relative_files: list[str]) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.backup_root / stamp
        backup_dir.mkdir(parents=True, exist_ok=True)
        for rel in relative_files:
            src = self.app_root / rel
            if src.exists():
                dst = backup_dir / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        return backup_dir

    def restore(self, backup_dir: str | Path) -> None:
        backup_dir = Path(backup_dir)
        for src in backup_dir.rglob("*"):
            if src.is_file():
                rel = src.relative_to(backup_dir)
                dst = self.app_root / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
