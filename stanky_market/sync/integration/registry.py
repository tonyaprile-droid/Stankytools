from __future__ import annotations

from .events import EventsIntegration
from .deep_desert import DeepDesertIntegration
from .guild_admin import GuildAdminIntegration
from .dashboard import DashboardIntegration
from .members import MembersIntegration


class SyncIntegrationRegistry:
    """Creates and updates all feature integrations for the active guild."""

    def __init__(self, guild_id: str | None = None):
        self.guild_id = guild_id
        self.events = EventsIntegration(guild_id)
        self.deep_desert = DeepDesertIntegration(guild_id)
        self.guild_admin = GuildAdminIntegration(guild_id)
        self.dashboard = DashboardIntegration(guild_id)
        self.members = MembersIntegration(guild_id)

    def set_guild(self, guild_id: str | None) -> None:
        self.guild_id = guild_id
        for integration in self.all():
            integration.set_guild(guild_id)

    def all(self):
        return [
            self.events,
            self.deep_desert,
            self.guild_admin,
            self.dashboard,
            self.members,
        ]

    def close(self) -> None:
        for integration in self.all():
            integration.close()
