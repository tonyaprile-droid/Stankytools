# RC1 Menu + Resource Patch

Changes included:

- Rebuilt the left navigation as large vertical icon tiles matching the approved UI direction.
- Added/copies dedicated `*_menu.png` icon assets for Dashboard, Market, Deep Desert, Hagga Basin, Guild, and Settings.
- Fixed resource paths so bundled assets and maps load from PyInstaller builds.
- Keeps runtime user data next to the EXE instead of inside bundled resources.
- Dashboard guild logo falls back to the placeholder when the user is not in a guild.
- GitHub Actions build command now bundles QtCore/QtGui/QtWidgets plus all assets/data.

Build locally with:

```powershell
py -m PyInstaller --clean --noconfirm --windowed --name StankyTools `
  --collect-submodules PySide6.QtCore `
  --collect-submodules PySide6.QtGui `
  --collect-submodules PySide6.QtWidgets `
  --add-data "assets;assets" `
  --add-data "data;data" `
  main.py
```

Run:

```powershell
.\dist\StankyTools\StankyTools.exe
```
