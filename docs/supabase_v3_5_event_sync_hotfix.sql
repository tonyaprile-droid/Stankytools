-- StankyTools v3.5 event sync hotfix
-- Safe to run more than once in Supabase SQL Editor.

CREATE TABLE IF NOT EXISTS public.guild_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  guild_code text NOT NULL,
  title text NOT NULL DEFAULT '',
  body text NOT NULL DEFAULT '',
  created_by text NOT NULL DEFAULT '',
  event_at text NOT NULL DEFAULT '',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_guild_events_guild_code
ON public.guild_events(guild_code);

CREATE INDEX IF NOT EXISTS idx_guild_events_event_at
ON public.guild_events(guild_code, event_at DESC);

ALTER TABLE public.guild_events REPLICA IDENTITY FULL;
ALTER TABLE public.guild_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS guild_events_read ON public.guild_events;
DROP POLICY IF EXISTS guild_events_insert ON public.guild_events;
DROP POLICY IF EXISTS guild_events_update ON public.guild_events;
DROP POLICY IF EXISTS guild_events_delete ON public.guild_events;
DROP POLICY IF EXISTS "guild_events_read" ON public.guild_events;
DROP POLICY IF EXISTS "guild_events_insert" ON public.guild_events;
DROP POLICY IF EXISTS "guild_events_update" ON public.guild_events;
DROP POLICY IF EXISTS "guild_events_delete" ON public.guild_events;

CREATE POLICY "guild_events_read" ON public.guild_events FOR SELECT USING (true);
CREATE POLICY "guild_events_insert" ON public.guild_events FOR INSERT WITH CHECK (true);
CREATE POLICY "guild_events_update" ON public.guild_events FOR UPDATE USING (true) WITH CHECK (true);
CREATE POLICY "guild_events_delete" ON public.guild_events FOR DELETE USING (true);

CREATE TABLE IF NOT EXISTS public.guild_event_attendance (
  event_id uuid NOT NULL REFERENCES public.guild_events(id) ON DELETE CASCADE,
  guild_code text NOT NULL,
  display_name text NOT NULL,
  status text NOT NULL DEFAULT 'attending',
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (event_id, display_name)
);

ALTER TABLE public.guild_event_attendance
ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'attending';

ALTER TABLE public.guild_event_attendance
DROP CONSTRAINT IF EXISTS guild_event_attendance_status_check;

ALTER TABLE public.guild_event_attendance
ADD CONSTRAINT guild_event_attendance_status_check
CHECK (status IN ('attending', 'interested'));

CREATE INDEX IF NOT EXISTS idx_guild_event_attendance_guild
ON public.guild_event_attendance(guild_code);

CREATE INDEX IF NOT EXISTS idx_guild_event_attendance_event
ON public.guild_event_attendance(event_id);

CREATE INDEX IF NOT EXISTS idx_guild_event_attendance_status
ON public.guild_event_attendance(event_id, status);

ALTER TABLE public.guild_event_attendance REPLICA IDENTITY FULL;
ALTER TABLE public.guild_event_attendance ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS guild_event_attendance_read ON public.guild_event_attendance;
DROP POLICY IF EXISTS guild_event_attendance_insert ON public.guild_event_attendance;
DROP POLICY IF EXISTS guild_event_attendance_update ON public.guild_event_attendance;
DROP POLICY IF EXISTS guild_event_attendance_delete ON public.guild_event_attendance;
DROP POLICY IF EXISTS "guild_event_attendance_read" ON public.guild_event_attendance;
DROP POLICY IF EXISTS "guild_event_attendance_insert" ON public.guild_event_attendance;
DROP POLICY IF EXISTS "guild_event_attendance_update" ON public.guild_event_attendance;
DROP POLICY IF EXISTS "guild_event_attendance_delete" ON public.guild_event_attendance;

CREATE POLICY "guild_event_attendance_read" ON public.guild_event_attendance FOR SELECT USING (true);
CREATE POLICY "guild_event_attendance_insert" ON public.guild_event_attendance FOR INSERT WITH CHECK (true);
CREATE POLICY "guild_event_attendance_update" ON public.guild_event_attendance FOR UPDATE USING (true) WITH CHECK (true);
CREATE POLICY "guild_event_attendance_delete" ON public.guild_event_attendance FOR DELETE USING (true);

DO $$
BEGIN
  BEGIN
    ALTER PUBLICATION supabase_realtime ADD TABLE public.guild_events;
  EXCEPTION WHEN duplicate_object THEN
    NULL;
  END;
  BEGIN
    ALTER PUBLICATION supabase_realtime ADD TABLE public.guild_event_attendance;
  EXCEPTION WHEN duplicate_object THEN
    NULL;
  END;
END $$;
