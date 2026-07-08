# StankyTools Phase 4 Sprint A4

Adds migration adapters for:

- Events
- Event responses
- Ideas
- Announcements

These are compatibility adapters. They let existing UI code move to `SyncManager` one page at a time without rewriting the full app at once.

## Install

Copy the `stanky_market/sync/adapters/` folder into your project.

Run:

```text
docs/supabase_v4_a4_soft_delete_indexes.sql
```

## Next Sprint

A5 should add Deep Desert POI/Base adapters and role-aware delete rules.
