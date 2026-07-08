from __future__ import annotations

from typing import Any
from stanky_market.sync.sync_manager import sync_manager

IDEAS_TABLE = 'guild_ideas'
VALID_STATUSES = {'New', 'Reviewing', 'Planned', 'In Progress', 'Completed', 'Declined'}

class IdeasSyncAdapter:
    def __init__(self, guild_id: str):
        self.guild_id = guild_id

    def submit_idea(self, title: str, description: str, submitted_by: str | None = None) -> None:
        title = (title or '').strip()
        description = (description or '').strip()
        if not title or not description:
            raise ValueError('Idea title and description are required.')
        payload = {'guild_id': self.guild_id, 'title': title, 'description': description, 'status': 'New'}
        if submitted_by:
            payload['submitted_by'] = submitted_by
        sync_manager.queue_change(IDEAS_TABLE, 'upsert', payload)

    def update_status(self, idea_id: str, status: str) -> None:
        if status not in VALID_STATUSES:
            raise ValueError(f'Invalid idea status: {status}')
        sync_manager.queue_change(IDEAS_TABLE, 'upsert', {'id': idea_id, 'guild_id': self.guild_id, 'status': status})

    def update_idea(self, idea_id: str, title: str, description: str, status: str | None = None) -> None:
        payload = {'id': idea_id, 'guild_id': self.guild_id, 'title': title.strip(), 'description': description.strip()}
        if status:
            if status not in VALID_STATUSES:
                raise ValueError(f'Invalid idea status: {status}')
            payload['status'] = status
        sync_manager.queue_change(IDEAS_TABLE, 'upsert', payload)

    def delete_idea(self, idea_id: str) -> None:
        sync_manager.queue_change(IDEAS_TABLE, 'soft_delete', {'id': idea_id, 'guild_id': self.guild_id})
