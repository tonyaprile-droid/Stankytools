from __future__ import annotations

from typing import Any
from stanky_market.sync.sync_manager import sync_manager

MEMBER_TABLE = 'guild_members'
SPECIALIZATION_TABLE = 'member_specializations'
SPECIALIZATION_ORDER = ['Crafting', 'Gathering', 'Exploration', 'Combat', 'Sabatoge']

class MemberSyncAdapter:
    def __init__(self, guild_id: str):
        self.guild_id = guild_id

    def update_member(self, member_id: str, updates: dict[str, Any]) -> None:
        payload = dict(updates)
        payload['id'] = member_id
        payload['guild_id'] = self.guild_id
        sync_manager.queue_change(MEMBER_TABLE, 'upsert', payload)

    def set_role(self, member_id: str, role: str) -> None:
        role = (role or '').strip().lower()
        if role not in {'owner', 'admin', 'officer', 'member'}:
            raise ValueError('Invalid guild role')
        self.update_member(member_id, {'role': role})

    def set_specialization(self, member_id: str, specialization: str, value: str) -> None:
        if specialization not in SPECIALIZATION_ORDER:
            raise ValueError('Invalid specialization')
        value = (value or '').strip()[:100]
        sync_manager.queue_change(SPECIALIZATION_TABLE, 'upsert', {
            'guild_id': self.guild_id,
            'guild_member_id': member_id,
            'specialization': specialization,
            'value': value,
        })

    def set_specializations(self, member_id: str, values: dict[str, str]) -> None:
        for spec in SPECIALIZATION_ORDER:
            if spec in values:
                self.set_specialization(member_id, spec, values[spec])
