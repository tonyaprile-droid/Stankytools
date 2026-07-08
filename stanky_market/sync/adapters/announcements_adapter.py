from __future__ import annotations

from typing import Any

from .base_adapter import AdapterResult, SyncAdapterBase


class AnnouncementsSyncAdapter(SyncAdapterBase):
    table_name = "guild_announcements"
    event_prefix = "announcement"

    def create_announcement(self, title: str, body: str, created_by: str, **extra: Any) -> AdapterResult:
        title = title.strip()
        body = body.strip()
        if not title or not body:
            return AdapterResult(False, error="Title and announcement body are required")
        return self.create({
            "title": title,
            "body": body,
            "created_by": created_by,
            **extra,
        })

    def update_announcement(self, announcement_id: str, **patch: Any) -> AdapterResult:
        return self.update(announcement_id, patch)

    def delete_announcement(self, announcement_id: str, deleted_by: str | None = None) -> AdapterResult:
        return self.soft_delete(announcement_id, {"deleted_by": deleted_by} if deleted_by else None)
