# StankyTools v1.0 Foundation Milestone 2

Dashboard Command Center redesign.

## Added
- Rebuilt Dashboard into a premium command-center layout.
- New hero banner with guild/server/build/sync status.
- Large stat cards for Guild Members, Guild Bases, Deep Desert POIs, and Items Tracked.
- Quick Action cards for Scan Auction, Deep Desert, Auction House, Manage Guild, and Sync All.
- Guild Announcements now render as premium cards instead of a generic table.
- Market Movers panel placeholder tied to live local app stats.
- Upcoming panel with Deep Desert reset and scanner status cards.
- New reusable dashboard UI components in `app.py`:
  - `PremiumStatCard`
  - `QuickActionCard`
  - `NewsCard`
  - `MarketMoverCard`
- Premium stylesheet additions for the new dashboard components.
- App version updated to `1.0.0-foundation.2`.

## Notes
- Existing dashboard tables are kept hidden for compatibility with existing refresh/detail methods.
- This milestone focuses on Dashboard migration. Deep Desert tactical redesign remains the next major sprint.
