from __future__ import annotations

import json
import shutil
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .hash_utils import file_matches, sha256_file
from .manifest import UpdateManifest, ManifestFile
from .paths import app_root, updates_dir, backup_dir

DEFAULT_MANIFEST_URL = "https://github.com/StankylegTools/StankyTools-Releases/releases/latest/download/manifest.json"


@dataclass
class UpdateResult:
    updated: bool = False
    version: str = ""
    error: str | None = None


class PatchClient:
    def __init__(self, manifest_url: str | None = None):
        self.manifest_url = manifest_url or DEFAULT_MANIFEST_URL
        self.root = app_root()
        self.stage = updates_dir() / "stage"
        self.stage.mkdir(parents=True, exist_ok=True)

    def fetch_manifest(self) -> UpdateManifest:
        with urllib.request.urlopen(self.manifest_url, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
        return UpdateManifest.from_dict(data)

    def changed_files(self, manifest: UpdateManifest) -> list[ManifestFile]:
        changed: list[ManifestFile] = []
        for item in manifest.files:
            local_path = self.root / item.path
            if not file_matches(local_path, item.sha256):
                changed.append(item)
        return changed

    def download_file(self, item: ManifestFile) -> Path:
        if not item.url:
            raise ValueError(f"No download URL for {item.path}")
        target = self.stage / item.path
        target.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(item.url, target)
        if sha256_file(target).lower() != item.sha256.lower():
            raise RuntimeError(f"Hash mismatch for {item.path}")
        return target

    def backup_file(self, relative_path: str, version: str) -> None:
        source = self.root / relative_path
        if not source.exists():
            return
        target = backup_dir(version) / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    def apply_file(self, staged: Path, relative_path: str) -> None:
        target = self.root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(staged, target)

    def update_if_needed(self) -> UpdateResult:
        try:
            manifest = self.fetch_manifest()
            changed = self.changed_files(manifest)
            if not changed:
                return UpdateResult(updated=False, version=manifest.version)

            downloaded: list[tuple[ManifestFile, Path]] = []
            for item in changed:
                downloaded.append((item, self.download_file(item)))

            for item, staged in downloaded:
                self.backup_file(item.path, manifest.version)
                self.apply_file(staged, item.path)

            return UpdateResult(updated=True, version=manifest.version)
        except Exception as exc:
            return UpdateResult(updated=False, error=str(exc))


