-- Phase 4 Sprint A4: soft-delete + delta-sync prep for Events, Ideas, Announcements

alter table if exists public.guild_events
  add column if not exists deleted_at timestamptz,
  add column if not exists sync_version bigint not null default 1;

alter table if exists public.guild_ideas
  add column if not exists deleted_at timestamptz,
  add column if not exists sync_version bigint not null default 1;

alter table if exists public.guild_announcements
  add column if not exists deleted_at timestamptz,
  add column if not exists sync_version bigint not null default 1;

create index if not exists idx_guild_events_guild_updated
  on public.guild_events (guild_id, updated_at desc);

create index if not exists idx_guild_events_guild_deleted
  on public.guild_events (guild_id, deleted_at);

create index if not exists idx_guild_ideas_guild_updated
  on public.guild_ideas (guild_id, updated_at desc);

create index if not exists idx_guild_ideas_guild_deleted
  on public.guild_ideas (guild_id, deleted_at);

create index if not exists idx_guild_announcements_guild_updated
  on public.guild_announcements (guild_id, updated_at desc);

create index if not exists idx_guild_announcements_guild_deleted
  on public.guild_announcements (guild_id, deleted_at);

-- Optional updated_at trigger helper. Safe if you already have one with this name.
create or replace function public.set_updated_at_and_sync_version()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  new.sync_version = coalesce(old.sync_version, 0) + 1;
  return new;
end;
$$;

drop trigger if exists trg_guild_events_sync_version on public.guild_events;
create trigger trg_guild_events_sync_version
before update on public.guild_events
for each row execute function public.set_updated_at_and_sync_version();

drop trigger if exists trg_guild_ideas_sync_version on public.guild_ideas;
create trigger trg_guild_ideas_sync_version
before update on public.guild_ideas
for each row execute function public.set_updated_at_and_sync_version();

drop trigger if exists trg_guild_announcements_sync_version on public.guild_announcements;
create trigger trg_guild_announcements_sync_version
before update on public.guild_announcements
for each row execute function public.set_updated_at_and_sync_version();
