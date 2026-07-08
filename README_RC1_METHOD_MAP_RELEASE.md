# RC1 Method Map + UI Patch

This build keeps the app's local guild POI overlay, and adds a live Deep Desert tab that loads:

https://www.method.gg/dune-awakening/deep-desert-companion

The live tab preserves the Method.gg map filters because it links into the live page instead of copying their map data.

## Notes
- Deep Desert page now has two tabs:
  - Live Map + Filters
  - Guild POI Overlay
- Guild News columns are now: Latest News, Poster, Date
- Sidebar is rebuilt with larger image tiles and better spacing.
- Packaged builds resolve assets/maps using the install folder so EXE builds can find maps and images.

## Build locally

```powershell
py -m PyInstaller --clean --noconfirm --windowed --name StankyTools `
  --hidden-import PySide6.QtWebEngineWidgets `
  --hidden-import PySide6.QtWebEngineCore `
  --collect-submodules PySide6.QtCore `
  --collect-submodules PySide6.QtGui `
  --collect-submodules PySide6.QtWidgets `
  --add-data "assets;assets" `
  --add-data "data;data" `
  main.py
```

Run only the EXE from `dist\StankyTools\StankyTools.exe`.
