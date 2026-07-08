from __future__ import annotations

from pathlib import Path
import shutil

from .patch_plan import PatchPlan
from .rollback import RollbackManager
from .file_hash import sha256_file


class PatchApplyError(RuntimeError):
    pass


class PatchApplier:
    def __init__(self, app_root: str | Path, download_root: str | Path, backup_root: str | Path):
        self.app_root = Path(app_root)
        self.download_root = Path(download_root)
        self.rollback = RollbackManager(app_root, backup_root)

    def apply(self, plan: PatchPlan) -> None:
        rel_files = [item.manifest_file.path for item in plan.files]
        backup = self.rollback.create_backup(rel_files)
        try:
            for item in plan.files:
                mf = item.manifest_file
                src = self.download_root / mf.path
                dst = self.app_root / mf.path
                if not src.exists():
                    raise PatchApplyError(f"Downloaded file missing: {mf.path}")
                if sha256_file(src).lower() != mf.sha256.lower():
                    raise PatchApplyError(f"Downloaded file hash mismatch: {mf.path}")
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        except Exception:
            self.rollback.restore(backup)
            raise
