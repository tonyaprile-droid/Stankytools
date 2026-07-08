from __future__ import annotations

from typing import Any
from stanky_market.sync.sync_manager import sync_manager

ANNOUNCEMENT_TABLE = 'guild_announcements'
LINK_TABLE = 'guild_links'

class AnnouncementSyncAdapter:
    def __init__(self, guild_id: str):
        self.guild_id = guild_id

    def create_announcement(self, data: dict[str, Any]) -> None:
        payload = dict(data)
        payload['guild_id'] = self.guild_id
        sync_manager.queue_change(ANNOUNCEMENT_TABLE, 'upsert', payload)

    def update_announcement(self, announcement_id: str, updates: dict[str, Any]) -> None:
        payload = dict(updates)
        payload['id'] = announcement_id
        payload['guild_id'] = self.guild_id
        sync_manager.queue_change(ANNOUNCEMENT_TABLE, 'upsert', payload)

    def delete_announcement(self, announcement_id: str) -> None:
        sync_manager.queue_change(ANNOUNCEMENT_TABLE, 'soft_delete', {'id': announcement_id, 'guild_id': self.guild_id})

    def create_link(self, data: dict[str, Any]) -> None:
        payload = dict(data)
        payload['guild_id'] = self.guild_id
        sync_manager.queue_change(LINK_TABLE, 'upsert', payload)

    def update_link(self, link_id: str, updates: dict[str, Any]) -> None:
        payload = dict(updates)
        payload['id'] = link_id
        payload['guild_id'] = self.guild_id
        sync_manager.queue_change(LINK_TABLE, 'upsert', payload)

    def delete_link(self, link_id: str) -> None:
        sync_manager.queue_change(LINK_TABLE, 'soft_delete', {'id': link_id, 'guild_id': self.guild_id})
