from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
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
    files: list[ManifestFile] = field(default_factory=list)
    release_notes: str = ""
    required_launcher_version: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UpdateManifest":
        return cls(
            version=str(data.get("version", "")).strip(),
            files=[ManifestFile(**item) for item in data.get("files", [])],
            release_notes=str(data.get("release_notes", "")),
            required_launcher_version=data.get("required_launcher_version"),
        )

    @classmethod
    def from_json(cls, text: str) -> "UpdateManifest":
        return cls.from_dict(json.loads(text))

    @classmethod
    def load(cls, path: str | Path) -> "UpdateManifest":
        return cls.from_json(Path(path).read_text(encoding="utf-8"))

    def save(self, path: str | Path) -> None:
        data = {
            "version": self.version,
            "release_notes": self.release_notes,
            "required_launcher_version": self.required_launcher_version,
            "files": [file.__dict__ for file in self.files],
        }
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")
