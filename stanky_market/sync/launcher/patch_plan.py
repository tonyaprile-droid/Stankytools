from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .file_hash import sha256_file
from .manifest import UpdateManifest, ManifestFile


@dataclass(slots=True)
class PatchFile:
    manifest_file: ManifestFile
    local_path: Path
    reason: str


@dataclass(slots=True)
class PatchPlan:
    version: str
    files: list[PatchFile]

    @property
    def total_size(self) -> int:
        return sum(item.manifest_file.size for item in self.files)

    @property
    def is_empty(self) -> bool:
        return not self.files


def build_patch_plan(app_root: str | Path, manifest: UpdateManifest) -> PatchPlan:
    app_root = Path(app_root)
    needed: list[PatchFile] = []

    for mf in manifest.files:
        local = app_root / mf.path
        if not local.exists():
            needed.append(PatchFile(mf, local, "missing"))
            continue
        if local.stat().st_size != mf.size:
            needed.append(PatchFile(mf, local, "size_mismatch"))
            continue
        if sha256_file(local).lower() != mf.sha256.lower():
            needed.append(PatchFile(mf, local, "hash_mismatch"))
            continue

    return PatchPlan(version=manifest.version, files=needed)
