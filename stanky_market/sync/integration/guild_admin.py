from __future__ import annotations

from typing import Any
from uuid import uuid4

from .base import BaseIntegration


class GuildAdminIntegration(BaseIntegration):
    feature_name = "guild_admin"
    ANNOUNCEMENT_TABLE = "guild_announcements"
    LINK_TABLE = "guild_links"
    IDEA_TABLE = "guild_ideas"

    def create_announcement(self, payload: dict[str, Any]) -> str:
        item_id = str(payload.get("id") or uuid4())
        payload = {**payload, "id": item_id}
        self.queue(self.ANNOUNCEMENT_TABLE, "upsert", payload)
        self.emit("announcement_local_upsert", payload)
        return item_id

    def update_announcement(self, item_id: str, updates: dict[str, Any]) -> None:
        payload = {**updates, "id": item_id}
        self.queue(self.ANNOUNCEMENT_TABLE, "upsert", payload)
        self.emit("announcement_local_upsert", payload)

    def delete_announcement(self, item_id: str) -> None:
        self.queue(self.ANNOUNCEMENT_TABLE, "soft_delete", {"id": item_id})
        self.emit("announcement_local_delete", item_id)

    def create_link(self, payload: dict[str, Any]) -> str:
        item_id = str(payload.get("id") or uuid4())
        payload = {**payload, "id": item_id}
        self.queue(self.LINK_TABLE, "upsert", payload)
        self.emit("link_local_upsert", payload)
        return item_id

    def update_link(self, item_id: str, updates: dict[str, Any]) -> None:
        payload = {**updates, "id": item_id}
        self.queue(self.LINK_TABLE, "upsert", payload)
        self.emit("link_local_upsert", payload)

    def delete_link(self, item_id: str) -> None:
        self.queue(self.LINK_TABLE, "soft_delete", {"id": item_id})
        self.emit("link_local_delete", item_id)

    def submit_idea(self, title: str, description: str, submitted_by: str | None = None) -> str:
        item_id = str(uuid4())
        payload = {
            "id": item_id,
            "title": title.strip(),
            "description": description.strip(),
            "status": "New",
        }
        if submitted_by:
            payload["submitted_by"] = submitted_by
        self.queue(self.IDEA_TABLE, "upsert", payload)
        self.emit("idea_local_upsert", payload)
        return item_id

    def update_idea_status(self, idea_id: str, status: str) -> None:
        payload = {"id": idea_id, "status": status}
        self.queue(self.IDEA_TABLE, "upsert", payload)
        self.emit("idea_local_upsert", payload)

    def delete_idea(self, idea_id: str) -> None:
        self.queue(self.IDEA_TABLE, "soft_delete", {"id": idea_id})
        self.emit("idea_local_delete", idea_id)
