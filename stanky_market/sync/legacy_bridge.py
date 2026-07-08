from __future__ import annotations

from typing import Any

from stanky_market.sync.integration import SyncIntegrationRegistry


class LegacySyncBridge:
    """Drop-in bridge for gradually replacing old direct Supabase calls."""

    def __init__(self, guild_id: str | None = None):
        self.registry = SyncIntegrationRegistry(guild_id)

    def set_guild(self, guild_id: str | None) -> None:
        self.registry.set_guild(guild_id)

    def save_event(self, payload: dict[str, Any]) -> str:
        return self.registry.events.create_event(payload)

    def save_poi(self, payload: dict[str, Any]) -> str:
        return self.registry.deep_desert.create_poi(payload)

    def save_base(self, payload: dict[str, Any]) -> str:
        return self.registry.deep_desert.create_base(payload)

    def submit_idea(self, title: str, description: str, submitted_by: str | None = None) -> str:
        return self.registry.guild_admin.submit_idea(title, description, submitted_by)
