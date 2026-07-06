-- DANGER: Deletes every StankyTools guild and all guild-linked data.
-- Run this only if you want to start completely fresh.

DELETE FROM guild_links;
DELETE FROM guild_news;
DELETE FROM guild_activity;
DELETE FROM guild_bases;
DELETE FROM guild_pois;
DELETE FROM guild_members;
DELETE FROM guilds;
