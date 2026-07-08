from __future__ import annotations

from typing import Any, Callable

try:
    from stanky_market.sync.dispatcher import dispatcher
except Exception:
    dispatcher = None

try:
    from stanky_market.sync.sync_manager import sync_manager
except Exception:
    sync_manager = None


class BaseIntegration:
    """Base class for feature integrations that route writes through SyncManager."""

    feature_name = "base"

    def __init__(self, guild_id: str | None = None):
        self.guild_id = guild_id
        self._callbacks: list[tuple[str, Callable[..., Any]]] = []

    def set_guild(self, guild_id: str | None) -> None:
        self.guild_id = guild_id

    def queue(self, table: str, action: str, payload: dict[str, Any]) -> None:
        if self.guild_id and "guild_id" not in payload:
            payload["guild_id"] = self.guild_id
        if sync_manager is None:
            raise RuntimeError("SyncManager is not available")
        sync_manager.queue_change(table, action, payload)

    def emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        if dispatcher is not None:
            dispatcher.emit(event, *args, **kwargs)

    def subscribe(self, event: str, callback: Callable[..., Any]) -> None:
        if dispatcher is not None:
            dispatcher.subscribe(event, callback)
            self._callbacks.append((event, callback))

    def close(self) -> None:
        if dispatcher is None:
            return
        for event, callback in self._callbacks:
            dispatcher.unsubscribe(event, callback)
        self._callbacks.clear()
