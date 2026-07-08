from __future__ import annotations

from typing import Any
from uuid import uuid4

from .base import BaseIntegration


class DeepDesertIntegration(BaseIntegration):
    feature_name = "deep_desert"
    POI_TABLE = "guild_pois"
    BASE_TABLE = "guild_bases"

    def create_poi(self, payload: dict[str, Any]) -> str:
        poi_id = str(payload.get("id") or uuid4())
        payload = {**payload, "id": poi_id}
        self.queue(self.POI_TABLE, "upsert", payload)
        self.emit("poi_local_upsert", payload)
        return poi_id

    def update_poi(self, poi_id: str, updates: dict[str, Any]) -> None:
        payload = {**updates, "id": poi_id}
        self.queue(self.POI_TABLE, "upsert", payload)
        self.emit("poi_local_upsert", payload)

    def delete_poi(self, poi_id: str) -> None:
        self.queue(self.POI_TABLE, "soft_delete", {"id": poi_id})
        self.emit("poi_local_delete", poi_id)

    def create_base(self, payload: dict[str, Any]) -> str:
        base_id = str(payload.get("id") or uuid4())
        payload = {**payload, "id": base_id}
        self.queue(self.BASE_TABLE, "upsert", payload)
        self.emit("base_local_upsert", payload)
        return base_id

    def update_base(self, base_id: str, updates: dict[str, Any]) -> None:
        payload = {**updates, "id": base_id}
        self.queue(self.BASE_TABLE, "upsert", payload)
        self.emit("base_local_upsert", payload)

    def delete_base(self, base_id: str) -> None:
        self.queue(self.BASE_TABLE, "soft_delete", {"id": base_id})
        self.emit("base_local_delete", base_id)

    @staticmethod
    def can_delete(role: str | None, current_user_id: str | None, owner_user_id: str | None) -> bool:
        role = (role or "").strip().lower()
        if role in {"owner", "admin", "officer"}:
            return True
        return bool(current_user_id and owner_user_id and str(current_user_id) == str(owner_user_id))
