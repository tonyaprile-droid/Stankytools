from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import shutil

from .integrity import sha256_file, verify_sha256
from .manifest_v2 import ManifestV2, ManifestFile
from .channels import channel_allows_file


@dataclass(slots=True)
class PatchPlanItem:
    manifest_file: ManifestFile
    target_path: Path
    needs_download: bool
    reason: str


@dataclass(slots=True)
class PatchPlan:
    version: str
    items: list[PatchPlanItem]

    @property
    def download_count(self) -> int:
        return sum(1 for item in self.items if item.needs_download)

    @property
    def download_size(self) -> int:
        return sum(item.manifest_file.size for item in self.items if item.needs_download)


class PatchEngine:
    def __init__(self, install_dir: str | Path, channel: str = "stable"):
        self.install_dir = Path(install_dir)
        self.channel = channel

    def build_plan(self, manifest: ManifestV2) -> PatchPlan:
        items: list[PatchPlanItem] = []
        for mf in manifest.files:
            if not channel_allows_file(self.channel, mf.channel):
                continue
            target = self.install_dir / mf.path
            needs, reason = self._needs_download(target, mf)
            items.append(PatchPlanItem(mf, target, needs, reason))
        return PatchPlan(manifest.version, items)

    def _needs_download(self, target: Path, mf: ManifestFile) -> tuple[bool, str]:
        if not target.exists():
            return True, "missing"
        if target.stat().st_size != mf.size:
            return True, "size mismatch"
        try:
            if sha256_file(target).lower() != mf.sha256.lower():
                return True, "hash mismatch"
        except OSError:
            return True, "unreadable"
        return False, "current"

    def apply_file(self, downloaded_file: str | Path, plan_item: PatchPlanItem) -> None:
        source = Path(downloaded_file)
        if not verify_sha256(source, plan_item.manifest_file.sha256):
            raise ValueError(f"Integrity check failed for {plan_item.manifest_file.path}")
        target = plan_item.target_path
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".new")
        shutil.copy2(source, tmp)
        os.replace(tmp, target)
