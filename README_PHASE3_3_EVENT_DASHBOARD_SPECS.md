# Phase 3.3 Event Dashboard + Local Specialization Sync

Changes included:

- Dashboard event cards now support right-click responses:
  - Mark Attending
  - Mark Interested
  - Remove Response
  - Open Details
- Event response changes save locally first so the UI updates immediately.
- If Supabase is unavailable, event response changes remain locally visible.
- Member specializations now have a local pending-sync flag.
- Local specialization edits are preserved during remote pulls instead of being wiped out.
- Pending local specialization edits are pushed before guild dashboard sync pulls fresh remote data.

Run this SQL if needed:

`docs/supabase_v3_3_event_dashboard_specs.sql`
