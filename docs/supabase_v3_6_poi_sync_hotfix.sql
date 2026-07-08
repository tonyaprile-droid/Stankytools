-- StankyTools v3.6 Deep Desert POI sync hotfix
-- Run in Supabase SQL Editor if Deep Desert POIs do not sync between users.

alter table if exists public.guild_pois add column if not exists guild_code text;
alter table if exists public.guild_pois add column if not exists name text;
alter table if exists public.guild_pois add column if not exists poi_type text default 'Custom';
alter table if exists public.guild_pois add column if not exists notes text default '';
alter table if exists public.guild_pois add column if not exists x double precision default 0;
alter table if exists public.guild_pois add column if not exists y double precision default 0;
alter table if exists public.guild_pois add column if not exists created_by text default '';
alter table if exists public.guild_pois add column if not exists last_updated_by text default '';
alter table if exists public.guild_pois add column if not exists pooped_on boolean not null default false;
alter table if exists public.guild_pois add column if not exists status text default 'active';
alter table if exists public.guild_pois add column if not exists updated_at timestamptz default now();

create index if not exists idx_guild_pois_guild_code on public.guild_pois(guild_code);

alter table public.guild_pois enable row level security;

drop policy if exists "pois readable" on public.guild_pois;
create policy "pois readable" on public.guild_pois for select using (true);

drop policy if exists "pois insertable" on public.guild_pois;
create policy "pois insertable" on public.guild_pois for insert with check (true);

drop policy if exists "pois updatable" on public.guild_pois;
create policy "pois updatable" on public.guild_pois for update using (true);

drop policy if exists "pois deletable" on public.guild_pois;
create policy "pois deletable" on public.guild_pois for delete using (true);

-- Make UPDATEs visible to realtime payloads. Safe to run more than once.
alter table public.guild_pois replica identity full;

-- Ensure the table is part of the realtime publication.
do $$
begin
    if not exists (
        select 1
        from pg_publication_tables
        where pubname = 'supabase_realtime'
          and schemaname = 'public'
          and tablename = 'guild_pois'
    ) then
        alter publication supabase_realtime add table public.guild_pois;
    end if;
end $$;
