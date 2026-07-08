StankyTools v1.4 Complete Update

Included:
- Background-thread catalog importer so the UI no longer freezes.
- Catalog import still uses a polite delay between web requests.
- Guild creation now asks for Guild Name only when creating a guild.
- Guild join only requires Display Name + Guild Code.
- Duplicate guild names are blocked.
- First member of a new guild is the owner.
- Default guild logo placeholder is shown when no logo is uploaded.
- Owners and officers can upload/delete the guild logo.
- Settings includes current guild members and owner/officer member removal.
- Base status colors: Friendly green, Enemy red, Defeated grey.
- POI right-click menu includes Active/Defeated/Edit/Delete.
- POI edit/delete buttons were moved into the right-click menu.
- Deep Desert map update/refresh lives in Settings maintenance.
- Selected POIs and selected bases get eye-catching map highlights.
- Previous settings cleanup is preserved: no Save button, no Supabase text, Join/Create auto-save, Leave Guild after joining.

Before using guild logo/base status features, run SUPABASE_UPDATE_v1_4.sql in Supabase SQL Editor.
