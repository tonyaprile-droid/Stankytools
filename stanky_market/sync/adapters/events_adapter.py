from __future__ import annotations

from typing import Any

from .base_adapter import AdapterResult, SyncAdapterBase


class EventsSyncAdapter(SyncAdapterBase):
    table_name = "guild_events"
    event_prefix = "event"

    def create_event(self, title: str, description: str, starts_at: str, created_by: str, **extra: Any) -> AdapterResult:
        return self.create({
            "title": title.strip(),
            "description": description.strip(),
            "starts_at": starts_at,
            "created_by": created_by,
            **extra,
        })

    def update_event(self, event_id: str, **patch: Any) -> AdapterResult:
        return self.update(event_id, patch)

    def delete_event(self, event_id: str, deleted_by: str | None = None) -> AdapterResult:
        return self.soft_delete(event_id, {"deleted_by": deleted_by} if deleted_by else None)

    def set_response(self, event_id: str, member_id: str, status: str | None) -> AdapterResult:
        normalized = (status or "").strip().lower()
        if normalized not in {"attending", "interested", ""}:
            return AdapterResult(False, error="Invalid event response")
        action = "delete" if not normalized else "upsert"
        payload = {
            "event_id": event_id,
            "member_id": member_id,
            "status": normalized,
        }
        self.sync.queue_change("guild_event_responses", action, payload)
        self.dispatcher.emit("event_response_changed", payload)
        return AdapterResult(True, payload)
