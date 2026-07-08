from __future__ import annotations

from enum import Enum


class SyncState(str, Enum):
    IDLE = "idle"
    SYNCING = "syncing"
    SYNCED = "synced"
    PENDING = "pending"
    OFFLINE = "offline"
    ERROR = "error"
