# RC1 UI / Resource Patch

This patch implements the generated dashboard direction in code without generating another image.

Included:
- Sidebar converted to large icon tiles with artwork above text.
- Large menu artwork cropped from existing Dune-style card assets and saved as `assets/icons/*_menu.png`.
- Resource loading now uses `stanky_market.paths` so assets and maps resolve correctly in source and PyInstaller builds.
- Deep Desert map uses `data/deep_desert_map.png` through `data_dir()`.
- Hagga Basin map uses `data/hagga_basin_map.png` through `data_dir()`.
- Dashboard guild logo area enlarged further and no logo border.
- GitHub Actions PyInstaller build updated to bundle Qt modules and the full `assets/` and `data/` folders.
- `.gitignore` updated to avoid shipping local SQLite/user cache.

After applying, build locally with:

```powershell
py -m PyInstaller --clean --noconfirm --windowed --name StankyTools `
  --collect-submodules PySide6.QtCore `
  --collect-submodules PySide6.QtGui `
  --collect-submodules PySide6.QtWidgets `
  --add-data "assets;assets" `
  --add-data "data;data" `
  main.py
```

Then run:

```powershell
.\dist\StankyTools\StankyTools.exe
```
