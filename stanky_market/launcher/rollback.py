from __future__ import annotations

from pathlib import Path

from .backup import BackupManager


class RollbackEngine:
    def __init__(self, backup_manager: BackupManager) -> None:
        self.backup_manager = backup_manager

    def rollback(self, backup_dir: str | Path) -> None:
        self.backup_manager.restore(backup_dir)
