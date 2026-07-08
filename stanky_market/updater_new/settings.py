from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json


@dataclass(slots=True)
class UpdateSettings:
    channel: str = "stable"
    auto_check: bool = True
    auto_download: bool = True
    auto_restart: bool = False
    bandwidth_limit_kbps: int | None = None

    @classmethod
    def load(cls, path: str | Path) -> "UpdateSettings":
        p = Path(path)
        if not p.exists():
            return cls()
        return cls(**json.loads(p.read_text(encoding="utf-8")))

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
