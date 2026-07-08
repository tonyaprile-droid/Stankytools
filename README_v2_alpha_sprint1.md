# StankyTools v2 Alpha Sprint 1

This build starts the release-quality polish work from the current project ZIP.

## Changes in this sprint

- Catalog page now shows item thumbnails instead of the Source column.
- Double-click an item image to open a larger preview.
- Double-click an item name/category to open the source item page if available.
- Added a default item placeholder image for missing catalog art.
- Added quick Maintenance buttons for opening the local Data and Logs folders.
- Preserved the existing guild, POI, Hagga Basin, updater, import worker, and map features from the uploaded project.

## Files changed

- `stanky_market/app.py`
- `assets/icons/default_item.png`

## Notes

This is intentionally a small, safe sprint so we do not regress the working guild/map features. The next sprint should focus on the updater workflow and logging.
