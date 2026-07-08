# StankyTools v1.0 Foundation Milestone 1

This milestone starts the AAA premium UI redesign without removing existing app functionality.

## Added
- New reusable `stanky_market/ui` package.
- Centralized premium theme system in `ui/theme.py`.
- Reusable command UI components:
  - `CommandCard`
  - `StatusPill`
  - `GoldButton`
- Rebuilt global stylesheet around matte black, bronze, brass, desert gold, and warm white.
- Reworked sidebar into a compact command-console layout.
- Sidebar now shows the live app version instead of old alpha labels.
- Reduced oversized sidebar nav buttons and improved readability.
- Added custom styling for buttons, inputs, tabs, tables, cards, scrollbars, checkboxes, progress bars, dialogs, and tooltips.

## Notes
This is the first foundation pass. Existing pages still use their current builders, but they now run under the new visual system. Next milestones can migrate Dashboard, Deep Desert, Auction House, Scanner, Guild, Resources, and Settings into dedicated component-based pages.
