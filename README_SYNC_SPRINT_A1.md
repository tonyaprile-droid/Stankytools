# StankyTools Phase 4.0 Sprint A1

Copy the `stanky_market/sync` folder into your project.

This package adds:
- SyncManager singleton
- Dispatcher/event bus
- Persistent offline queue
- Retry policy
- Cache manager rooted in `%APPDATA%/StankyTools`
- Sync status enum
- Base sync model

This does not migrate existing Events/POIs yet. Next sprint wires one subsystem into SyncManager.
