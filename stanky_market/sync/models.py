from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class SyncObject:
    id: str = field(default_factory=lambda: str(uuid4()))
    guild_id: str | None = None
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    deleted_at: str | None = None
    sync_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "guild_id": self.guild_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "deleted_at": self.deleted_at,
            "sync_version": self.sync_version,
        }
