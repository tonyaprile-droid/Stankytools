-- StankyTools v1.8 / v2 Alpha Sprint 3 database update
-- Run the CONTENTS of this file in Supabase SQL Editor. Safe to run more than once.

create extension if not exists pgcrypto;

-- Guild news submitted by owners/officers and displayed on dashboard/app launch.
create table if not exists guild_news (
  id uuid primary key default gen_random_uuid(),
  guild_code text not null references guilds(guild_code) on delete cascade,
  title text not null default 'Guild Update',
  body text default '',
  created_by text default '',
  created_at timestamptz default now()
);

-- Guild activity feed. The app logs POI/base/member/logo/link/news actions here.
create table if not exists guild_activity (
  id uuid primary key default gen_random_uuid(),
  guild_code text not null references guilds(guild_code) on delete cascade,
  actor text default '',
  message text not null,
  created_at timestamptz default now()
);

-- Useful guild links submitted by owners/officers.
create table if not exists guild_links (
  id uuid primary key default gen_random_uuid(),
  guild_code text not null references guilds(guild_code) on delete cascade,
  title text not null,
  url text not null,
  created_by text default '',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

alter table guild_news enable row level security;
alter table guild_activity enable row level security;
alter table guild_links enable row level security;

drop policy if exists "news readable" on guild_news;
create policy "news readable" on guild_news for select using (true);
drop policy if exists "news insertable" on guild_news;
create policy "news insertable" on guild_news for insert with check (true);
drop policy if exists "news updatable" on guild_news;
create policy "news updatable" on guild_news for update using (true);
drop policy if exists "news deletable" on guild_news;
create policy "news deletable" on guild_news for delete using (true);

drop policy if exists "activity readable" on guild_activity;
create policy "activity readable" on guild_activity for select using (true);
drop policy if exists "activity insertable" on guild_activity;
create policy "activity insertable" on guild_activity for insert with check (true);
drop policy if exists "activity updatable" on guild_activity;
create policy "activity updatable" on guild_activity for update using (true);
drop policy if exists "activity deletable" on guild_activity;
create policy "activity deletable" on guild_activity for delete using (true);

drop policy if exists "links readable" on guild_links;
create policy "links readable" on guild_links for select using (true);
drop policy if exists "links insertable" on guild_links;
create policy "links insertable" on guild_links for insert with check (true);
drop policy if exists "links updatable" on guild_links;
create policy "links updatable" on guild_links for update using (true);
drop policy if exists "links deletable" on guild_links;
create policy "links deletable" on guild_links for delete using (true);

create index if not exists idx_guild_news_guild_created on guild_news(guild_code, created_at desc);
create index if not exists idx_guild_activity_guild_created on guild_activity(guild_code, created_at desc);
create index if not exists idx_guild_links_guild_title on guild_links(guild_code, title);
