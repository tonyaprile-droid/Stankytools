from __future__ import annotations

from typing import Any

from .base import BaseIntegration


class MembersIntegration(BaseIntegration):
    feature_name = "members"
    MEMBER_TABLE = "guild_members"
    SPECIALIZATION_TABLE = "member_specializations"

    def update_member_role(self, member_id: str, role: str) -> None:
        payload = {"id": member_id, "role": role}
        self.queue(self.MEMBER_TABLE, "upsert", payload)
        self.emit("member_local_upsert", payload)

    def remove_member(self, member_id: str) -> None:
        self.queue(self.MEMBER_TABLE, "soft_delete", {"id": member_id})
        self.emit("member_local_delete", member_id)

    def update_specializations(self, member_id: str, specializations: dict[str, Any]) -> None:
        payload = {"member_id": member_id, **specializations}
        self.queue(self.SPECIALIZATION_TABLE, "upsert", payload)
        self.emit("specialization_local_upsert", payload)
