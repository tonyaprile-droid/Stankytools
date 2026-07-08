from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional


@dataclass
class GuildSubscriptionState:
    guild_id: Optional[str] = None
    active_tables: List[str] = field(default_factory=list)
    subscribed_at: Optional[str] = None


class GuildSubscriptionManager:
    """Guild-scoped subscription coordinator.

    This intentionally keeps the implementation provider-neutral. Your existing
    Supabase/realtime code can be passed in through `subscribe_fn` and
    `unsubscribe_fn` without forcing a full app rewrite.
    """

    DEFAULT_TABLES = (
        "guild_events",
        "guild_event_responses",
        "guild_announcements",
        "guild_links",
        "guild_ideas",
        "guild_pois",
        "guild_bases",
        "guild_members",
        "member_specializations",
    )

    def __init__(self) -> None:
        self.state = GuildSubscriptionState()
        self._handles: Dict[str, object] = {}

    def subscribe(
        self,
        guild_id: str,
        subscribe_fn: Optional[Callable[[str, str], object]] = None,
        tables: Optional[List[str]] = None,
    ) -> GuildSubscriptionState:
        self.unsubscribe()
        selected_tables = list(tables or self.DEFAULT_TABLES)
        self.state = GuildSubscriptionState(
            guild_id=guild_id,
            active_tables=selected_tables,
            subscribed_at=datetime.now(timezone.utc).isoformat(),
        )
        if subscribe_fn:
            for table in selected_tables:
                self._handles[table] = subscribe_fn(table, guild_id)
        return self.state

    def unsubscribe(self, unsubscribe_fn: Optional[Callable[[object], None]] = None) -> None:
        if unsubscribe_fn:
            for handle in list(self._handles.values()):
                try:
                    unsubscribe_fn(handle)
                except Exception:
                    pass
        self._handles.clear()
        self.state = GuildSubscriptionState()

    @property
    def current_guild_id(self) -> Optional[str]:
        return self.state.guild_id
