# StankyTools Release Build

Use this package as the source of truth for guild releases.

## Build the EXE

1. Commit and push to GitHub.
2. Go to **Actions → Build StankyTools**.
3. Download the `StankyTools-Windows` artifact.

## Publish a release for the updater

The in-app updater only downloads the release asset named:

```text
StankyTools-Windows.zip
```

To publish a release automatically:

```powershell
git tag v2.0.0-alpha.1
git push origin v2.0.0-alpha.1
```

GitHub Actions will build the app and attach `StankyTools-Windows.zip` to the release.

## Important

The release ZIP intentionally does **not** include:

- `data/stanky_market.sqlite3`
- `*.sqlite3`
- `*.db`
- user logs
- update staging files

That prevents updates from kicking users out of their guilds or overwriting local settings.

The app stores user data next to the EXE in:

```text
data/stanky_market.sqlite3
logs/
updates/
```

The updater preserves those folders.
