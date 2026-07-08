from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None

try:
    from .paths import data_dir
except Exception:
    data_dir = None
APP_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = data_dir() if data_dir is not None else APP_DIR / "data"
MAP_DIR = DATA_DIR / "deep_desert"
META_PATH = MAP_DIR / "deep_desert_meta.json"
HTML_PATH = MAP_DIR / "deep_desert.html"
MAP_URL = "https://dune.gaming.tools/deep-desert"
USER_AGENT = "StankyToolsDeepDesertLiveLink/2.0 (+weekly-cache)"
EASTERN_TZ = "America/New_York"
WEEKLY_UPDATE_WEEKDAY = 1  # Tuesday, Monday=0
WEEKLY_UPDATE_HOUR = 7
WEEKLY_UPDATE_MINUTE = 30
PAGE_LOAD_DELAY_SECONDS = 5


def _eastern_now() -> datetime:
    """Return current Eastern time, safely on Windows/PyInstaller builds.

    Some frozen Windows builds do not include the IANA timezone database
    unless the optional `tzdata` package is bundled. If it is missing,
    ZoneInfo("America/New_York") raises ZoneInfoNotFoundError.
    The app should still launch, so fall back to local time.
    """
    if ZoneInfo is not None:
        try:
            return datetime.now(ZoneInfo(EASTERN_TZ)).replace(microsecond=0)
        except Exception:
            pass
    return datetime.now().replace(microsecond=0)


def _current_update_window(now: datetime | None = None) -> datetime:
    """Return the latest Tuesday 7:30 AM Eastern update window."""
    now = now or _eastern_now()
    days_since_tuesday = (now.weekday() - WEEKLY_UPDATE_WEEKDAY) % 7
    candidate = (now - timedelta(days=days_since_tuesday)).replace(
        hour=WEEKLY_UPDATE_HOUR,
        minute=WEEKLY_UPDATE_MINUTE,
        second=0,
        microsecond=0,
    )
    if candidate > now:
        candidate -= timedelta(days=7)
    return candidate


def next_tuesday_update(now: datetime | None = None) -> datetime:
    now = now or _eastern_now()
    days_ahead = (WEEKLY_UPDATE_WEEKDAY - now.weekday()) % 7
    candidate = (now + timedelta(days=days_ahead)).replace(
        hour=WEEKLY_UPDATE_HOUR,
        minute=WEEKLY_UPDATE_MINUTE,
        second=0,
        microsecond=0,
    )
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
            "last_update_window": "",
            "next_scheduled_update": next_tuesday_update().isoformat(sep=" "),
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
            "last_update_window": "",
            "next_scheduled_update": next_tuesday_update().isoformat(sep=" "),
        }


def save_meta(meta: dict[str, Any]) -> None:
    MAP_DIR.mkdir(parents=True, exist_ok=True)
    META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def _fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=45) as response:
        return response.read()


def _find_image_url(html: str) -> str:
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
    return ".png"


def _looks_like_valid_image(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 25_000:
        return False
    try:
        from PIL import Image
        with Image.open(path) as img:
            width, height = img.size
            return width >= 500 and height >= 500
    except Exception:
        # If Pillow is unavailable, file size is the fallback validation.
        return path.stat().st_size >= 75_000


def _download_candidate_map(html: str, old_image_path: str) -> tuple[str, str]:
    image_url = _find_image_url(html)
    if not image_url:
        return "", old_image_path
    image_bytes = _fetch(image_url)
    ext = _extension_from_url(image_url)
    img_path = MAP_DIR / f"deep_desert_map{ext}"
    tmp_path = MAP_DIR / f"deep_desert_map.tmp{ext}"
    tmp_path.write_bytes(image_bytes)
    if _looks_like_valid_image(tmp_path):
        tmp_path.replace(img_path)
        return image_url, str(img_path)
    try:
        tmp_path.unlink(missing_ok=True)
    except Exception:
        pass
    return image_url, old_image_path


def check_for_update(force: bool = False) -> dict[str, Any]:
    """Update the cached Deep Desert map using Tuesday 7:15 AM Eastern rules.

    Behavior:
    - Uses the cached map immediately unless a weekly check is due.
    - Reads the website only after the Tuesday 7:15 AM ET update window, once per week.
    - Waits five seconds before reading the website so the source page has time to settle.
    - Keeps the last known good map if the new map is incomplete or unavailable.
    """
    MAP_DIR.mkdir(parents=True, exist_ok=True)
    old = load_meta()
    now = _eastern_now()
    update_window = _current_update_window(now)
    update_key = update_window.isoformat(sep=" ")
    image_path = old.get("image_path", "")
    cached_exists = bool(image_path and Path(image_path).exists())
    already_checked_this_window = old.get("last_update_window") == update_key

    if not force and cached_exists and already_checked_this_window:
        meta = dict(old)
        meta.update({
            "source_url": MAP_URL,
            "skipped": True,
            "skip_reason": "Cached map already checked for this Tuesday 7:30 AM ET update window.",
            "next_scheduled_update": next_tuesday_update(now).isoformat(sep=" "),
        })
        save_meta(meta)
        return meta

    # Let the app finish opening and give the map website time to complete its own load.
    time.sleep(PAGE_LOAD_DELAY_SECONDS)

    html_bytes = _fetch(MAP_URL)
    content_hash = hashlib.sha256(html_bytes).hexdigest()
    html = html_bytes.decode("utf-8", errors="replace")
    HTML_PATH.write_text(html, encoding="utf-8")

    changed = content_hash != old.get("content_hash", "")
    checked = now.isoformat(sep=" ")
    image_url = old.get("image_url", "")
    new_image_path = image_path

    try:
        found_url, candidate_path = _download_candidate_map(html, image_path)
        if found_url:
            image_url = found_url
        if candidate_path:
            new_image_path = candidate_path
    except Exception:
        # Keep last good cached map.
        new_image_path = image_path

    meta = {
        "source_url": MAP_URL,
        "last_checked": checked,
        "last_changed": checked if changed else old.get("last_changed", "Never"),
        "content_hash": content_hash,
        "image_url": image_url,
        "image_path": new_image_path,
        "html_path": str(HTML_PATH),
        "changed": changed,
        "skipped": False,
        "last_update_window": update_key,
        "next_scheduled_update": next_tuesday_update(now).isoformat(sep=" "),
        "update_rule": "Tuesday 7:30 AM Eastern",
    }
    save_meta(meta)
    return meta


def map_image_path() -> Path:
    """Return the canonical cached Deep Desert screenshot path used by the native canvas."""
    return data_dir() / "deep_desert_map.png" if data_dir is not None else DATA_DIR / "deep_desert_map.png"

def should_auto_screenshot(now: datetime | None = None) -> bool:
    """True when the weekly Tuesday 7:30 AM ET map screenshot is due.

    The app checks this on Deep Desert page creation/startup. It only returns
    true after the current weekly reset window and only when the cached map has
    not already been captured for that window.
    """
    now = now or _eastern_now()
    update_window = _current_update_window(now)
    if now < update_window:
        return False
    meta = load_meta()
    image_path = str(meta.get("image_path") or map_image_path())
    cached_exists = bool(image_path and Path(image_path).exists())
    return (not cached_exists) or meta.get("last_update_window") != update_window.isoformat(sep=" ")

def save_screenshot_meta(image_path: str, force: bool = False) -> dict[str, Any]:
    """Record metadata after the app captures a live web screenshot."""
    now = _eastern_now()
    update_window = _current_update_window(now)
    old = load_meta()
    path = Path(image_path)
    content_hash = ""
    try:
        content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        content_hash = old.get("content_hash", "")
    meta = {
        "source_url": MAP_URL,
        "last_checked": now.isoformat(sep=" "),
        "last_changed": now.isoformat(sep=" "),
        "content_hash": content_hash,
        "image_url": "",
        "image_path": str(path),
        "html_path": str(HTML_PATH),
        "changed": content_hash != old.get("content_hash", ""),
        "skipped": False,
        "capture_method": "QtWebEngine screenshot after 5 second wait",
        "last_update_window": update_window.isoformat(sep=" "),
        "next_scheduled_update": next_tuesday_update(now).isoformat(sep=" "),
        "update_rule": "Tuesday 7:30 AM Eastern",
    }
    save_meta(meta)
    return meta
