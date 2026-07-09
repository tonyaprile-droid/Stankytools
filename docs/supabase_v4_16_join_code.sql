-- Sprint A16: separate public join code from internal guild_code.
-- This lets owners/officers rotate the join code for future members
-- without moving existing members or changing the guild_code used by existing data.

alter table public.guilds
add column if not exists join_code text;

update public.guilds
set join_code = guild_code
where coalesce(join_code, '') = '';

create unique index if not exists guilds_join_code_unique_idx
on public.guilds (upper(join_code))
where join_code is not null and join_code <> '';

create index if not exists guilds_guild_code_lookup_idx
on public.guilds (upper(guild_code));

-- Optional: keep updated_at fresh if your guilds table has this column and trigger support.
