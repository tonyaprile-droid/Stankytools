-- Phase 3.3 - Event dashboard responses and member specialization local sync support
-- Safe to run more than once.

-- Event attendance/interest responses. One response per event/user.
CREATE TABLE IF NOT EXISTS public.guild_event_attendance (
    event_id uuid NOT NULL,
    guild_code text NOT NULL,
    display_name text NOT NULL,
    status text NOT NULL DEFAULT 'attending' CHECK (status IN ('attending', 'interested')),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (event_id, display_name)
);

ALTER TABLE public.guild_event_attendance REPLICA IDENTITY FULL;

CREATE INDEX IF NOT EXISTS idx_guild_event_attendance_guild
ON public.guild_event_attendance (guild_code);

CREATE INDEX IF NOT EXISTS idx_guild_event_attendance_event
ON public.guild_event_attendance (event_id);

-- Member specializations used by guild sync.
CREATE TABLE IF NOT EXISTS public.member_specializations (
    guild_code text NOT NULL,
    display_name text NOT NULL,
    crafting integer NOT NULL DEFAULT 1 CHECK (crafting BETWEEN 1 AND 100),
    gathering integer NOT NULL DEFAULT 1 CHECK (gathering BETWEEN 1 AND 100),
    exploration integer NOT NULL DEFAULT 1 CHECK (exploration BETWEEN 1 AND 100),
    combat integer NOT NULL DEFAULT 1 CHECK (combat BETWEEN 1 AND 100),
    sabotage integer NOT NULL DEFAULT 1 CHECK (sabotage BETWEEN 1 AND 100),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (guild_code, display_name)
);

ALTER TABLE public.member_specializations REPLICA IDENTITY FULL;

CREATE INDEX IF NOT EXISTS idx_member_specializations_guild
ON public.member_specializations (guild_code);

-- Optional realtime publication setup. Ignore duplicate publication membership errors if Supabase reports them.
DO $$
BEGIN
    BEGIN
        ALTER PUBLICATION supabase_realtime ADD TABLE public.guild_event_attendance;
    EXCEPTION WHEN duplicate_object THEN
        NULL;
    END;
    BEGIN
        ALTER PUBLICATION supabase_realtime ADD TABLE public.member_specializations;
    EXCEPTION WHEN duplicate_object THEN
        NULL;
    END;
END $$;
