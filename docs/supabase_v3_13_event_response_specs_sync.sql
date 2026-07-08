-- Phase 3.13 - Event response + member specialization sync hardening
-- Run in Supabase SQL Editor.

CREATE TABLE IF NOT EXISTS public.guild_event_attendance (
    event_id text NOT NULL,
    guild_code text NOT NULL,
    display_name text NOT NULL,
    status text NOT NULL DEFAULT 'attending',
    created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.guild_event_attendance
DROP CONSTRAINT IF EXISTS guild_event_attendance_status_check;

ALTER TABLE public.guild_event_attendance
ADD CONSTRAINT guild_event_attendance_status_check
CHECK (status IN ('attending', 'interested'));

-- One member can only have one response per event/guild.
CREATE UNIQUE INDEX IF NOT EXISTS guild_event_attendance_unique_response
ON public.guild_event_attendance(event_id, guild_code, display_name);

-- Backward compatibility for older app builds that used on_conflict=event_id,display_name.
CREATE UNIQUE INDEX IF NOT EXISTS guild_event_attendance_legacy_unique_response
ON public.guild_event_attendance(event_id, display_name);

CREATE INDEX IF NOT EXISTS idx_guild_event_attendance_guild
ON public.guild_event_attendance(guild_code);

CREATE INDEX IF NOT EXISTS idx_guild_event_attendance_event
ON public.guild_event_attendance(event_id);

CREATE INDEX IF NOT EXISTS idx_guild_event_attendance_status
ON public.guild_event_attendance(event_id, guild_code, status);

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

CREATE TABLE IF NOT EXISTS public.member_specializations (
    guild_code text NOT NULL,
    display_name text NOT NULL,
    crafting integer NOT NULL DEFAULT 1,
    gathering integer NOT NULL DEFAULT 1,
    exploration integer NOT NULL DEFAULT 1,
    combat integer NOT NULL DEFAULT 1,
    sabotage integer NOT NULL DEFAULT 1,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (guild_code, display_name)
);

CREATE INDEX IF NOT EXISTS idx_member_specializations_guild
ON public.member_specializations(guild_code);

ALTER TABLE public.member_specializations REPLICA IDENTITY FULL;
ALTER TABLE public.member_specializations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS member_specializations_read ON public.member_specializations;
DROP POLICY IF EXISTS member_specializations_insert ON public.member_specializations;
DROP POLICY IF EXISTS member_specializations_update ON public.member_specializations;
DROP POLICY IF EXISTS member_specializations_delete ON public.member_specializations;
DROP POLICY IF EXISTS "member_specializations_read" ON public.member_specializations;
DROP POLICY IF EXISTS "member_specializations_insert" ON public.member_specializations;
DROP POLICY IF EXISTS "member_specializations_update" ON public.member_specializations;
DROP POLICY IF EXISTS "member_specializations_delete" ON public.member_specializations;

CREATE POLICY "member_specializations_read" ON public.member_specializations FOR SELECT USING (true);
CREATE POLICY "member_specializations_insert" ON public.member_specializations FOR INSERT WITH CHECK (true);
CREATE POLICY "member_specializations_update" ON public.member_specializations FOR UPDATE USING (true) WITH CHECK (true);
CREATE POLICY "member_specializations_delete" ON public.member_specializations FOR DELETE USING (true);

CREATE OR REPLACE FUNCTION public.set_member_specializations_updated_at()
RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_member_specializations_updated_at ON public.member_specializations;
CREATE TRIGGER trg_member_specializations_updated_at
BEFORE UPDATE ON public.member_specializations
FOR EACH ROW EXECUTE FUNCTION public.set_member_specializations_updated_at();

DO $$
BEGIN
    BEGIN
        ALTER PUBLICATION supabase_realtime ADD TABLE public.guild_event_attendance;
    EXCEPTION WHEN duplicate_object THEN NULL;
    END;
    BEGIN
        ALTER PUBLICATION supabase_realtime ADD TABLE public.member_specializations;
    EXCEPTION WHEN duplicate_object THEN NULL;
    END;
END $$;
