# StankyTools v1.0 RC2.27

Cumulative Dune Data Engine integration update.

- Fully integrates Gizmo3030/Dune-Awakening-API data without requiring users to run FastAPI/Uvicorn.
- Import Dune Data checks a local running API if present, then local cloned items_data.json, then raw GitHub items_data.json, then local cache.
- Catalog details open inside StankyTools and show description, power, crafting materials, and deep desert materials.
- No separate API server is required for normal users.
