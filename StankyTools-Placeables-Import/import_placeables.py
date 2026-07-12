from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path


def main() -> int:
    package_dir = Path(__file__).resolve().parent
    repo_root = Path.cwd()

    if not (repo_root / "stanky_market").exists():
        print("ERROR: Run this script from the StankyTools repository root.")
        print(r"Example: cd C:\Users\tonya\Documents\GitHub\Stankytools")
        print("Then run: py import_placeables.py")
        return 1

    sys.path.insert(0, str(repo_root))

    from stanky_market import db
    from stanky_market.paths import local_app_data_dir

    records = json.loads((package_dir / "placeables.json").read_text(encoding="utf-8"))
    source_images = package_dir / "item_images"
    destination_images = local_app_data_dir() / "item_images"
    destination_images.mkdir(parents=True, exist_ok=True)

    added_or_updated = 0
    copied_images = 0

    for record in records:
        filename = record["image_filename"]
        source = source_images / filename
        destination = destination_images / filename

        if source.exists():
            shutil.copy2(source, destination)
            copied_images += 1

        image_path = f"item_images/{filename}"
        db.upsert_catalog_item(
            name=record["name"],
            category=record["category"],
            subcategory=record["subcategory"],
            item_type=record["item_type"],
            source_url="User-provided placeables screenshots, 2026-07-10",
            image_path=image_path,
        )
        added_or_updated += 1

    print(f"Imported or updated {added_or_updated} catalog items.")
    print(f"Copied {copied_images} item images to: {destination_images}")
    print("Open StankyTools and use Reload Catalog, or restart the app.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
