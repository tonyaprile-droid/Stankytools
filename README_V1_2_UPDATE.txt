StankyTools v1.2 Tactical Guild Update

Included changes:
- Friendly/Enemy/Defeated base tactical colors.
- Base status syncs to Supabase using guild_bases.status.
- Right-click base list to set Friendly, Enemy, or Defeated.
- Guild POI right-click menu now contains Active, Defeated, Edit Note, and Delete POI.
- Deep Desert POI buttons were cleaned up; map refresh is in Settings > Maintenance.
- Larger Guild POI note dialogs are preserved.
- Selected POIs and selected bases are highlighted on the map while unselected markers stay clean.
- Settings keeps the no-save-button Join/Create/Leave workflow.
- Settings shows guild members after joining.
- Owner/officers can remove guild members.
- Owner/officers can upload or delete the current guild logo.
- Dashboard uses the cached guild logo when available.
- Existing banner/icon assets are preserved.

Supabase:
Run docs/supabase_v1_2_guild_tactical_update.sql in Supabase SQL Editor before using guild logo/base status features.
