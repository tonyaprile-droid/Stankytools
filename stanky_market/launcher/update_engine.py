from __future__ import annotations

from pathlib import Path
import shutil

from .backup import BackupManager
from .downloader import ResumableDownloader
from .hash_verify import verify_file
from .manifest import UpdateManifest
from .progress import ProgressCallback, UpdateProgress, noop_progress
from .rollback import RollbackEngine


class UpdateEngineError(RuntimeError):
    pass


class UpdateEngine:
    def __init__(self, app_dir: str | Path, update_dir: str | Path, backup_dir: str | Path, user_agent: str = "StankyToolsUpdater/1.0") -> None:
        self.app_dir = Path(app_dir)
        self.update_dir = Path(update_dir)
        self.update_dir.mkdir(parents=True, exist_ok=True)
        self.backup = BackupManager(self.app_dir, backup_dir)
        self.rollback = RollbackEngine(self.backup)
        self.downloader = ResumableDownloader(user_agent=user_agent)

    def changed_files(self, manifest: UpdateManifest) -> list:
        changed = []
        for item in manifest.files:
            local = self.app_dir / item.path
            if not local.exists() or not verify_file(local, item.sha256):
                changed.append(item)
        return changed

    def download_changed_files(self, manifest: UpdateManifest, progress: ProgressCallback = noop_progress) -> list[Path]:
        downloads: list[Path] = []
        changed = self.changed_files(manifest)
        total = max(len(changed), 1)
        for index, item in enumerate(changed, start=1):
            if not item.url:
                raise UpdateEngineError(f"Missing download URL for {item.path}")
            target = self.update_dir / item.path
            progress(UpdateProgress("downloading", int((index - 1) * 100 / total), f"Downloading {item.path}"))
            self.downloader.download(item.url, target, progress)
            if not verify_file(target, item.sha256):
                raise UpdateEngineError(f"Hash verification failed for {item.path}")
            downloads.append(target)
        progress(UpdateProgress("ready", 100, "Update ready to install"))
        return downloads

    def install(self, manifest: UpdateManifest, current_version: str, progress: ProgressCallback = noop_progress) -> None:
        backup_dir = self.backup.create_backup(current_version)
        progress(UpdateProgress("backup", 5, "Backup created"))
        try:
            changed = self.changed_files(manifest)
            total = max(len(changed), 1)
            for index, item in enumerate(changed, start=1):
                source = self.update_dir / item.path
                target = self.app_dir / item.path
                if not source.exists():
                    raise UpdateEngineError(f"Downloaded file missing: {source}")
                if not verify_file(source, item.sha256):
                    raise UpdateEngineError(f"Hash verification failed before install: {item.path}")
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                progress(UpdateProgress("installing", int(index * 100 / total), f"Installed {item.path}"))
            self.backup.cleanup_old_backups()
            progress(UpdateProgress("installed", 100, f"Installed {manifest.version}"))
        except Exception:
            progress(UpdateProgress("rollback", 0, "Install failed; restoring previous version"))
            self.rollback.rollback(backup_dir)
            raise

    def cleanup_downloads(self) -> None:
        for child in self.update_dir.iterdir():
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            else:
                child.unlink(missing_ok=True)
