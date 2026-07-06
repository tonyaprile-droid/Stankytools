StankyTools v1.6 Guild Required + Cache Cleanup

Included changes:
- You must be joined to a guild before placing POIs or Hagga Basin bases.
- You must be joined to edit/delete/status-change guild POIs and bases.
- Leaving a guild clears local cached guild POIs and bases so ghost bases do not remain.
- Switching guilds clears old local guild cache before loading the new guild.
- Local orphan POIs are no longer pushed into guild sync.
- Dashboard guild logo increased to 160x160 with a larger frame.
- All v1.5 tactical cleanup features are preserved.

No new Supabase SQL is required for this update if v1.5 already ran.
