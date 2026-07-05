from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

APP_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = APP_DIR / "data"
MAP_DIR = DATA_DIR / "deep_desert"
META_PATH = MAP_DIR / "deep_desert_meta.json"
HTML_PATH = MAP_DIR / "deep_desert.html"
MAP_URL = "https://dune.gaming.tools/deep-desert"
USER_AGENT = "StankyMarketDeepDesertUpdater/1.0 (+manual update only)"


def _now_local() -> datetime:
    return datetime.now().replace(microsecond=0)


def next_tuesday_midnight(now: datetime | None = None) -> datetime:
    now = now or _now_local()
    # Monday=0, Tuesday=1
    days_ahead = (1 - now.weekday()) % 7
    candidate = (now + timedelta(days=days_ahead)).replace(hour=0, minute=0, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=7)
    return candidate


def load_meta() -> dict[str, Any]:
    if not META_PATH.exists():
        return {
            "source_url": MAP_URL,
            "last_checked": "Never",
            "last_changed": "Never",
            "content_hash": "",
            "image_url": "",
            "image_path": "",
        }
    try:
        return json.loads(META_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {
            "source_url": MAP_URL,
            "last_checked": "Never",
            "last_changed": "Never",
            "content_hash": "",
            "image_url": "",
            "image_path": "",
        }


def save_meta(meta: dict[str, Any]) -> None:
    MAP_DIR.mkdir(parents=True, exist_ok=True)
    META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def _fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read()


def _find_image_url(html: str) -> str:
    # Prefer social preview images, then first likely map/image asset.
    patterns = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<img[^>]+src=["\']([^"\']+)["\'][^>]*(?:map|deep|desert)',
        r'<img[^>]+(?:map|deep|desert)[^>]+src=["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        m = re.search(pattern, html, flags=re.IGNORECASE)
        if m:
            return urllib.parse.urljoin(MAP_URL, m.group(1))
    return ""


def _extension_from_url(url: str) -> str:
    path = urllib.parse.urlparse(url).path.lower()
    for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        if path.endswith(ext):
            return ext
    return ".img"


def check_for_update() -> dict[str, Any]:
    """Fetch the Deep Desert page only when the user manually requests an update."""
    MAP_DIR.mkdir(parents=True, exist_ok=True)
    old = load_meta()
    html_bytes = _fetch(MAP_URL)
    content_hash = hashlib.sha256(html_bytes).hexdigest()
    html = html_bytes.decode("utf-8", errors="replace")
    HTML_PATH.write_text(html, encoding="utf-8")

    changed = content_hash != old.get("content_hash", "")
    checked = _now_local().isoformat(sep=" ")
    image_url = _find_image_url(html)
    image_path = old.get("image_path", "")

    if image_url and (changed or image_url != old.get("image_url", "") or not image_path or not Path(image_path).exists()):
        try:
            image_bytes = _fetch(image_url)
            ext = _extension_from_url(image_url)
            img_path = MAP_DIR / f"deep_desert_map{ext}"
            img_path.write_bytes(image_bytes)
            image_path = str(img_path)
        except Exception:
            # Keep HTML cache even if image extraction fails.
            image_path = old.get("image_path", "")

    meta = {
        "source_url": MAP_URL,
        "last_checked": checked,
        "last_changed": checked if changed else old.get("last_changed", "Never"),
        "content_hash": content_hash,
        "image_url": image_url or old.get("image_url", ""),
        "image_path": image_path,
        "html_path": str(HTML_PATH),
        "changed": changed,
        "next_scheduled_update": next_tuesday_midnight().isoformat(sep=" "),
    }
    save_meta(meta)
    return meta
