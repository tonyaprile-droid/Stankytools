# Private Source / Public Release Workflow

Use this setup when the StankyTools source repository is private but the compiled Windows app should be publicly downloadable and auto-updatable.

## Repository layout

- Keep the source repository private.
- Create a separate public repository: `StankylegTools/StankyTools-Releases`.
- Do not put source code in the public repository.
- Use the public repository only for GitHub Releases and compiled release assets.

GitHub will still show automatic source archive links for the public releases repo, but that repository should contain no private source. The app updater ignores source archive URLs and selects only Windows installer/portable assets.

## Required secret in the private source repo

Create a fine-grained GitHub token that can write releases in `StankylegTools/StankyTools-Releases`, then save it in the private source repository as:

`PUBLIC_RELEASES_TOKEN`

The build workflow uses that token only when a version tag is pushed.

## Release asset names

Preferred updater-compatible names:

- `StankyTools-Setup-vX.X.X.exe`
- `StankyTools-Portable-vX.X.X.zip`

The current workflow builds and uploads:

`StankyTools-Portable-vX.X.X.zip`

Do not tell users to download source code ZIPs or TAR files.

## Release process

1. Update `APP_VERSION` in `stanky_market/updater.py`.
2. Commit changes in the private source repository.
3. Tag the release, for example `v1.0.2`.
4. Push the tag.
5. Confirm the workflow publishes only compiled assets to `StankylegTools/StankyTools-Releases`.
6. Confirm the app Settings page "Check For App Update" sees the public release.

## Extra public assets

If catalog images or optional video assets are needed by public users, attach them to the public releases repo as release assets too:

- `catalog_images.zip`
- `pgmayo.mp4`


