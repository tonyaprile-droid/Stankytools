# v0.3.5 Event Sync Hotfix

Fixes guild event syncing after the Guild Admin layout/event response changes.

Run this Supabase SQL once if events or attendance responses are not syncing:

`docs/supabase_v3_5_event_sync_hotfix.sql`

Changes:
- Event pull no longer fails if event response table has a schema issue.
- Creating a single event no longer clears the full local event cache.
- Event response changes queue an immediate event sync.
- Dashboard event right-click menu now says Not Attending / Remove Response.
