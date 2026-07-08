# StankyTools Phase 4 Sprint A7

This package adds migration adapters that route Events, POIs, Bases, Announcements, Links, Ideas, Members, and Member Specializations through the new SyncManager queue.

## Install

Copy the `stanky_market/sync/` files into your project, preserving folders.

## Important

This sprint provides integration scaffolding. It does not automatically remove old direct Supabase calls from `app.py`. Migrate one feature at a time by replacing direct write calls with the adapters.

Example:

```python
from stanky_market.sync.legacy_bridge import LegacySyncBridge

bridge = LegacySyncBridge(current_guild_id)
bridge.events.set_response(event_id, member_id, "attending")
bridge.pois.delete_poi(poi_id, current_role, current_user_id, owner_user_id)
```

## Supabase

Review and run:

`docs/supabase_phase4_a7_indexes_permissions.sql`

Only run after confirming your table and column names match.
