\
from __future__ import annotations

import json
import platform
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


def _default_log_dir() -> Path:
    return Path.home() / "AppData" / "Roaming" / "StankyTools" / "logs"


@dataclass
class TelemetryEvent:
    name: str
    timestamp: float
    payload: dict[str, Any]


class TelemetryLogger:
    """
    Local-only telemetry logger.

    This does not upload anything. It writes JSONL events under:
    %APPDATA%/StankyTools/logs/telemetry.jsonl
    """

    def __init__(self, log_dir: Path | None = None, enabled: bool = True):
        self.enabled = enabled
        self.log_dir = log_dir or _default_log_dir()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.log_dir / "telemetry.jsonl"

    def log(self, name: str, **payload: Any) -> None:
        if not self.enabled:
            return

        event = TelemetryEvent(
            name=name,
            timestamp=time.time(),
            payload={
                **payload,
                "platform": platform.platform(),
                "python": platform.python_version(),
            },
        )

        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event), default=str) + "\n")

    def tail(self, limit: int = 100) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []

        lines = self.path.read_text(encoding="utf-8", errors="ignore").splitlines()
        out: list[dict[str, Any]] = []

        for line in lines[-limit:]:
            try:
                out.append(json.loads(line))
            except Exception:
                continue

        return out
