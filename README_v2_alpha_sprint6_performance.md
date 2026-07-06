# StankyTools v2 Alpha Sprint 6 — Performance + Hagga Menu Cleanup

Changes included:

- Optimized app responsiveness by slowing automatic Supabase sync from every 5 seconds to every 60 seconds.
- Added a 45-second throttle guard so network sync cannot stack up and repeatedly block the UI.
- Manual actions still sync immediately after POI/base edits, guild changes, and saves.
- Added cached catalog thumbnails so switching/searching catalog no longer repeatedly decodes every item image.
- Disabled table repainting during catalog/market refreshes to reduce UI lag.
- Hagga Basin right-click menu now only shows:
  - Edit Base
  - Remove Base
- Preserved Sprint 5 changes: guild news, useful links, guild page, member dialog, custom guild code, Deep Desert map, catalog image column, settings cleanup, and guild cache fixes.

No new Supabase SQL is required for this sprint.
