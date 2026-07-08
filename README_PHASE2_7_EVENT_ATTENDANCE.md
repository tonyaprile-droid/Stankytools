# Phase 2.7 - Event Attendance

Included in this patch:

- Added guild event attendance support.
- Guild members can select an event and click **Mark Attending**.
- Guild members can remove their attendance with **Remove Attendance**.
- Added **View Attendees** for selected events.
- Events table now shows the attendance count and marks the current user with `YES` when attending.
- Dashboard events table now shows attendance count.
- Supabase SQL updated with `guild_event_attendance` table and RLS policies.

Required Supabase step:

Run this updated SQL file again in Supabase SQL Editor:

`docs/supabase_v2_events_specializations_sync.sql`

Testing:

1. Launch two app copies using the same guild code.
2. Create an event as owner/officer.
3. Select the event as a guild member and click **Mark Attending**.
4. Confirm the attendance count updates after sync.
5. Click **View Attendees** to confirm the member name appears.
