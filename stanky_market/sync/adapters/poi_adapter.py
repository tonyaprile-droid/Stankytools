from __future__ import annotations

from typing import Any
from stanky_market.sync.sync_manager import sync_manager

POI_TABLE = 'guild_pois'

def can_delete_intel(current_role: str | None, current_user_id: str, owner_user_id: str) -> bool:
    role = (current_role or '').strip().lower()
    return role in {'owner', 'admin', 'officer'} or str(current_user_id) == str(owner_user_id)

class POISyncAdapter:
    def __init__(self, guild_id: str):
        self.guild_id = guild_id

    def create_poi(self, poi_data: dict[str, Any]) -> None:
        payload = dict(poi_data)
        payload['guild_id'] = self.guild_id
        sync_manager.queue_change(POI_TABLE, 'upsert', payload)

    def update_poi(self, poi_id: str, updates: dict[str, Any]) -> None:
        payload = dict(updates)
        payload['id'] = poi_id
        payload['guild_id'] = self.guild_id
        sync_manager.queue_change(POI_TABLE, 'upsert', payload)

    def delete_poi(self, poi_id: str, current_role: str | None = None, current_user_id: str | None = None, owner_user_id: str | None = None) -> None:
        if current_user_id and owner_user_id and not can_delete_intel(current_role, current_user_id, owner_user_id):
            raise PermissionError('Members can only delete their own POIs.')
        sync_manager.queue_change(POI_TABLE, 'soft_delete', {'id': poi_id, 'guild_id': self.guild_id})
