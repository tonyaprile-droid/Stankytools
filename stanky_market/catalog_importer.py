from __future__ import annotations

import html.parser
import json
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import db

BASE_URL = "https://dune.gaming.tools"
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

# These are intentionally conservative. Listing/detail page fetches are delayed so the site is not hammered.
REQUEST_DELAY_SECONDS = 1.75
IMAGE_DELAY_SECONDS = 0.20
MAX_PAGINATION_PAGES = 40
MAX_EMPTY_PAGES = 2
USER_AGENT = "StankyToolsCatalogImporter/1.7 (+local user import; polite paced requests)"

# Import only the pages the user explicitly requested.
REQUESTED_IMPORT_PAGES = [
    ("/items/augment", "Augmentations"),
    ("/items/garment?tier=6", "Garments"),
    ("/items/utility", "Utility"),
    ("/items/vehicles", "Vehicles"),
    ("/items/weapons?tier=6", "Weapons"),
    ("/items/misc/components", "Components"),
    ("/items/misc/fuel", "Fuel"),
    ("/items/misc/rawresources", "Raw Resources"),
    ("/items/misc/refinedresources", "Refined Resources"),
]
SEED_PATHS = [path for path, _category in REQUESTED_IMPORT_PAGES]
PAGE_CATEGORY_MAP = {path.lower(): category for path, category in REQUESTED_IMPORT_PAGES}
PAGE_CATEGORY_MAP.update({urllib.parse.urljoin(BASE_URL, path).lower(): category for path, category in REQUESTED_IMPORT_PAGES})
KNOWN_CATEGORIES = ALLOWED_CATEGORIES

# Extra listing pages. The site often renders only the first visible batch on the
# main page. These subcategory URLs expose the rest of the category without
# hammering the server. Tier filters are preserved where the user requested Tier 6.
EXPANDED_LISTING_PAGES = [
    ("/items/augment/melee", "Augmentations"),
    ("/items/augment/ranged", "Augmentations"),
    ("/items/augment/garment", "Augmentations"),
    ("/items/augment/misc", "Augmentations"),
    ("/items/garment/heavy-armor?tier=6", "Garments"),
    ("/items/garment/light-armor?tier=6", "Garments"),
    ("/items/garment/stillsuits?tier=6", "Garments"),
    ("/items/utility/utility-tools", "Utility"),
    ("/items/utility/building-tools", "Utility"),
    ("/items/utility/cartography-tools", "Utility"),
    ("/items/utility/hydration-tools", "Utility"),
    ("/items/utility/gathering-tools", "Utility"),
    ("/items/utility/deployables", "Utility"),
    ("/items/utility/consumables", "Utility"),
    ("/items/vehicles/light-ornithopter", "Vehicles"),
    ("/items/vehicles/medium-ornithopter", "Vehicles"),
    ("/items/vehicles/four-man-groundcar", "Vehicles"),
    ("/items/vehicles/sandbike", "Vehicles"),
    ("/items/vehicles/buggy", "Vehicles"),
    ("/items/weapons/sidearms?tier=6", "Weapons"),
    ("/items/weapons/scatterguns?tier=6", "Weapons"),
    ("/items/weapons/heavy-weapons?tier=6", "Weapons"),
    ("/items/weapons/rifles?tier=6", "Weapons"),
    ("/items/weapons/long-blades?tier=6", "Weapons"),
    ("/items/weapons/short-blades?tier=6", "Weapons"),
    ("/items/weapons/ammunition?tier=6", "Weapons"),
]

ALL_IMPORT_PAGES = REQUESTED_IMPORT_PAGES + [p for p in EXPANDED_LISTING_PAGES if p not in REQUESTED_IMPORT_PAGES]

LISTING_PATH_KEYS = set()
for _path, _cat in ALL_IMPORT_PAGES:
    _parsed = urllib.parse.urlparse(urllib.parse.urljoin(BASE_URL, _path))
    LISTING_PATH_KEYS.add((_parsed.path.rstrip("/") + (f"?{_parsed.query}" if _parsed.query else "")).lower())
    LISTING_PATH_KEYS.add(_parsed.path.rstrip("/").lower())


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
        d = {k: v for k, v in attrs if k}
        if tag == "a" and d.get("href"):
            self._href = d.get("href")
            self._text = []
        elif tag == "img":
            src = _best_src_from_attrs(d)
            if src:
                self.images.append((src, d.get("alt", "") or ""))
        elif tag == "source":
            src = _best_src_from_attrs(d)
            if src:
                self.images.append((src, d.get("alt", "") or ""))
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


def _strip_url_fragment(url: str) -> str:
    parsed = urllib.parse.urlparse(_abs_url(url))
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, ""))


def _best_src_from_attrs(attrs: dict[str, str | None]) -> str:
    for key in ("src", "data-src", "data-original", "data-lazy-src", "data-nimg", "data-image"):
        value = attrs.get(key) or ""
        if value and not value.startswith("data:"):
            return value
    srcset = attrs.get("srcset") or attrs.get("data-srcset") or ""
    if srcset:
        # Use the largest candidate if widths are present, otherwise first URL.
        candidates: list[tuple[int, str]] = []
        for piece in srcset.split(","):
            parts = piece.strip().split()
            if not parts:
                continue
            url = parts[0]
            width = 0
            if len(parts) > 1 and parts[1].endswith("w"):
                try:
                    width = int(parts[1][:-1])
                except Exception:
                    width = 0
            candidates.append((width, url))
        if candidates:
            return sorted(candidates)[-1][1]
    return ""


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
    parsed = urllib.parse.urlparse(_abs_url(url))
    path_key = parsed.path.rstrip("/").lower()
    query = f"?{parsed.query}" if parsed.query else ""
    full_key = (path_key + query).lower()
    absolute_key = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", parsed.query, "")).lower()
    return PAGE_CATEGORY_MAP.get(full_key) or PAGE_CATEGORY_MAP.get(absolute_key) or MISC_CATEGORY_MAP.get(path_key, "")


def _listing_category_for_url(url: str) -> str:
    cat = _seed_category_for_url(url)
    return normalize_category(cat, "") if cat else ""


def _category_from_misc_path(url: str) -> str:
    parsed = urllib.parse.urlparse(_abs_url(url))
    path = parsed.path.rstrip("/").lower()
    for seed_path, category in MISC_CATEGORY_MAP.items():
        if path.startswith(seed_path + "/") or path == seed_path:
            return normalize_category(category)
    return ""


def _slug_to_name(slug: str) -> str:
    slug = slug.split("?")[0].strip("/").split("/")[-1]
    return re.sub(r"[-_]+", " ", slug).title().strip()


def _is_seed_listing_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(_abs_url(url))
    path_q = (parsed.path.rstrip("/") + (f"?{parsed.query}" if parsed.query else "")).lower()
    path_only = parsed.path.rstrip("/").lower()
    return path_q in LISTING_PATH_KEYS or path_only in LISTING_PATH_KEYS


def _is_item_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(_abs_url(url))
    if parsed.netloc and parsed.netloc != urllib.parse.urlparse(BASE_URL).netloc:
        return False
    path = parsed.path.strip("/")
    if not path.startswith("items/"):
        return False
    if _is_seed_listing_url(url):
        return False
    parts = path.split("/")
    if len(parts) < 2 or parts[1] in {"", "all"}:
        return False
    if parts[1].lower() == "misc":
        return bool(_category_from_misc_path(urllib.parse.urlunparse(parsed))) and len(parts) >= 4
    # Exclude broad category URLs; detail pages normally have a deeper or item slug path.
    if len(parts) == 2 and parts[1].lower() in {"augment", "garment", "utility", "vehicles", "weapons", "misc"}:
        return False
    return True


def _category_from_text(text: str) -> tuple[str, str, str]:
    item_type = "Schematic" if "schematic" in text.lower() else "Item"
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
    text = html_text[:800000]
    item_type = "Schematic" if re.search(r"schematic", text, flags=re.I) else "Item"
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
    for cat in sorted(KNOWN_CATEGORIES, key=len, reverse=True):
        idx = text.lower().find(cat.lower())
        if idx > 0:
            return _clean_text(text[:idx])
    text = re.sub(r"\bTier\s+\d+\b.*$", "", text, flags=re.I).strip()
    if text and len(text) <= 90 and not text.lower().startswith(("image:", "home", "database", "items")):
        return text
    return _slug_to_name(href)


def _skip_category(category: str) -> bool:
    return category.strip().lower() in IGNORE_CATEGORIES


def _fetch(url: str, retries: int = 2) -> str:
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
            with urllib.request.urlopen(req, timeout=35) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(charset, errors="replace")
        except Exception as exc:
            last = exc
            if attempt < retries:
                time.sleep(REQUEST_DELAY_SECONDS)
    raise last or RuntimeError("Fetch failed")


def _parse(html_text: str) -> _PageParser:
    p = _PageParser()
    p.feed(html_text)
    return p


def _extract_regex_links(html_text: str) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    # Capture anchors including text even if the HTML parser misses deeply nested rendered markup.
    for m in re.finditer(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html_text, flags=re.I | re.S):
        href = m.group(1)
        text = re.sub(r"<[^>]+>", " ", m.group(2))
        links.append((href, _clean_text(text)))
    # Capture item URLs embedded in JSON/script blobs.
    for m in re.finditer(r'["\'](\/items\/[a-zA-Z0-9_\-/]+(?:\?[^"\']*)?)["\']', html_text):
        href = m.group(1).replace("\\/", "/")
        links.append((href, _slug_to_name(href)))
    return links


def _extract_json_candidates(html_text: str, forced_category: str, base_url: str) -> list[CatalogCandidate]:
    """Best-effort extraction from client-rendered data chunks.

    This catches items that are not present as normal anchor text but are embedded in JSON.
    It intentionally keeps only records that contain an /items/ URL and a plausible name.
    """
    candidates: dict[str, CatalogCandidate] = {}
    text = html_text[:2_000_000]
    url_matches = list(re.finditer(r'"(?:href|url|path|slug|link)"\s*:\s*"([^"\\]*(?:\\/)?items(?:\\/|/)[^"\\]+)"', text, flags=re.I))
    for m in url_matches:
        raw_url = m.group(1).replace("\\/", "/")
        full = _strip_url_fragment(raw_url)
        if not _is_item_url(full):
            continue
        window = text[max(0, m.start() - 900): min(len(text), m.end() + 900)]
        name = ""
        for pat in (r'"name"\s*:\s*"([^"\\]{2,100})"', r'"title"\s*:\s*"([^"\\]{2,100})"'):
            nm = re.search(pat, window, flags=re.I)
            if nm:
                name = _clean_text(nm.group(1))
                break
        if not name:
            name = _slug_to_name(full)
        img = ""
        for pat in (r'"image"\s*:\s*"([^"\\]+)"', r'"icon"\s*:\s*"([^"\\]+)"', r'"src"\s*:\s*"([^"\\]+)"'):
            im = re.search(pat, window, flags=re.I)
            if im:
                img = im.group(1).replace("\\/", "/")
                break
        category = normalize_category(forced_category or _category_from_misc_path(full), "Utility")
        item_type = "Resource" if category in {"Raw Resources", "Refined Resources", "Fuel"} else "Item"
        candidates[full] = CatalogCandidate(name, category, "", item_type, full, _abs_url(img) if img else "")
    return list(candidates.values())


def _best_image(parser: _PageParser, item_name: str) -> str:
    for key in ("og:image", "twitter:image", "twitter:image:src"):
        if parser.meta.get(key):
            return _abs_url(parser.meta[key])
    lname = item_name.lower()
    for src, alt in parser.images:
        if alt and (lname in alt.lower() or alt.lower() in lname):
            return _abs_url(src)
    for src, _alt in parser.images:
        lower = src.lower()
        if src and not any(x in lower for x in ("logo", "discord", "ads", "avatar")):
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
    counter = 2
    while path.exists() and path.stat().st_size == 0:
        path.unlink(missing_ok=True)
    if path.exists() and path.stat().st_size > 0:
        return str(path)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"})
    with urllib.request.urlopen(req, timeout=35) as response:
        data = response.read()
        if not data:
            return ""
        path.write_bytes(data)
    time.sleep(IMAGE_DELAY_SECONDS)
    return str(path)


def _candidate_from_link(href: str, text: str, forced_category: str = "") -> CatalogCandidate | None:
    full = _strip_url_fragment(href)
    if not _is_item_url(full):
        return None
    category, subcategory, item_type = _category_from_text(text)
    misc_category = _category_from_misc_path(full)
    if misc_category:
        category = normalize_category(misc_category)
        subcategory = ""
        item_type = "Resource" if category in {"Raw Resources", "Refined Resources", "Fuel"} else item_type
    if forced_category:
        category = normalize_category(forced_category)
        subcategory = ""
        item_type = "Resource" if category in {"Raw Resources", "Refined Resources", "Fuel"} else item_type
    name = _name_from_link_text(text, href)
    if not name or name.lower() in {"items", "image: gaming.tools", "database"}:
        return None
    if category and _skip_category(category):
        return None
    category = normalize_category(category, "Utility") if category else "Utility"
    return CatalogCandidate(name=name, category=category, subcategory=subcategory, item_type=item_type, source_url=full)


def _pagination_url(seed_path: str, page_num: int) -> str:
    parsed = urllib.parse.urlparse(_abs_url(seed_path))
    q = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
    q["page"] = str(page_num)
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, urllib.parse.urlencode(q), ""))


def _same_listing_family(seed_url: str, href: str) -> bool:
    seed = urllib.parse.urlparse(_abs_url(seed_url))
    target = urllib.parse.urlparse(_abs_url(href))
    if target.netloc != seed.netloc or target.path.rstrip("/") != seed.path.rstrip("/"):
        return False
    q = dict(urllib.parse.parse_qsl(target.query))
    return any(k.lower() in {"page", "p", "offset"} for k in q) or q == dict(urllib.parse.parse_qsl(seed.query))


def _collect_listing_candidates(seed_path: str, category: str, progress: Callable[[str], None] | None, stats: dict[str, int]) -> dict[str, CatalogCandidate]:
    collected: dict[str, CatalogCandidate] = {}
    seen_listing_pages: set[str] = set()
    queue: list[str] = [_abs_url(seed_path)]
    forced_category = normalize_category(category)
    empty_pages = 0

    def log(msg: str):
        if progress:
            progress(msg)

    # Discover explicit pagination links and also probe ?page=N because some pages only expose a subset initially.
    for page_num in range(2, MAX_PAGINATION_PAGES + 1):
        queue.append(_pagination_url(seed_path, page_num))

    while queue:
        url = queue.pop(0)
        url = _strip_url_fragment(url)
        if url in seen_listing_pages:
            continue
        seen_listing_pages.add(url)
        before = len(collected)
        try:
            log(f"Reading {forced_category}: {url}")
            html_text = _fetch(url)
            stats["pages"] += 1
            parser = _parse(html_text)
            links = parser.links + _extract_regex_links(html_text)
            for href, text in links:
                if _same_listing_family(_abs_url(seed_path), href):
                    target = _strip_url_fragment(href)
                    if target not in seen_listing_pages and target not in queue:
                        queue.append(target)
                # If the page links to a subcategory listing in the same import category,
                # crawl that listing rather than treating it as an item.
                target_abs = _strip_url_fragment(href)
                if _is_seed_listing_url(target_abs):
                    if target_abs not in seen_listing_pages and target_abs not in queue:
                        queue.append(target_abs)
                    continue
                cand = _candidate_from_link(href, text, forced_category)
                if cand:
                    collected[cand.source_url] = cand
            for cand in _extract_json_candidates(html_text, forced_category, url):
                collected[cand.source_url] = cand
        except Exception as exc:
            stats["errors"] += 1
            log(f"Listing failed: {url} ({exc})")
        gained = len(collected) - before
        if "page=" in urllib.parse.urlparse(url).query:
            if gained <= 0:
                empty_pages += 1
                if empty_pages >= MAX_EMPTY_PAGES:
                    # Stop probing if consecutive pages add nothing. Explicit links already in the queue still ran first.
                    queue = [q for q in queue if "page=" not in urllib.parse.urlparse(q).query]
            else:
                empty_pages = 0
        log(f"Found {len(collected)} {forced_category} item links so far.")
        time.sleep(REQUEST_DELAY_SECONDS)
    return collected


def import_catalog(progress: Callable[[str], None] | None = None, max_items: int | None = None) -> dict[str, int]:
    """Import the requested Dune item pages politely on the user's machine.

    Improvements over earlier importers:
    - probes paginated listing pages so it does not stop at the first visible batch;
    - extracts anchors and embedded JSON/client data;
    - understands lazy-loaded image attributes and srcsets;
    - fetches detail pages for accurate names/images;
    - writes a report to data/catalog_import_report.json.
    """
    def log(msg: str):
        if progress:
            progress(msg)

    stats = {"pages": 0, "links": 0, "items": 0, "images": 0, "skipped": 0, "duplicates": 0, "errors": 0}
    failures: list[str] = []
    existing_names = {(row["name"].strip().lower(), row["category"].strip().lower()) for row in db.list_catalog()}
    item_urls: dict[str, CatalogCandidate] = {}

    for path, category in ALL_IMPORT_PAGES:
        try:
            found = _collect_listing_candidates(path, category, progress, stats)
            item_urls.update(found)
            stats["links"] = len(item_urls)
        except Exception as exc:
            stats["errors"] += 1
            failures.append(f"{path}: {exc}")

    log(f"Found {len(item_urls)} unique item links. Importing detail pages and images...")
    image_dir = db.DATA_DIR / "catalog_images"

    for n, (url, cand) in enumerate(list(item_urls.items()), start=1):
        if max_items is not None and stats["items"] >= max_items:
            break
        try:
            log(f"Importing {n}/{len(item_urls)}: {cand.name}")
            html_text = _fetch(url)
            parser = _parse(html_text)
            title = _clean_text(" ".join(parser.h1_parts)) or cand.name
            name = title if title and len(title) < 100 else cand.name
            cat2, sub2, type2 = _category_from_text(" ".join([_clean_text(" ".join(parser.title_parts)), title, cand.category]))
            cat3, sub3, type3 = _category_from_embedded_data(html_text) if not cat2 else ("", "", "")
            category = normalize_category(_category_from_misc_path(url) or cand.category or cat2 or cat3, "Utility")
            if (name.strip().lower(), category.strip().lower()) in existing_names:
                stats["duplicates"] += 1
                log(f"Skipping existing item: {name} ({category})")
                continue
            subcategory = sub2 or sub3 or cand.subcategory or ""
            item_type = type2 or type3 or cand.item_type or "Item"
            if category in {"Raw Resources", "Refined Resources", "Fuel"}:
                item_type = "Resource"
            if _skip_category(category):
                stats["skipped"] += 1
                continue
            image_url = cand.image_url or _best_image(parser, name)
            image_path = ""
            if image_url:
                try:
                    image_path = _download_image(image_url, name, image_dir)
                    if image_path:
                        stats["images"] += 1
                except Exception as exc:
                    failures.append(f"Image failed for {name}: {exc}")
                    log(f"Image failed for {name}: {exc}")
            db.upsert_catalog_item(name, category, subcategory, item_type, url, image_path)
            existing_names.add((name.strip().lower(), category.strip().lower()))
            stats["items"] += 1
        except Exception as exc:
            stats["errors"] += 1
            failures.append(f"Item failed {url}: {exc}")
            log(f"Item failed: {url} ({exc})")
        time.sleep(REQUEST_DELAY_SECONDS)

    report = {
        "stats": stats,
        "requested_pages": REQUESTED_IMPORT_PAGES,
        "expanded_listing_pages": EXPANDED_LISTING_PAGES,
        "unique_links_found": len(item_urls),
        "failures": failures[-200:],
    }
    try:
        db.DATA_DIR.mkdir(parents=True, exist_ok=True)
        (db.DATA_DIR / "catalog_import_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    except Exception:
        pass
    log(f"Done. Imported {stats['items']} new items, skipped {stats['duplicates']} duplicates, downloaded {stats['images']} images. Report saved in data/catalog_import_report.json")
    return stats
