from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import threading
import time
from typing import Callable

from .manifest_v2 import ManifestV2
from .patch_engine import PatchEngine
from .download_manager import DownloadManager


@dataclass(slots=True)
class BackgroundUpdateResult:
    version: str
    downloaded_files: int
    total_bytes: int


class BackgroundUpdateService:
    def __init__(self, install_dir: str | Path, download_dir: str | Path, channel: str = "stable"):
        self.patch_engine = PatchEngine(install_dir, channel)
        self.downloader = DownloadManager(download_dir)
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start_once(self, manifest: ManifestV2, done: Callable[[BackgroundUpdateResult], None] | None = None, error: Callable[[Exception], None] | None = None) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run_once, args=(manifest, done, error), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run_once(self, manifest: ManifestV2, done, error) -> None:
        try:
            plan = self.patch_engine.build_plan(manifest)
            downloaded = 0
            total_bytes = 0
            for item in plan.items:
                if self._stop.is_set():
                    return
                if not item.needs_download or not item.manifest_file.url:
                    continue
                filename = item.manifest_file.path.replace("/", "_").replace("\\", "_")
                local = self.downloader.download(item.manifest_file.url, filename)
                self.patch_engine.apply_file(local, item)
                downloaded += 1
                total_bytes += item.manifest_file.size
            if done:
                done(BackgroundUpdateResult(manifest.version, downloaded, total_bytes))
        except Exception as exc:
            if error:
                error(exc)
