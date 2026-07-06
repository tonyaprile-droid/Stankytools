StankyTools v1.5 Tactical Cleanup

Run SUPABASE_UPDATE_v1_5.sql in Supabase SQL Editor if you have not already applied the v1.4 schema.

Included:
- Deep Desert POIs now use tactical colors:
  - Enemy Base = red
  - Friendly Base = green
  - Defeated = grey
- Right-click POI menu can set Friendly / Enemy / Defeated, plus Edit/Delete.
- Last member leaving a guild deletes the guild, POIs, bases, members, and logo data.
- If an owner leaves while members remain, the oldest officer is promoted to owner. If no officers exist, the oldest member is promoted.
- Guild names become reusable after the final member leaves and the guild is deleted.
- Preserves all v1.4 features: background catalog import, guild logo placeholder/upload/delete, member management, base status colors, settings cleanup, map refresh in Settings, and join/create/leave workflow.
