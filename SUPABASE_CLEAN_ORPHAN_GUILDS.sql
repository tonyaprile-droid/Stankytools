-- Clean up guild rows with no members so the same guild name/code can be reused.
-- Safe to run more than once.

DELETE FROM guild_news
WHERE guild_code IN (
  SELECT g.guild_code
  FROM guilds g
  WHERE NOT EXISTS (
    SELECT 1 FROM guild_members m WHERE m.guild_code = g.guild_code
  )
);

DELETE FROM guild_links
WHERE guild_code IN (
  SELECT g.guild_code
  FROM guilds g
  WHERE NOT EXISTS (
    SELECT 1 FROM guild_members m WHERE m.guild_code = g.guild_code
  )
);

DELETE FROM guild_activity
WHERE guild_code IN (
  SELECT g.guild_code
  FROM guilds g
  WHERE NOT EXISTS (
    SELECT 1 FROM guild_members m WHERE m.guild_code = g.guild_code
  )
);

DELETE FROM guild_bases
WHERE guild_code IN (
  SELECT g.guild_code
  FROM guilds g
  WHERE NOT EXISTS (
    SELECT 1 FROM guild_members m WHERE m.guild_code = g.guild_code
  )
);

DELETE FROM guild_pois
WHERE guild_code IN (
  SELECT g.guild_code
  FROM guilds g
  WHERE NOT EXISTS (
    SELECT 1 FROM guild_members m WHERE m.guild_code = g.guild_code
  )
);

DELETE FROM guilds g
WHERE NOT EXISTS (
  SELECT 1 FROM guild_members m WHERE m.guild_code = g.guild_code
);
