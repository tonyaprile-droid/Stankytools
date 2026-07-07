# StankyTools v1.0 Foundation Milestone 5.4 Hotfix

## Easter egg video asset

- Replaced the YouTube/WebEngine Easter egg with a local MP4 player using Qt Multimedia.
- The app now looks for `pgmayo.mp4` in the user cache first.
- If missing, it downloads from GitHub Releases:

  `https://github.com/tonyaprile-droid/Stankytools/releases/latest/download/pgmayo.mp4`

- If the GitHub asset is not available while running from source, the bundled developer fallback in `assets/videos/pgmayo.mp4` is used.
- Video does **not** autoplay.
- The popup closes automatically when the video reaches the end.

## Release requirement

Attach `pgmayo.mp4` to your latest GitHub release asset list so installed users can download/cache it on demand.

## PyInstaller

Updated `StankyTools.spec` to include Qt Multimedia and Qt Multimedia Widgets.
