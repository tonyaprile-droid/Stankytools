-- StankyTools Hagga Basin guild bases
-- Run in Supabase SQL Editor after the guild system SQL.

create table if not exists guild_bases (
  id uuid primary key default gen_random_uuid(),
  guild_code text not null references guilds(guild_code) on delete cascade,
  base_name text not null default 'Guild Base',
  seitch text not null default '',
  x real not null,
  y real not null,
  created_by text default '',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

alter table guild_bases enable row level security;

drop policy if exists "bases readable" on guild_bases;
create policy "bases readable" on guild_bases for select using (true);

drop policy if exists "bases insertable" on guild_bases;
create policy "bases insertable" on guild_bases for insert with check (true);

drop policy if exists "bases updatable" on guild_bases;
create policy "bases updatable" on guild_bases for update using (true);

drop policy if exists "bases deletable" on guild_bases;
create policy "bases deletable" on guild_bases for delete using (true);

create index if not exists idx_guild_bases_guild on guild_bases(guild_code);
create index if not exists idx_guild_bases_created_by on guild_bases(guild_code, created_by);

-- v1.2 base tactical status upgrade
alter table guild_bases add column if not exists status text not null default 'friendly';
