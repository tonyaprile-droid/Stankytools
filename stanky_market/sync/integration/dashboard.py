from __future__ import annotations

from .base import BaseIntegration


class DashboardIntegration(BaseIntegration):
    feature_name = "dashboard"

    def connect_auto_refresh(self, refresh_callback):
        for event_name in (
            "guild_changed",
            "event_local_upsert",
            "event_local_delete",
            "event_response_local_upsert",
            "event_response_local_delete",
            "poi_local_upsert",
            "poi_local_delete",
            "base_local_upsert",
            "base_local_delete",
            "announcement_local_upsert",
            "announcement_local_delete",
            "member_local_upsert",
            "member_local_delete",
        ):
            self.subscribe(event_name, lambda *_, **__: refresh_callback())
