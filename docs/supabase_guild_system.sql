-- StankyTools Guild System
-- Run this in Supabase SQL Editor.
-- Use only the public/anon key inside the desktop app. Never ship the service role / secret key.

create extension if not exists pgcrypto;

create table if not exists guilds (
  id uuid primary key default gen_random_uuid(),
  guild_code text unique not null,
  guild_name text not null,
  owner_name text not null,
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

create table if not exists guild_activity (
  id uuid primary key default gen_random_uuid(),
  guild_code text not null references guilds(guild_code) on delete cascade,
  actor text default '',
  message text not null,
  poi_id uuid null,
  created_at timestamptz default now()
);

-- Safe ALTERs for users upgrading from older StankyTools builds.
alter table guild_pois add column if not exists pooped_on boolean not null default false;
alter table guild_pois add column if not exists last_updated_by text default '';

alter table guilds enable row level security;
alter table guild_members enable row level security;
alter table guild_pois enable row level security;
alter table guild_activity enable row level security;

-- Simple public-anon policies for guild-code based desktop sync.
-- Anyone with the public app key and guild code can read/write rows for that guild.
-- Keep the service role key private.

drop policy if exists "guilds readable" on guilds;
create policy "guilds readable" on guilds for select using (true);

drop policy if exists "guilds insertable" on guilds;
create policy "guilds insertable" on guilds for insert with check (true);

drop policy if exists "guilds updatable" on guilds;
create policy "guilds updatable" on guilds for update using (true);

drop policy if exists "members readable" on guild_members;
create policy "members readable" on guild_members for select using (true);

drop policy if exists "members insertable" on guild_members;
create policy "members insertable" on guild_members for insert with check (true);

drop policy if exists "members updatable" on guild_members;
create policy "members updatable" on guild_members for update using (true);

drop policy if exists "pois readable" on guild_pois;
create policy "pois readable" on guild_pois for select using (true);

drop policy if exists "pois insertable" on guild_pois;
create policy "pois insertable" on guild_pois for insert with check (true);

drop policy if exists "pois updatable" on guild_pois;
create policy "pois updatable" on guild_pois for update using (true);

drop policy if exists "pois deletable" on guild_pois;
create policy "pois deletable" on guild_pois for delete using (true);

drop policy if exists "activity readable" on guild_activity;
create policy "activity readable" on guild_activity for select using (true);

drop policy if exists "activity insertable" on guild_activity;
create policy "activity insertable" on guild_activity for insert with check (true);

-- v1.2 tactical guild update
alter table guilds add column if not exists logo_data text default '';

drop policy if exists "members deletable" on guild_members;
create policy "members deletable" on guild_members for delete using (true);
