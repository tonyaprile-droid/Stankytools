\
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class SyncStats:
    last_success: float | None = None
    last_failure: float | None = None
    upload_success_count: int = 0
    upload_failure_count: int = 0
    download_success_count: int = 0
    download_failure_count: int = 0
    realtime_event_count: int = 0
    pending_queue_count: int = 0
    last_error: str | None = None
    active_guild_id: str | None = None
    active_subscriptions: list[str] = field(default_factory=list)

    def mark_upload_success(self):
        self.upload_success_count += 1
        self.last_success = time.time()
        self.last_error = None

    def mark_upload_failure(self, error: Exception | str):
        self.upload_failure_count += 1
        self.last_failure = time.time()
        self.last_error = str(error)

    def mark_download_success(self):
        self.download_success_count += 1
        self.last_success = time.time()
        self.last_error = None

    def mark_download_failure(self, error: Exception | str):
        self.download_failure_count += 1
        self.last_failure = time.time()
        self.last_error = str(error)

    def mark_realtime_event(self):
        self.realtime_event_count += 1

    def to_dict(self) -> dict:
        return {
            "last_success": self.last_success,
            "last_failure": self.last_failure,
            "upload_success_count": self.upload_success_count,
            "upload_failure_count": self.upload_failure_count,
            "download_success_count": self.download_success_count,
            "download_failure_count": self.download_failure_count,
            "realtime_event_count": self.realtime_event_count,
            "pending_queue_count": self.pending_queue_count,
            "last_error": self.last_error,
            "active_guild_id": self.active_guild_id,
            "active_subscriptions": self.active_subscriptions,
        }
