from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json


@dataclass(slots=True)
class ManifestFile:
    path: str
    sha256: str
    size: int
    url: str | None = None
    channel: str = "stable"
    executable: bool = False


@dataclass(slots=True)
class ManifestV2:
    version: str
    channel: str = "stable"
    notes: str = ""
    files: list[ManifestFile] = field(default_factory=list)
    min_launcher_version: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "ManifestV2":
        files = [ManifestFile(**item) for item in data.get("files", [])]
        return cls(
            version=str(data.get("version", "0.0.0")),
            channel=str(data.get("channel", "stable")),
            notes=str(data.get("notes", "")),
            files=files,
            min_launcher_version=data.get("min_launcher_version"),
        )

    @classmethod
    def load(cls, path: str | Path) -> "ManifestV2":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "channel": self.channel,
            "notes": self.notes,
            "min_launcher_version": self.min_launcher_version,
            "files": [f.__dict__ for f in self.files],
        }

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
