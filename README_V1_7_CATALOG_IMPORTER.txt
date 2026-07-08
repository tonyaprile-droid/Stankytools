StankyTools v1.7 Catalog Importer Update

Included:
- Keeps all v1.6 changes.
- Catalog import remains on a background thread so the app does not freeze.
- Importer now probes paginated listing pages instead of stopping at first visible batch.
- Importer extracts item links from anchors and embedded JSON/client data.
- Importer supports lazy images, data-src, data-srcset/srcset, og:image, and detail-page images.
- Importer writes data/catalog_import_report.json with stats and failures.
- Requests remain politely paced; listing/detail requests wait 1.75 seconds.
- Dashboard guild logo is larger.
- Settings includes a View Members / Roles button.

Use Catalog > Import Dune Item Database.
