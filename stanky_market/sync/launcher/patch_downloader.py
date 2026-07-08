from __future__ import annotations

from pathlib import Path
import urllib.request

from .patch_plan import PatchPlan
from .file_hash import sha256_file


class PatchDownloadError(RuntimeError):
    pass


class PatchDownloader:
    def __init__(self, download_dir: str | Path):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def download_plan(self, plan: PatchPlan) -> list[Path]:
        downloaded: list[Path] = []
        for item in plan.files:
            mf = item.manifest_file
            if not mf.url:
                raise PatchDownloadError(f"No URL for {mf.path}")
            target = self.download_dir / mf.path
            target.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(mf.url, target)
            if target.stat().st_size != mf.size:
                raise PatchDownloadError(f"Size check failed for {mf.path}")
            if sha256_file(target).lower() != mf.sha256.lower():
                raise PatchDownloadError(f"Hash check failed for {mf.path}")
            downloaded.append(target)
        return downloaded
