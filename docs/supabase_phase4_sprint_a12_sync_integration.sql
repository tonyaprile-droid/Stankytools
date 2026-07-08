-- Phase 4 Sprint A12 - SyncManager integration support

-- Adds sync fields where missing. Safe to rerun.
do $$
declare
  t text;
begin
  foreach t in array array[
    'guild_events',
    'event_responses',
    'guild_pois',
    'guild_bases',
    'guild_announcements',
    'guild_links',
    'guild_ideas',
    'guild_members',
    'member_specializations'
  ] loop
    execute format('alter table if exists public.%I add column if not exists updated_at timestamptz default now()', t);
    execute format('alter table if exists public.%I add column if not exists deleted_at timestamptz', t);
    execute format('alter table if exists public.%I add column if not exists sync_version bigint default 1', t);
  end loop;
end $$;

create or replace function public.bump_sync_fields()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  new.sync_version = coalesce(old.sync_version, 0) + 1;
  return new;
end;
$$;

-- Indexes for guild-scoped delta sync
create index if not exists idx_guild_events_guild_updated on public.guild_events(guild_id, updated_at);
create index if not exists idx_guild_pois_guild_updated on public.guild_pois(guild_id, updated_at);
create index if not exists idx_guild_bases_guild_updated on public.guild_bases(guild_id, updated_at);
create index if not exists idx_guild_announcements_guild_updated on public.guild_announcements(guild_id, updated_at);
create index if not exists idx_guild_links_guild_updated on public.guild_links(guild_id, updated_at);
create index if not exists idx_guild_ideas_guild_updated on public.guild_ideas(guild_id, updated_at);
create index if not exists idx_guild_members_guild_updated on public.guild_members(guild_id, updated_at);
create index if not exists idx_event_responses_event_member on public.event_responses(event_id, guild_member_id);

-- Owner/officer POI/base delete permission helper policies are intentionally separated from app logic.
-- Adjust column names if your tables use created_by/member_id instead of owner_user_id.
