from __future__ import annotations

from typing import Any
from stanky_market.sync.sync_manager import sync_manager
from .poi_adapter import can_delete_intel

BASE_TABLE = 'guild_bases'

class BaseSyncAdapter:
    def __init__(self, guild_id: str):
        self.guild_id = guild_id

    def create_base(self, base_data: dict[str, Any]) -> None:
        payload = dict(base_data)
        payload['guild_id'] = self.guild_id
        sync_manager.queue_change(BASE_TABLE, 'upsert', payload)

    def update_base(self, base_id: str, updates: dict[str, Any]) -> None:
        payload = dict(updates)
        payload['id'] = base_id
        payload['guild_id'] = self.guild_id
        sync_manager.queue_change(BASE_TABLE, 'upsert', payload)

    def delete_base(self, base_id: str, current_role: str | None = None, current_user_id: str | None = None, owner_user_id: str | None = None) -> None:
        if current_user_id and owner_user_id and not can_delete_intel(current_role, current_user_id, owner_user_id):
            raise PermissionError('Members can only delete their own Bases.')
        sync_manager.queue_change(BASE_TABLE, 'soft_delete', {'id': base_id, 'guild_id': self.guild_id})
