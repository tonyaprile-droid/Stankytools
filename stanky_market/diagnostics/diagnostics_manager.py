\
from __future__ import annotations

from pathlib import Path
from typing import Any

from .connection_monitor import ConnectionMonitor
from .debug_console import DebugConsole
from .health_monitor import HealthMonitor
from .performance import PerformanceTracker
from .queue_monitor import QueueMonitor
from .sync_stats import SyncStats
from .telemetry import TelemetryLogger


class DiagnosticsManager:
    _instance = None

    @classmethod
    def instance(cls) -> "DiagnosticsManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, appdata_dir: Path | None = None):
        self.appdata_dir = appdata_dir or Path.home() / "AppData" / "Roaming" / "StankyTools"
        self.telemetry = TelemetryLogger(self.appdata_dir / "logs")
        self.performance = PerformanceTracker()
        self.sync_stats = SyncStats()
        self.queue_monitor = QueueMonitor()
        self.connection_monitor = ConnectionMonitor()
        self.health_monitor = HealthMonitor(self.appdata_dir)
        self.console = DebugConsole()

    def log(self, message: str, **payload: Any) -> None:
        self.console.write(message)
        self.telemetry.log("diagnostic_log", message=message, **payload)

    def record_error(self, source: str, error: Exception | str) -> None:
        msg = f"[{source}] {error}"
        self.console.write(msg)
        self.telemetry.log("error", source=source, error=str(error))

    def snapshot(self) -> dict:
        return {
            "health": self.health_monitor.snapshot(),
            "connection": self.connection_monitor.to_dict(),
            "queue": self.queue_monitor.to_dict(),
            "sync": self.sync_stats.to_dict(),
            "performance": self.performance.summary(),
            "recent_logs": self.console.lines[-50:],
        }

    def save_snapshot(self, path: str | Path | None = None) -> Path:
        import json
        import time

        target = Path(path) if path else self.appdata_dir / "logs" / f"diagnostics_{int(time.time())}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.snapshot(), indent=2, default=str), encoding="utf-8")
        return target
