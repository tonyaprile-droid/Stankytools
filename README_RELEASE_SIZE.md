# Release size notes

The app was reporting `2.0.0-alpha.9` because `stanky_market/updater.py` still had an old `APP_VERSION` value. It is now set to `0.2.3`.

The portable EXE ZIP was very large because the old `StankyTools.spec` used:

```python
collect_all('PySide6')
```

That pulls in many Qt modules the app does not use. The new spec lets PyInstaller's hooks include the needed Qt runtime and explicitly keeps WebEngine for the live maps.

Build with:

```powershell
py -m pip install -r requirements.txt
py -m pip install pyinstaller
pyinstaller --clean --noconfirm StankyTools.spec
py tools/analyze_release_size.py dist\StankyTools
Compress-Archive -Path dist\StankyTools\* -DestinationPath StankyTools-Windows.zip -Force
```

Expected result: smaller than the prior 300 MB build. Qt WebEngine is still large, so a Windows portable ZIP may still be around 120-200 MB depending on PySide6.
