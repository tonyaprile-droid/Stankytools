from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ManifestFile:
    path: str
    sha256: str
    size: int
    url: str | None = None


@dataclass
class UpdateManifest:
    version: str
    files: list[ManifestFile] = field(default_factory=list)
    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UpdateManifest":
        return cls(
            version=str(data.get("version", "0.0.0")),
            notes=str(data.get("notes", "")),
            files=[ManifestFile(**item) for item in data.get("files", [])],
        )
