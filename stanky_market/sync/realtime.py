from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Subscription:
    table: str
    guild_id: str
    callback: Callable[[dict], None]
    active: bool = True


class RealtimeManager:
    def __init__(self) -> None:
        self.guild_id: str | None = None
        self._subscriptions: dict[str, Subscription] = {}

    def subscribe_guild(self, guild_id: str, tables: list[str], callback: Callable[[dict], None]) -> None:
        self.unsubscribe_all()
        self.guild_id = guild_id
        for table in tables:
            self._subscriptions[table] = Subscription(table=table, guild_id=guild_id, callback=callback)

    def unsubscribe_all(self) -> None:
        for sub in self._subscriptions.values():
            sub.active = False
        self._subscriptions.clear()
        self.guild_id = None

    def handle_payload(self, table: str, payload: dict) -> None:
        sub = self._subscriptions.get(table)
        if sub and sub.active:
            sub.callback(payload)

    @property
    def active_tables(self) -> list[str]:
        return list(self._subscriptions.keys())
