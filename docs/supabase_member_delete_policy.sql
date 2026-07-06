-- Allow StankyTools to delete guild members through the public anon key.
-- Run this in Supabase SQL Editor.

alter table guild_members enable row level security;

drop policy if exists "members deletable" on guild_members;
create policy "members deletable"
on guild_members
for delete
using (true);
