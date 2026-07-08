# Phase 3.7 - Weekly Deep Desert Map Screenshot

## Added

- Deep Desert page now uses `https://dune.gaming.tools/deep-desert` as the weekly map source.
- Added **Update Weekly Map** button to the Deep Desert page.
- The app opens the source map in hidden Qt WebEngine, waits 5 seconds, captures the rendered map page, and saves it as the local Deep Desert map.
- Cached map is saved to the user's persistent data folder:
  - `%LOCALAPPDATA%/StankyTools/data/deep_desert_map.png`
- Deep Desert canvas reloads immediately after capture.
- Automatic weekly check runs when the Deep Desert page opens:
  - Tuesday
  - 7:30 AM Eastern
  - once per weekly update window
- No Playwright dependency required.
- No scheduled external ChatGPT task required.

## Notes

This keeps the app package small because the weekly map image is cached locally by each user instead of being bundled with the release.
