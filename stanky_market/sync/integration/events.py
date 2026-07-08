from __future__ import annotations

from typing import Any
from uuid import uuid4

from .base import BaseIntegration


class EventsIntegration(BaseIntegration):
    feature_name = "events"
    EVENT_TABLE = "guild_events"
    RESPONSE_TABLE = "event_responses"

    def create_event(self, payload: dict[str, Any]) -> str:
        event_id = str(payload.get("id") or uuid4())
        payload = {**payload, "id": event_id}
        self.queue(self.EVENT_TABLE, "upsert", payload)
        self.emit("event_local_upsert", payload)
        return event_id

    def update_event(self, event_id: str, updates: dict[str, Any]) -> None:
        payload = {**updates, "id": event_id}
        self.queue(self.EVENT_TABLE, "upsert", payload)
        self.emit("event_local_upsert", payload)

    def delete_event(self, event_id: str) -> None:
        payload = {"id": event_id}
        self.queue(self.EVENT_TABLE, "soft_delete", payload)
        self.emit("event_local_delete", event_id)

    def set_response(self, event_id: str, member_id: str, status: str) -> None:
        status = (status or "").strip().lower()
        if status not in {"attending", "interested"}:
            self.remove_response(event_id, member_id)
            return
        payload = {
            "event_id": event_id,
            "guild_member_id": member_id,
            "status": status,
        }
        self.queue(self.RESPONSE_TABLE, "upsert", payload)
        self.emit("event_response_local_upsert", payload)

    def remove_response(self, event_id: str, member_id: str) -> None:
        payload = {"event_id": event_id, "guild_member_id": member_id}
        self.queue(self.RESPONSE_TABLE, "delete", payload)
        self.emit("event_response_local_delete", payload)
