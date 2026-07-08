from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone


@dataclass
class SyncDiagnostics:
    guild_id: str | None = None
    status: str = "synced"
    pending_queue: int = 0
    last_sync_at: str | None = None
    last_error: str | None = None
    realtime_tables: list[str] | None = None

    def mark_sync(self) -> None:
        self.last_sync_at = datetime.now(timezone.utc).isoformat()
        self.last_error = None

    def mark_error(self, message: str) -> None:
        self.last_error = message

    def to_dict(self) -> dict:
        return asdict(self)
