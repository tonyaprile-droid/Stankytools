-- StankyTools guild events + member specialization sync
-- Run in Supabase SQL Editor once.

create table if not exists public.guild_events (
  id uuid primary key default gen_random_uuid(),
  guild_code text not null,
  title text not null default '',
  body text not null default '',
  created_by text not null default '',
  event_at text not null default '',
  created_at timestamptz not null default now()
);

create index if not exists idx_guild_events_guild_code on public.guild_events(guild_code);
create index if not exists idx_guild_events_event_at on public.guild_events(guild_code, event_at desc);

create table if not exists public.guild_event_attendance (
  event_id uuid not null references public.guild_events(id) on delete cascade,
  guild_code text not null,
  display_name text not null,
  status text not null default 'attending' check (status in ('attending', 'interested')),
  created_at timestamptz not null default now(),
  primary key (event_id, display_name)
);

alter table public.guild_event_attendance add column if not exists status text not null default 'attending';
alter table public.guild_event_attendance drop constraint if exists guild_event_attendance_status_check;
alter table public.guild_event_attendance add constraint guild_event_attendance_status_check check (status in ('attending', 'interested'));

create index if not exists idx_guild_event_attendance_guild on public.guild_event_attendance(guild_code);
create index if not exists idx_guild_event_attendance_event on public.guild_event_attendance(event_id);
create index if not exists idx_guild_event_attendance_status on public.guild_event_attendance(event_id, status);

create table if not exists public.member_specializations (
  guild_code text not null,
  display_name text not null,
  combat integer not null default 1 check (combat between 1 and 100),
  exploration integer not null default 1 check (exploration between 1 and 100),
  crafting integer not null default 1 check (crafting between 1 and 100),
  gathering integer not null default 1 check (gathering between 1 and 100),
  sabotage integer not null default 1 check (sabotage between 1 and 100),
  updated_at timestamptz not null default now(),
  primary key (guild_code, display_name)
);

create or replace function public.set_member_specializations_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_member_specializations_updated_at on public.member_specializations;
create trigger trg_member_specializations_updated_at
before update on public.member_specializations
for each row execute function public.set_member_specializations_updated_at();

alter table public.guild_events enable row level security;
alter table public.member_specializations enable row level security;
alter table public.guild_event_attendance enable row level security;

-- Desktop app uses the anon key. These policies intentionally match the existing lightweight guild-sync model.
drop policy if exists "guild_events_read" on public.guild_events;
drop policy if exists "guild_events_insert" on public.guild_events;
drop policy if exists "guild_events_update" on public.guild_events;
drop policy if exists "guild_events_delete" on public.guild_events;
create policy "guild_events_read" on public.guild_events for select using (true);
create policy "guild_events_insert" on public.guild_events for insert with check (true);
create policy "guild_events_update" on public.guild_events for update using (true) with check (true);
create policy "guild_events_delete" on public.guild_events for delete using (true);

drop policy if exists "member_specializations_read" on public.member_specializations;
drop policy if exists "member_specializations_insert" on public.member_specializations;
drop policy if exists "member_specializations_update" on public.member_specializations;
drop policy if exists "member_specializations_delete" on public.member_specializations;
create policy "member_specializations_read" on public.member_specializations for select using (true);
create policy "member_specializations_insert" on public.member_specializations for insert with check (true);
create policy "member_specializations_update" on public.member_specializations for update using (true) with check (true);
create policy "member_specializations_delete" on public.member_specializations for delete using (true);

drop policy if exists "guild_event_attendance_read" on public.guild_event_attendance;
drop policy if exists "guild_event_attendance_insert" on public.guild_event_attendance;
drop policy if exists "guild_event_attendance_update" on public.guild_event_attendance;
drop policy if exists "guild_event_attendance_delete" on public.guild_event_attendance;
create policy "guild_event_attendance_read" on public.guild_event_attendance for select using (true);
create policy "guild_event_attendance_insert" on public.guild_event_attendance for insert with check (true);
create policy "guild_event_attendance_update" on public.guild_event_attendance for update using (true) with check (true);
create policy "guild_event_attendance_delete" on public.guild_event_attendance for delete using (true);
