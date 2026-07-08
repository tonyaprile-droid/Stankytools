-- Phase 3.2 - Guild logo sync support
-- Run this once in Supabase SQL Editor if guild logos do not sync between members.

alter table public.guilds
  add column if not exists logo_data text default '';

-- Keep realtime available for guild row changes, including logo updates.
alter publication supabase_realtime add table public.guilds;
