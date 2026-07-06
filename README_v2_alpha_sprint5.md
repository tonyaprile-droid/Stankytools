# StankyTools v2 Alpha Sprint 5

Changes included:

- Fixed ugly table/item selection focus outline.
- Dates now display as `7-6-2026` style.
- Added Delete News for guild news.
- Double-click guild news to read full notes/body.
- Dashboard now shows Useful Links instead of Activity Feed.
- Guild page now includes Activity Feed.
- Fixed join/save flow so the app does not revert to the bundled Griffin Wing settings.
- Bundled local SQLite settings/cache were cleared so new installs start clean.
- Added `SUPABASE_DELETE_ALL_GUILDS.sql` to wipe all remote guilds/news/links/activity/POIs/bases/members if you want a fresh Supabase database.

If you want to delete all existing remote guilds, open `SUPABASE_DELETE_ALL_GUILDS.sql`, copy the SQL inside it, paste it into Supabase SQL Editor, and run it.
