from __future__ import annotations

import html.parser
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from . import db

BASE_URL = "https://dune.gaming.tools"
ITEMS_URL = f"{BASE_URL}/items"
TIER6_URL = f"{BASE_URL}/items?tier=6"
ALLOWED_CATEGORIES = [
    "Refined Resources",
    "Raw Resources",
    "Augmentations",
    "Components",
    "Utility",
    "Vehicles",
    "Weapons",
    "Garments",
    "Fuel",
]
ALLOWED_CATEGORY_SET = {c.lower(): c for c in ALLOWED_CATEGORIES}
IGNORE_CATEGORIES = {"misc", "customization", "construction"}
# Misc is not imported as a top-level category, but specific misc subpages below are allowed.
# There is intentionally no Components category in Stanky Market; components-page items are
# grouped under Utility so the catalog only uses the eight approved categories.
MISC_CATEGORY_MAP = {
    "/items/misc/components": "Components",
    "/items/misc/fuel": "Fuel",
    "/items/misc/rawresources": "Raw Resources",
    "/items/misc/refinedresources": "Refined Resources",
}
CATEGORY_ALIASES = {
    "augment": "Augmentations",
    "augments": "Augmentations",
    "augmentation": "Augmentations",
    "augmentations": "Augmentations",
    "utilities": "Utility",
    "utility": "Utility",
    "weapon": "Weapons",
    "weapons": "Weapons",
    "garment": "Garments",
    "garments": "Garments",
    "vehicle": "Vehicles",
    "vehicles": "Vehicles",
    "fuel": "Fuel",
    "raw resource": "Raw Resources",
    "raw resources": "Raw Resources",
    "rawresources": "Raw Resources",
    "refined resource": "Refined Resources",
    "refined resources": "Refined Resources",
    "refinedresources": "Refined Resources",
    "resource": "Raw Resources",
    "resources": "Raw Resources",
    "components": "Components",
    "component": "Components",
    "schematics": "Utility",
    "tools": "Utility",
    "modules": "Utility",
    "consumables": "Utility",
}
REQUEST_DELAY_SECONDS = 1.15
USER_AGENT = "StankyMarketCatalogImporter/1.0 (+local user import; polite delay)"

# Seed known listing/filter pages. The crawler also follows item links discovered from these.
SEED_PATHS = [
    "/items",
    "/items?tier=6",
    "/items/misc/components",
    "/items/misc/fuel",
    "/items/misc/rawresources",
    "/items/misc/refinedresources",
    "/items/weapons",
    "/items/weapons?rarity=Unique",
    "/items/garments",
    "/items/utility",
    "/items/augment",
    "/items/resources",
    "/items/refined-resources",
    "/items/raw-resources",
    "/items/consumables",
    "/items/vehicles",
    "/items/components",
    "/items/schematics",
]

KNOWN_CATEGORIES = ALLOWED_CATEGORIES


@dataclass(frozen=True)
class CatalogCandidate:
    name: str
    category: str
    subcategory: str = ""
    item_type: str = "Item"
    source_url: str = ""
    image_url: str = ""


class _PageParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self.images: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []
        self.title_parts: list[str] = []
        self._in_title = False
        self.h1_parts: list[str] = []
        self._in_h1 = False
        self.meta: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs):
        d = dict(attrs)
        if tag == "a" and d.get("href"):
            self._href = d.get("href")
            self._text = []
        elif tag == "img" and d.get("src"):
            self.images.append((d.get("src", ""), d.get("alt", "")))
        elif tag == "title":
            self._in_title = True
        elif tag == "h1":
            self._in_h1 = True
        elif tag == "meta":
            key = d.get("property") or d.get("name") or ""
            value = d.get("content") or ""
            if key and value:
                self.meta[key.lower()] = value

    def handle_endtag(self, tag: str):
        if tag == "a" and self._href is not None:
            text = _clean_text(" ".join(self._text))
            self.links.append((self._href, text))
            self._href = None
            self._text = []
        elif tag == "title":
            self._in_title = False
        elif tag == "h1":
            self._in_h1 = False

    def handle_data(self, data: str):
        if self._href is not None:
            self._text.append(data)
        if self._in_title:
            self.title_parts.append(data)
        if self._in_h1:
            self.h1_parts.append(data)


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _abs_url(url: str) -> str:
    return urllib.parse.urljoin(BASE_URL, url)


def normalize_category(category: str, fallback: str = "Utility") -> str:
    raw = _clean_text(category)
    if not raw:
        return fallback
    key = raw.lower().replace("-", " ").strip()
    key_compact = key.replace(" ", "")
    if key in ALLOWED_CATEGORY_SET:
        return ALLOWED_CATEGORY_SET[key]
    if key in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[key]
    if key_compact in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[key_compact]
    for allowed in ALLOWED_CATEGORIES:
        if allowed.lower() in key or key in allowed.lower():
            return allowed
    return fallback

def _seed_category_for_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    key = parsed.path.rstrip("/").lower()
    return MISC_CATEGORY_MAP.get(key, "")


def _category_from_misc_path(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    path = parsed.path.rstrip("/").lower()
    for seed_path, category in MISC_CATEGORY_MAP.items():
        if path.startswith(seed_path + "/") or path == seed_path:
            return normalize_category(category)
    return ""


def _slug_to_name(slug: str) -> str:
    slug = slug.split("?")[0].strip("/").split("/")[-1]
    return re.sub(r"[-_]+", " ", slug).title().strip()


def _is_item_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc and parsed.netloc != urllib.parse.urlparse(BASE_URL).netloc:
        return False
    path = parsed.path.strip("/")
    if not path.startswith("items/"):
        return False
    parts = path.split("/")
    if len(parts) < 2 or parts[1] in {"", "all"}:
        return False
    # Allow whitelisted misc subcategory item pages only. Do not import generic /items/misc.
    if parts[1].lower() == "misc":
        return bool(_category_from_misc_path(urllib.parse.urlunparse(parsed))) and len(parts) >= 4
    # /items/<slug> is either an item or a category. Category pages are handled by text/category checks.
    return True


def _category_from_text(text: str) -> tuple[str, str, str]:
    """Parse listing text like 'Adept Kindjal Weapons - Short Blades Tier 5'."""
    item_type = "Item"
    if "schematic" in text.lower():
        item_type = "Schematic"
    for cat in sorted(KNOWN_CATEGORIES, key=len, reverse=True):
        m = re.search(rf"\b{re.escape(cat)}\b", text, flags=re.I)
        if m:
            rest = text[m.end():]
            sub = ""
            sub_match = re.search(r"-\s*([^\n]+?)(?:\s+Tier\b|\s+Unique\b|\s+Common\b|\s+Uncommon\b|\s+Rare\b|$)", rest, flags=re.I)
            if sub_match:
                sub = _clean_text(sub_match.group(1))
            return normalize_category(cat), sub, item_type
    return "", "", item_type


def _category_from_embedded_data(html_text: str) -> tuple[str, str, str]:
    """Best-effort category extraction from app/JSON data on detail pages."""
    text = html_text[:500000]
    item_type = "Schematic" if re.search(r"schematic", text, flags=re.I) else "Item"
    # Common shapes used by client-rendered pages. This is intentionally broad but harmless.
    patterns = [
        r'"category"\s*:\s*"([^"\\]+)"',
        r'"categoryName"\s*:\s*"([^"\\]+)"',
        r'"itemCategory"\s*:\s*"([^"\\]+)"',
        r'"category"\s*:\s*\{[^{}]*"name"\s*:\s*"([^"\\]+)"',
    ]
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.I)
        if m:
            raw = _clean_text(m.group(1))
            for cat in KNOWN_CATEGORIES:
                if raw.lower() == cat.lower() or cat.lower() in raw.lower():
                    return normalize_category(cat), "", item_type
            if raw and raw.strip().lower() not in IGNORE_CATEGORIES:
                return normalize_category(raw), "", item_type
    return "", "", item_type


def _name_from_link_text(text: str, href: str) -> str:
    text = _clean_text(text)
    # Remove category and trailing metadata from known listing labels.
    for cat in sorted(KNOWN_CATEGORIES, key=len, reverse=True):
        idx = text.lower().find(cat.lower())
        if idx > 0:
            return _clean_text(text[:idx])
    if text and len(text) <= 90 and not text.lower().startswith(("image:", "home", "database")):
        return text
    return _slug_to_name(href)


def _skip_category(category: str) -> bool:
    return category.strip().lower() in IGNORE_CATEGORIES


def _fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=25) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def _parse(html_text: str) -> _PageParser:
    p = _PageParser()
    p.feed(html_text)
    return p


def _best_image(parser: _PageParser, item_name: str) -> str:
    # Prefer social/image metadata, then images whose alt resembles the item name.
    for key in ("og:image", "twitter:image"):
        if parser.meta.get(key):
            return _abs_url(parser.meta[key])
    lname = item_name.lower()
    for src, alt in parser.images:
        if alt and (lname in alt.lower() or alt.lower() in lname):
            return _abs_url(src)
    for src, alt in parser.images:
        if src and not any(x in src.lower() for x in ("logo", "discord", "ads")):
            return _abs_url(src)
    return ""


def _download_image(url: str, item_name: str, dest_dir: Path) -> str:
    if not url:
        return ""
    dest_dir.mkdir(parents=True, exist_ok=True)
    parsed = urllib.parse.urlparse(url)
    suffix = Path(parsed.path).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        suffix = ".webp"
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", item_name).strip("_")[:80] or "item"
    path = dest_dir / f"{safe}{suffix}"
    if path.exists() and path.stat().st_size > 0:
        return str(path)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as response:
        path.write_bytes(response.read())
    return str(path)


def _candidate_from_link(href: str, text: str) -> CatalogCandidate | None:
    full = _abs_url(href)
    if not _is_item_url(full):
        return None
    category, subcategory, item_type = _category_from_text(text)
    misc_category = _category_from_misc_path(full)
    if misc_category:
        category = normalize_category(misc_category)
        subcategory = ""
        item_type = "Resource" if category in {"Raw Resources", "Refined Resources", "Fuel"} else item_type
    name = _name_from_link_text(text, href)
    if not name or name.lower() in {"items", "image: gaming.tools"}:
        return None
    if category and _skip_category(category):
        return None
    # Some filtered pages such as /items?tier=6 may render item cards with limited text.
    # Keep the candidate and let the detail page fill the category; fall back to Tier 6 only if needed.
    category = normalize_category(category, "Utility") if category else "Utility"
    return CatalogCandidate(name=name, category=category, subcategory=subcategory, item_type=item_type, source_url=full)


def import_catalog(progress: Callable[[str], None] | None = None, max_items: int | None = None) -> dict[str, int]:
    """Import Dune item catalog politely on the user's machine.

    The importer intentionally sleeps between page requests to avoid hammering the website.
    It skips Misc, Customization, and Construction categories.
    """
    def log(msg: str):
        if progress:
            progress(msg)

    seen_pages: set[str] = set()
    item_urls: dict[str, CatalogCandidate] = {}
    stats = {"pages": 0, "items": 0, "images": 0, "skipped": 0, "duplicates": 0, "errors": 0}
    existing_names = {row["name"].strip().lower() for row in db.list_catalog()}

    # First pass: fetch listing/filter pages and collect item links.
    for path in SEED_PATHS:
        url = _abs_url(path)
        if url in seen_pages:
            continue
        try:
            log(f"Fetching listing: {url}")
            html_text = _fetch(url)
            seen_pages.add(url)
            stats["pages"] += 1
            parser = _parse(html_text)
            seed_category = normalize_category(_seed_category_for_url(url), "") if _seed_category_for_url(url) else ""
            for href, text in parser.links:
                cand = _candidate_from_link(href, text)
                if cand:
                    if seed_category:
                        item_type = "Resource" if seed_category in {"Raw Resources", "Refined Resources", "Fuel"} else cand.item_type
                        cand = CatalogCandidate(cand.name, seed_category, cand.subcategory, item_type, cand.source_url, cand.image_url)
                    item_urls[cand.source_url] = cand
        except Exception as exc:
            stats["errors"] += 1
            log(f"Listing failed: {url} ({exc})")
        time.sleep(REQUEST_DELAY_SECONDS)

    log(f"Found {len(item_urls)} item links before detail import.")
    image_dir = db.DATA_DIR / "catalog_images"

    # Second pass: fetch detail pages for images and better metadata.
    for n, (url, cand) in enumerate(list(item_urls.items()), start=1):
        if max_items is not None and stats["items"] >= max_items:
            break
        try:
            log(f"Importing {n}/{len(item_urls)}: {cand.name}")
            html_text = _fetch(url)
            parser = _parse(html_text)
            title = _clean_text(" ".join(parser.h1_parts)) or cand.name
            if title and len(title) < 90:
                name = title
            else:
                name = cand.name
            if name.strip().lower() in existing_names:
                stats["duplicates"] += 1
                log(f"Skipping existing item: {name}")
                continue
            # Keep listing-derived category unless detail text or embedded data clearly includes a known one.
            detail_text = " ".join([_clean_text(" ".join(parser.title_parts)), title, cand.category])
            cat2, sub2, type2 = _category_from_text(detail_text)
            if not cat2 or cat2 == "Tier 6":
                cat3, sub3, type3 = _category_from_embedded_data(html_text)
            else:
                cat3, sub3, type3 = "", "", ""
            category = normalize_category(_category_from_misc_path(url) or cat2 or cat3 or cand.category, "Utility")
            subcategory = ""
            item_type = type2 or type3 or cand.item_type
            if category in {"Raw Resources", "Refined Resources", "Fuel"}:
                item_type = "Resource"
            if _skip_category(category):
                stats["skipped"] += 1
                continue
            image_url = _best_image(parser, name)
            image_path = ""
            if image_url:
                try:
                    image_path = _download_image(image_url, name, image_dir)
                    if image_path:
                        stats["images"] += 1
                except Exception as exc:
                    log(f"Image failed for {name}: {exc}")
            db.upsert_catalog_item(name, category, subcategory, item_type, url, image_path)
            existing_names.add(name.strip().lower())
            stats["items"] += 1
        except Exception as exc:
            stats["errors"] += 1
            log(f"Item failed: {url} ({exc})")
        time.sleep(REQUEST_DELAY_SECONDS)

    log(f"Done. Imported {stats['items']} new items, skipped {stats['duplicates']} duplicates, downloaded {stats['images']} images.")
    return stats
