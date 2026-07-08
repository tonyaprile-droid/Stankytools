from __future__ import annotations

from typing import Any
from stanky_market.sync.sync_manager import sync_manager

EVENT_TABLE = 'guild_events'
EVENT_RESPONSE_TABLE = 'event_responses'

class EventSyncAdapter:
    def __init__(self, guild_id: str):
        self.guild_id = guild_id

    def create_event(self, event_data: dict[str, Any]) -> None:
        event_data = dict(event_data)
        event_data['guild_id'] = self.guild_id
        sync_manager.queue_change(EVENT_TABLE, 'upsert', event_data)

    def update_event(self, event_id: str, updates: dict[str, Any]) -> None:
        payload = dict(updates)
        payload['id'] = event_id
        payload['guild_id'] = self.guild_id
        sync_manager.queue_change(EVENT_TABLE, 'upsert', payload)

    def delete_event(self, event_id: str) -> None:
        sync_manager.queue_change(EVENT_TABLE, 'soft_delete', {'id': event_id, 'guild_id': self.guild_id})

    def set_response(self, event_id: str, member_id: str, status: str) -> None:
        status = (status or '').strip().lower()
        if status not in {'attending', 'interested'}:
            raise ValueError('status must be attending or interested')
        sync_manager.queue_change(EVENT_RESPONSE_TABLE, 'upsert', {
            'event_id': event_id,
            'guild_member_id': member_id,
            'guild_id': self.guild_id,
            'status': status,
        })

    def remove_response(self, event_id: str, member_id: str) -> None:
        sync_manager.queue_change(EVENT_RESPONSE_TABLE, 'delete', {
            'event_id': event_id,
            'guild_member_id': member_id,
            'guild_id': self.guild_id,
        })
