# StankyTools v1.0 RC2.28

## Awakening Wiki Data Engine

This build removes the old Gizmo3030/FastAPI sample API integration and replaces it with a standalone Awakening Wiki data engine.

Users do not need to install Python packages, clone another repository, run FastAPI, run Uvicorn, or start a local server.

Catalog update now pulls from:

- https://api.awakening.wiki/items/
- https://api.awakening.wiki/ammo/
- https://api.awakening.wiki/consumables/
- https://api.awakening.wiki/contract_items/
- https://api.awakening.wiki/garments/
- https://api.awakening.wiki/resources/
- https://api.awakening.wiki/tools/
- https://api.awakening.wiki/vehicles/
- https://api.awakening.wiki/weapons/

The results are normalized into the local SQLite catalog and cached for offline item details.

## Cleanup

Removed the embedded Dune-Awakening-API folder and its .git/database/sample files from the shipped app.

## Version

1.0.0-rc2.28
