# Building and Releasing StankyTools

## Build locally for testing

```powershell
py -3.13 -m pip install -r requirements.txt
py -3.13 -m pip install pyinstaller
pyinstaller --clean --noconfirm --windowed --name StankyTools --add-data "assets;assets" --add-data "data\hagga_basin_map.png;data" --add-data "data\deep_desert_map.png;data" main.py
```

The portable app will be in:

```text
dist\StankyTools\StankyTools.exe
```

Zip the contents of `dist\StankyTools\` and send that ZIP to guild members.

## Build with GitHub Actions

Push to `main` or run **Actions → Build StankyTools → Run workflow**.

The workflow creates:

```text
StankyTools-Windows.zip
```

## Publish an update

1. Commit your changes.
2. Update `APP_VERSION` in `stanky_market/updater.py`.
3. Create a tag:

```powershell
git tag v2.0.1
git push origin v2.0.1
```

GitHub Actions will build and attach `StankyTools-Windows.zip` to the release.

## How the updater works

The app checks:

```text
https://api.github.com/repos/tonyaprile-droid/Stankytools/releases/latest
```

When a newer release exists and contains `StankyTools-Windows.zip`, the app downloads it, stages a Windows batch updater, closes StankyTools, copies the new files over the old app folder, and relaunches.

The updater preserves the app folder instead of deleting it, so local runtime files such as settings, cached images, logs, and SQLite data are not intentionally removed.

Important: automatic install works in the packaged EXE build. If you are running with `py main.py`, the app can check/download the update, but it cannot safely replace your source tree automatically.
