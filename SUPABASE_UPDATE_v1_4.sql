-- StankyTools v1.4 database update
-- Run this in Supabase SQL Editor. It is safe to run more than once.

create extension if not exists pgcrypto;

create table if not exists guilds (
  id uuid primary key default gen_random_uuid(),
  guild_code text unique not null,
  guild_name text not null,
  owner_name text not null,
  logo_data text default '',
  created_at timestamptz default now()
);

create table if not exists guild_members (
  id uuid primary key default gen_random_uuid(),
  guild_code text not null references guilds(guild_code) on delete cascade,
  display_name text not null,
  role text not null default 'member' check (role in ('owner','officer','member','guest')),
  joined_at timestamptz default now(),
  last_seen timestamptz default now(),
  unique(guild_code, display_name)
);

create table if not exists guild_pois (
  id uuid primary key default gen_random_uuid(),
  guild_code text not null references guilds(guild_code) on delete cascade,
  name text not null,
  poi_type text not null default 'Custom',
  x real not null,
  y real not null,
  notes text default '',
  pooped_on boolean not null default false,
  created_by text default '',
  last_updated_by text default '',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists guild_bases (
  id uuid primary key default gen_random_uuid(),
  guild_code text not null references guilds(guild_code) on delete cascade,
  base_name text not null default 'Guild Base',
  seitch text default '',
  x real not null,
  y real not null,
  created_by text default '',
  status text not null default 'friendly' check (status in ('friendly','enemy','defeated')),
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

alter table guilds add column if not exists logo_data text default '';
alter table guild_bases add column if not exists status text not null default 'friendly';
alter table guild_pois add column if not exists pooped_on boolean not null default false;
alter table guild_pois add column if not exists last_updated_by text default '';

create unique index if not exists guilds_guild_name_lower_unique on guilds (lower(guild_name));

alter table guilds enable row level security;
alter table guild_members enable row level security;
alter table guild_pois enable row level security;
alter table guild_bases enable row level security;

-- Simple public-anon policies for this desktop guild-code sync model.
drop policy if exists "guilds readable" on guilds;
create policy "guilds readable" on guilds for select using (true);
drop policy if exists "guilds insertable" on guilds;
create policy "guilds insertable" on guilds for insert with check (true);
drop policy if exists "guilds updatable" on guilds;
create policy "guilds updatable" on guilds for update using (true);
drop policy if exists "guilds deletable" on guilds;
create policy "guilds deletable" on guilds for delete using (true);

drop policy if exists "members readable" on guild_members;
create policy "members readable" on guild_members for select using (true);
drop policy if exists "members insertable" on guild_members;
create policy "members insertable" on guild_members for insert with check (true);
drop policy if exists "members updatable" on guild_members;
create policy "members updatable" on guild_members for update using (true);
drop policy if exists "members deletable" on guild_members;
create policy "members deletable" on guild_members for delete using (true);

drop policy if exists "pois readable" on guild_pois;
create policy "pois readable" on guild_pois for select using (true);
drop policy if exists "pois insertable" on guild_pois;
create policy "pois insertable" on guild_pois for insert with check (true);
drop policy if exists "pois updatable" on guild_pois;
create policy "pois updatable" on guild_pois for update using (true);
drop policy if exists "pois deletable" on guild_pois;
create policy "pois deletable" on guild_pois for delete using (true);

drop policy if exists "bases readable" on guild_bases;
create policy "bases readable" on guild_bases for select using (true);
drop policy if exists "bases insertable" on guild_bases;
create policy "bases insertable" on guild_bases for insert with check (true);
drop policy if exists "bases updatable" on guild_bases;
create policy "bases updatable" on guild_bases for update using (true);
drop policy if exists "bases deletable" on guild_bases;
create policy "bases deletable" on guild_bases for delete using (true);
