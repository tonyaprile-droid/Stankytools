from __future__ import annotations

from pathlib import Path
import shutil
import time


class BackupManager:
    def __init__(self, app_dir: str | Path, backup_root: str | Path) -> None:
        self.app_dir = Path(app_dir)
        self.backup_root = Path(backup_root)
        self.backup_root.mkdir(parents=True, exist_ok=True)

    def create_backup(self, version: str) -> Path:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup_dir = self.backup_root / f"{version}-{stamp}"
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        ignore = shutil.ignore_patterns("updates", "cache", "logs", "*.part")
        shutil.copytree(self.app_dir, backup_dir, ignore=ignore)
        return backup_dir

    def restore(self, backup_dir: str | Path) -> None:
        backup_dir = Path(backup_dir)
        if not backup_dir.exists():
            raise FileNotFoundError(f"Backup does not exist: {backup_dir}")
        for child in self.app_dir.iterdir():
            if child.name.lower() in {"cache", "updates", "logs"}:
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink(missing_ok=True)
        for child in backup_dir.iterdir():
            target = self.app_dir / child.name
            if child.is_dir():
                shutil.copytree(child, target, dirs_exist_ok=True)
            else:
                shutil.copy2(child, target)

    def cleanup_old_backups(self, keep: int = 3) -> None:
        backups = sorted([p for p in self.backup_root.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)
        for old in backups[keep:]:
            shutil.rmtree(old, ignore_errors=True)
