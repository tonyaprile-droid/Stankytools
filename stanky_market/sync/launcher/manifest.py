from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json


@dataclass(slots=True)
class ManifestFile:
    path: str
    sha256: str
    size: int
    url: str | None = None


@dataclass(slots=True)
class UpdateManifest:
    version: str
    files: list[ManifestFile]
    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "UpdateManifest":
        return cls(
            version=str(data.get("version", "0.0.0")),
            notes=str(data.get("notes", "")),
            files=[ManifestFile(**item) for item in data.get("files", [])],
        )

    @classmethod
    def load(cls, path: str | Path) -> "UpdateManifest":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "notes": self.notes,
            "files": [f.__dict__ for f in self.files],
        }

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
