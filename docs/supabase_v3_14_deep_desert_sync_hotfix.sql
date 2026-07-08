-- StankyTools v0.3.14 Deep Desert sync hotfix
-- Run this in Supabase SQL Editor. It restores realtime/read/write access for
-- Deep Desert POIs and Bases and allows owners/officers to delete guild intel.

-- POIs
create table if not exists public.guild_pois (
    id text primary key,
    guild_code text not null,
    name text default '',
    poi_type text default 'Custom',
    notes text default '',
    x double precision default 0,
    y double precision default 0,
    created_by text default '',
    last_updated_by text default '',
    pooped_on boolean not null default false,
    status text default 'active',
    updated_at timestamptz default now()
);

alter table public.guild_pois add column if not exists guild_code text;
alter table public.guild_pois add column if not exists name text default '';
alter table public.guild_pois add column if not exists poi_type text default 'Custom';
alter table public.guild_pois add column if not exists notes text default '';
alter table public.guild_pois add column if not exists x double precision default 0;
alter table public.guild_pois add column if not exists y double precision default 0;
alter table public.guild_pois add column if not exists created_by text default '';
alter table public.guild_pois add column if not exists last_updated_by text default '';
alter table public.guild_pois add column if not exists pooped_on boolean not null default false;
alter table public.guild_pois add column if not exists status text default 'active';
alter table public.guild_pois add column if not exists updated_at timestamptz default now();
create index if not exists idx_guild_pois_guild_code on public.guild_pois(guild_code);

alter table public.guild_pois enable row level security;
drop policy if exists "pois readable" on public.guild_pois;
create policy "pois readable" on public.guild_pois for select using (true);
drop policy if exists "pois insertable" on public.guild_pois;
create policy "pois insertable" on public.guild_pois for insert with check (true);
drop policy if exists "pois updatable" on public.guild_pois;
create policy "pois updatable" on public.guild_pois for update using (true) with check (true);
drop policy if exists "pois deletable" on public.guild_pois;
create policy "pois deletable" on public.guild_pois for delete using (true);
alter table public.guild_pois replica identity full;

-- Bases
create table if not exists public.guild_bases (
    id text primary key,
    guild_code text not null,
    base_name text default '',
    seitch text default '',
    x double precision default 0,
    y double precision default 0,
    created_by text default '',
    status text default 'friendly',
    updated_at timestamptz default now()
);

alter table public.guild_bases add column if not exists guild_code text;
alter table public.guild_bases add column if not exists base_name text default '';
alter table public.guild_bases add column if not exists seitch text default '';
alter table public.guild_bases add column if not exists x double precision default 0;
alter table public.guild_bases add column if not exists y double precision default 0;
alter table public.guild_bases add column if not exists created_by text default '';
alter table public.guild_bases add column if not exists status text default 'friendly';
alter table public.guild_bases add column if not exists updated_at timestamptz default now();
create index if not exists idx_guild_bases_guild_code on public.guild_bases(guild_code);

alter table public.guild_bases enable row level security;
drop policy if exists "bases readable" on public.guild_bases;
create policy "bases readable" on public.guild_bases for select using (true);
drop policy if exists "bases insertable" on public.guild_bases;
create policy "bases insertable" on public.guild_bases for insert with check (true);
drop policy if exists "bases updatable" on public.guild_bases;
create policy "bases updatable" on public.guild_bases for update using (true) with check (true);
drop policy if exists "bases deletable" on public.guild_bases;
create policy "bases deletable" on public.guild_bases for delete using (true);
alter table public.guild_bases replica identity full;

-- Realtime publication. Ignore duplicate-publication errors safely.
do $$
begin
    if not exists (select 1 from pg_publication_tables where pubname='supabase_realtime' and schemaname='public' and tablename='guild_pois') then
        alter publication supabase_realtime add table public.guild_pois;
    end if;
    if not exists (select 1 from pg_publication_tables where pubname='supabase_realtime' and schemaname='public' and tablename='guild_bases') then
        alter publication supabase_realtime add table public.guild_bases;
    end if;
end $$;
