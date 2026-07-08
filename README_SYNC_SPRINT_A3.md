# StankyTools Phase 4 Sprint A3

Adds guild-scoped subscription and persistent offline queue infrastructure.

## Files

Copy these into your project:

```text
stanky_market/sync/guild_subscription.py
stanky_market/sync/persistent_queue.py
stanky_market/sync/retry_scheduler.py
stanky_market/sync/a3_sync_manager_patch.py
```

## Startup Integration

In app startup after importing/creating your SyncManager:

```python
from stanky_market.sync import sync_manager
from stanky_market.sync.a3_sync_manager_patch import install_a3_features

install_a3_features(sync_manager)
```

## Guild Switch

```python
sync_manager.change_guild(current_guild_id)
```

If your realtime system returns handles:

```python
sync_manager.change_guild(
    guild_id,
    subscribe_fn=lambda table, guild_id: supabase_subscribe(table, guild_id),
    unsubscribe_fn=lambda handle: handle.unsubscribe(),
)
```

## Queue Offline Changes

```python
sync_manager.queue_offline_change("guild_pois", "upsert", payload)
```

## Process Queue

```python
def upload_fn(table, action, payload):
    # call your existing Supabase upsert/delete here
    ...

sync_manager.process_offline_queue(upload_fn)
```

This is intentionally adapter-based so you can migrate Events, Ideas, POIs, and Bases one at a time.
