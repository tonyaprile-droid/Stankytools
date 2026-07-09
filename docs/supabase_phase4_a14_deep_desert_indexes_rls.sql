-- Phase 4 Sprint A14 - Deep Desert POI/Base sync hardening
-- Run in Supabase SQL Editor.

alter table if exists public.guild_pois add column if not exists deleted_at timestamptz;
alter table if exists public.guild_pois add column if not exists updated_at timestamptz default now();
alter table if exists public.guild_pois add column if not exists updated_by text;

alter table if exists public.guild_bases add column if not exists deleted_at timestamptz;
alter table if exists public.guild_bases add column if not exists updated_at timestamptz default now();
alter table if exists public.guild_bases add column if not exists updated_by text;

create index if not exists idx_guild_pois_guild_code_updated on public.guild_pois(guild_code, updated_at);
create index if not exists idx_guild_pois_guild_code_deleted on public.guild_pois(guild_code, deleted_at);
create index if not exists idx_guild_bases_guild_code_updated on public.guild_bases(guild_code, updated_at);
create index if not exists idx_guild_bases_guild_code_deleted on public.guild_bases(guild_code, deleted_at);

-- If your project uses RLS with display_name text identities, adapt these policies to your existing auth model.
-- The important rule: owner/admin/officer can delete any marker in their guild; members only their own.

-- Example role-policy template using guild_members.display_name and guild_code:
-- drop policy if exists "guild_pois_delete_managers_or_owner" on public.guild_pois;
-- create policy "guild_pois_delete_managers_or_owner"
-- on public.guild_pois
-- for delete
-- using (
--   created_by = current_setting('request.jwt.claims', true)::json->>'display_name'
--   or exists (
--     select 1 from public.guild_members gm
--     where gm.guild_code = guild_pois.guild_code
--       and gm.display_name = current_setting('request.jwt.claims', true)::json->>'display_name'
--       and lower(gm.role) in ('owner','admin','officer')
--   )
-- );
