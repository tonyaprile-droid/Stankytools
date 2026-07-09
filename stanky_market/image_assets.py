from __future__ import annotations

import re
import threading
import urllib.request
from pathlib import Path
from typing import Iterable

from . import db
from .paths import local_app_data_dir

GITHUB_IMAGE_BASE_URL = "https://raw.githubusercontent.com/StankylegTools/stanky-tools-assets/main/items"
CATALOG_IMAGE_DIR = local_app_data_dir() / "item_images"
_IMAGE_EXTS = (".webp", ".png", ".jpg", ".jpeg")


def safe_item_filename(name: str, ext: str = ".webp") -> str:
    """Return the catalog image filename used by the GitHub assets repo."""
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", str(name or "")).strip("_")
    return f"{cleaned or 'item'}{ext}"


def catalog_cache_path(name: str, image_path: str = "") -> Path:
    """Resolve the best local cache path for a catalog item image."""
    raw = str(image_path or "").strip().replace("\\", "/")
    filename = Path(raw).name if raw else safe_item_filename(name)
    if not filename:
        filename = safe_item_filename(name)
    return CATALOG_IMAGE_DIR / filename


def github_image_url(name: str, image_path: str = "") -> str:
    """Build the raw GitHub URL for a catalog item image."""
    filename = catalog_cache_path(name, image_path).name
    from urllib.parse import quote
    return f"{GITHUB_IMAGE_BASE_URL}/{quote(filename)}"


def ensure_catalog_image(name: str, image_path: str = "", timeout: int = 8) -> Path | None:
    """Download one catalog image from GitHub if it is missing locally."""
    target = catalog_cache_path(name, image_path)
    if target.exists() and target.stat().st_size > 0:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    url = github_image_url(name, image_path)
    tmp = target.with_suffix(target.suffix + ".tmp")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "StankyTools/2"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
        if len(data) < 32:
            return None
        tmp.write_bytes(data)
        tmp.replace(target)
        return target
    except Exception:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass
        return None


def normalize_catalog_image_paths() -> None:
    """Make DB image paths portable and pointed at the local GitHub-backed cache."""
    rows = db.list_catalog("", "")
    changed = []
    for row in rows:
        name = row["name"] if "name" in row.keys() else ""
        image_path = row["image_path"] if "image_path" in row.keys() else ""
        target = catalog_cache_path(name, image_path)
        portable = f"item_images/{target.name}"
        if str(image_path or "").replace("\\", "/") != portable:
            changed.append((portable, int(row["id"])))
    if not changed:
        return
    with db.connect() as conn:
        conn.executemany("UPDATE catalog_items SET image_path=? WHERE id=?", changed)


def _iter_catalog_rows(limit: int | None = None) -> Iterable[tuple[str, str]]:
    rows = db.list_catalog("", "")
    count = 0
    for row in rows:
        name = row["name"] if "name" in row.keys() else ""
        image_path = row["image_path"] if "image_path" in row.keys() else ""
        if not name:
            continue
        yield name, image_path
        count += 1
        if limit is not None and count >= limit:
            return


def import_missing_catalog_images_async(limit: int | None = None) -> threading.Thread:
    """Import missing item images from GitHub in the background during app launch."""
    def worker() -> None:
        try:
            normalize_catalog_image_paths()
            for name, image_path in _iter_catalog_rows(limit):
                ensure_catalog_image(name, image_path)
        except Exception:
            pass

    thread = threading.Thread(target=worker, name="CatalogImageImporter", daemon=True)
    thread.start()
    return thread

