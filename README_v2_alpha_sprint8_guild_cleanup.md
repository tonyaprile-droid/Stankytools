# StankyTools v2 Alpha Sprint 8

Changes included:
- Stronger last-member guild cleanup: leaving now deletes the member, re-checks remaining members, and deletes the guild if empty.
- Creating a guild now cleans up empty/orphaned guild rows with the same name/code before blocking duplicates.
- Guild News tables now use `Poster` instead of `Officer`.
- Useful Links now show a `Poster` column.
- Replaced the default guild logo placeholder with a cleaner Dune-style guild emblem.
- Sprint 7 changes preserved.

No new Supabase SQL is required if previous v1.8 SQL was already applied.
