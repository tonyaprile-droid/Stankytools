-- Phase 4 Sprint A7 helper migration
-- Run only after confirming table names match your Supabase schema.

create index if not exists idx_guild_events_guild_updated on public.guild_events(guild_id, updated_at);
create index if not exists idx_event_responses_event_member on public.event_responses(event_id, guild_member_id);
create index if not exists idx_guild_pois_guild_updated on public.guild_pois(guild_id, updated_at);
create index if not exists idx_guild_bases_guild_updated on public.guild_bases(guild_id, updated_at);
create index if not exists idx_guild_announcements_guild_updated on public.guild_announcements(guild_id, updated_at);
create index if not exists idx_guild_links_guild_updated on public.guild_links(guild_id, updated_at);
create index if not exists idx_guild_ideas_guild_updated on public.guild_ideas(guild_id, updated_at);
create index if not exists idx_member_specializations_guild_member on public.member_specializations(guild_id, guild_member_id);

-- Owners/admins/officers can delete any guild POI/Base; members can delete their own.
-- Adjust created_by column if your schema uses owner_id/user_id instead.
drop policy if exists "guild_pois_delete_owner_officer_member" on public.guild_pois;
create policy "guild_pois_delete_owner_officer_member"
on public.guild_pois
for delete
using (
  created_by = auth.uid()
  or exists (
    select 1 from public.guild_members gm
    where gm.guild_id = guild_pois.guild_id
      and gm.user_id = auth.uid()
      and lower(gm.role) in ('owner', 'admin', 'officer')
  )
);

drop policy if exists "guild_bases_delete_owner_officer_member" on public.guild_bases;
create policy "guild_bases_delete_owner_officer_member"
on public.guild_bases
for delete
using (
  created_by = auth.uid()
  or exists (
    select 1 from public.guild_members gm
    where gm.guild_id = guild_bases.guild_id
      and gm.user_id = auth.uid()
      and lower(gm.role) in ('owner', 'admin', 'officer')
  )
);
