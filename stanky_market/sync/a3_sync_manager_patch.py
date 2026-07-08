"""Drop-in helper to extend the Sprint A1/A2 SyncManager.

Usage in your app startup after creating/importing sync_manager:

    from stanky_market.sync.a3_sync_manager_patch import install_a3_features
    install_a3_features(sync_manager)

Then use:

    sync_manager.change_guild(guild_id)
    sync_manager.queue_offline_change("guild_pois", "upsert", payload)
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from .guild_subscription import GuildSubscriptionManager
from .persistent_queue import PersistentQueue
from .retry_scheduler import RetryScheduler


def default_appdata_root() -> Path:
    import os
    return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "StankyTools"


def install_a3_features(sync_manager, appdata_root: Optional[Path] = None) -> None:
    root = Path(appdata_root or default_appdata_root())
    queue_path = root / "queue" / "offline_queue.json"

    sync_manager.guild_subscriptions = GuildSubscriptionManager()
    sync_manager.offline_queue = PersistentQueue(queue_path)
    sync_manager.retry_scheduler = RetryScheduler()

    def change_guild(
        guild_id: Optional[str],
        subscribe_fn: Optional[Callable[[str, str], object]] = None,
        unsubscribe_fn: Optional[Callable[[object], None]] = None,
    ):
        sync_manager.guild_subscriptions.unsubscribe(unsubscribe_fn)
        if hasattr(sync_manager, "clear_guild_cache"):
            try:
                sync_manager.clear_guild_cache()
            except Exception:
                pass
        if guild_id:
            return sync_manager.guild_subscriptions.subscribe(guild_id, subscribe_fn)
        return None

    def queue_offline_change(table: str, action: str, payload: dict):
        item = sync_manager.offline_queue.add(table, action, payload)
        if hasattr(sync_manager, "pendingChanged"):
            sync_manager.pendingChanged.emit(sync_manager.offline_queue.pending)
        return item

    def process_offline_queue(upload_fn: Callable[[str, str, dict], None], max_items: int = 25) -> int:
        processed = 0
        while processed < max_items:
            item = sync_manager.offline_queue.peek()
            if not item:
                break
            if not sync_manager.retry_scheduler.can_run(item.id):
                break
            try:
                upload_fn(item.table, item.action, item.payload)
                sync_manager.offline_queue.remove(item.id)
                sync_manager.retry_scheduler.record_success(item.id)
                processed += 1
            except Exception as exc:
                sync_manager.offline_queue.mark_failed(item.id, str(exc))
                sync_manager.retry_scheduler.record_failure(item.id)
                break
        if hasattr(sync_manager, "pendingChanged"):
            sync_manager.pendingChanged.emit(sync_manager.offline_queue.pending)
        return processed

    sync_manager.change_guild = change_guild
    sync_manager.queue_offline_change = queue_offline_change
    sync_manager.process_offline_queue = process_offline_queue
