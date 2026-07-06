-- StankyTools v1.2 Tactical Guild Update
-- Run this in Supabase SQL Editor.
-- Adds guild logos, guild member removal policy, and base tactical status.

alter table guilds add column if not exists logo_data text default '';

create table if not exists guild_bases (
  id uuid primary key default gen_random_uuid(),
  guild_code text not null references guilds(guild_code) on delete cascade,
  base_name text not null default 'Guild Base',
  seitch text not null default '',
  x real not null,
  y real not null,
  created_by text default '',
  status text not null default 'friendly' check (status in ('friendly','enemy','defeated')),
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

alter table guild_bases add column if not exists status text not null default 'friendly';

alter table guild_bases enable row level security;

-- Keep policies simple for guild-code desktop sync using the public anon key.
drop policy if exists "bases readable" on guild_bases;
create policy "bases readable" on guild_bases for select using (true);

drop policy if exists "bases insertable" on guild_bases;
create policy "bases insertable" on guild_bases for insert with check (true);

drop policy if exists "bases updatable" on guild_bases;
create policy "bases updatable" on guild_bases for update using (true);

drop policy if exists "bases deletable" on guild_bases;
create policy "bases deletable" on guild_bases for delete using (true);

drop policy if exists "members deletable" on guild_members;
create policy "members deletable" on guild_members for delete using (true);

create index if not exists idx_guild_bases_guild on guild_bases(guild_code);
create index if not exists idx_guild_bases_created_by on guild_bases(guild_code, created_by);
