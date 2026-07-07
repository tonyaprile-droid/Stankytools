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

GAME8_BASE = "https://game8.co"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) StankyToolsGame8Importer/1.0"
REQUEST_DELAY_SECONDS = 0.75
IMAGE_DELAY_SECONDS = 0.15

# Game8 pages requested by the user. Category is the StankyTools top-level category.
# Type column is preserved as subcategory, except the resources page where Type maps to category.
GAME8_IMPORT_PAGES = [
    {
        "url": "https://game8.co/games/Dune-Awakening/archives/524002",
        "label": "Resources",
        "category": "",
        "type_is_category": True,
    },
    {
        "url": "https://game8.co/games/Dune-Awakening/archives/523574",
        "label": "Unique Weapons",
        "category": "Weapons",
        "type_is_subcategory": True,
    },
    {
        "url": "https://game8.co/games/Dune-Awakening/archives/527260",
        "label": "Unique Garments",
        "category": "Garments",
        "type_is_subcategory": True,
    },
    {
        "url": "https://game8.co/games/Dune-Awakening/archives/527383",
        "label": "Unique Vehicle Parts",
        "category": "Vehicles",
        "type_is_subcategory": True,
    },
    {
        "url": "https://game8.co/games/Dune-Awakening/archives/527032",
        "label": "Unique Tools",
        "category": "Tools",
        "type_is_subcategory": True,
    },
    {
        "url": "https://game8.co/games/Dune-Awakening/archives/523472",
        "label": "Armor",
        "category": "Garments",
        "type_is_subcategory": True,
    },
]

@dataclass
class Cell:
    text: str = ""
    images: list[tuple[str, str]] | None = None

    def __post_init__(self):
        if self.images is None:
            self.images = []

class Game8TableParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[Cell]]] = []
        self._in_table = False
        self._in_row = False
        self._in_cell = False
        self._current_table: list[list[Cell]] = []
        self._current_row: list[Cell] = []
        self._current_cell: Cell | None = None
        self._link_href: str | None = None
        self._cell_text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs):
        attrs_d = {k: v for k, v in attrs if k}
        if tag == "table":
            self._in_table = True
            self._current_table = []
        elif self._in_table and tag == "tr":
            self._in_row = True
            self._current_row = []
        elif self._in_row and tag in {"td", "th"}:
            self._in_cell = True
            self._current_cell = Cell()
            self._cell_text_parts = []
        elif self._in_cell and tag == "a" and attrs_d.get("href"):
            self._link_href = attrs_d.get("href")
        elif self._in_cell and tag == "img":
            src = _best_src(attrs_d)
            alt = attrs_d.get("alt") or ""
            if src and self._current_cell is not None:
                self._current_cell.images.append((src, alt))
        elif self._in_cell and tag == "source":
            src = _best_src(attrs_d)
            if src and self._current_cell is not None:
                self._current_cell.images.append((src, ""))

    def handle_endtag(self, tag: str):
        if tag == "a":
            self._link_href = None
        elif self._in_cell and tag in {"td", "th"}:
            if self._current_cell is not None:
                self._current_cell.text = _clean(" ".join(self._cell_text_parts))
                self._current_row.append(self._current_cell)
            self._current_cell = None
            self._in_cell = False
            self._cell_text_parts = []
        elif self._in_row and tag == "tr":
            if self._current_row:
                self._current_table.append(self._current_row)
            self._current_row = []
            self._in_row = False
        elif self._in_table and tag == "table":
            if self._current_table:
                self.tables.append(self._current_table)
            self._current_table = []
            self._in_table = False

    def handle_data(self, data: str):
        if self._in_cell:
            self._cell_text_parts.append(data)


def _clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    # Game8 sometimes appends image alt/title into the text. Keep it readable.
    return text.replace("\u3000", " ").strip()


def _best_src(attrs: dict[str, str | None]) -> str:
    for key in ("data-src", "data-original", "data-lazy-src", "src"):
        value = attrs.get(key) or ""
        if value and not value.startswith("data:"):
            return value
    srcset = attrs.get("srcset") or attrs.get("data-srcset") or ""
    if srcset:
        candidates = []
        for piece in srcset.split(","):
            parts = piece.strip().split()
            if not parts:
                continue
            width = 0
            if len(parts) > 1 and parts[1].endswith("w"):
                try:
                    width = int(parts[1][:-1])
                except Exception:
                    pass
            candidates.append((width, parts[0]))
        if candidates:
            return sorted(candidates)[-1][1]
    return ""


def _fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=35) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _abs_url(url: str) -> str:
    return urllib.parse.urljoin(GAME8_BASE, url)


def _safe_filename(name: str, suffix: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip()).strip("._-") or "item"
    return stem[:90] + suffix.lower()


def _download_image(image_url: str, name: str, out_dir: Path) -> str:
    if not image_url:
        return ""
    url = _abs_url(image_url)
    parsed = urllib.parse.urlparse(url)
    suffix = Path(parsed.path).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        suffix = ".png"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / _safe_filename(name, suffix)
    if out_path.exists() and out_path.stat().st_size > 0:
        return str(out_path)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Referer": GAME8_BASE})
    with urllib.request.urlopen(req, timeout=45) as resp:
        data = resp.read()
    if len(data) < 100:
        return ""
    out_path.write_bytes(data)
    time.sleep(IMAGE_DELAY_SECONDS)
    return str(out_path)


def _norm_header(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")


def _category_from_type(type_text: str) -> str:
    raw = _clean(type_text)
    key = raw.lower()
    if "refined" in key:
        return "Refined Resources"
    if "raw" in key:
        return "Raw Resources"
    if "component" in key:
        return "Components"
    if "weapon" in key:
        return "Weapons"
    if "garment" in key or "armor" in key:
        return "Garments"
    if "vehicle" in key:
        return "Vehicles"
    if "tool" in key:
        return "Tools"
    return db.normalize_category(raw)


def _pick_first_image(row: list[Cell]) -> str:
    for cell in row:
        for src, _alt in cell.images or []:
            if src:
                return src
    return ""


def _cell(row: list[Cell], idx: int) -> str:
    if idx < 0 or idx >= len(row):
        return ""
    return _clean(row[idx].text)


def _best_name_from_cell(cell: Cell) -> str:
    text = _clean(cell.text)
    # Prefer alt text if the text is missing or generic.
    if (not text or len(text) < 2 or text.lower() in {"image", "icon"}) and cell.images:
        for _src, alt in cell.images:
            if _clean(alt):
                return _clean(alt)
    return text


def _parse_page(page: dict, progress: Callable[[str], None] | None, image_dir: Path) -> dict[str, int]:
    def log(msg: str):
        if progress:
            progress(msg)

    url = page["url"]
    html = _fetch(url)
    parser = Game8TableParser()
    parser.feed(html)
    stats = {"items": 0, "images": 0, "tables": len(parser.tables), "errors": 0}

    best_table = None
    best_headers = None
    for table in parser.tables:
        if len(table) < 2:
            continue
        headers = [_norm_header(c.text) for c in table[0]]
        score = 0
        for h in headers:
            if h in {"resource", "resources", "name", "item", "weapon", "garment", "armor", "vehicle_part", "tool"}:
                score += 3
            if h in {"type", "category"}:
                score += 2
            if h in {"description", "details", "effect", "location", "how_to_get"}:
                score += 1
        if score > 0 and (best_table is None or score > sum(1 for h in best_headers or [] if h)):
            best_table = table
            best_headers = headers
            if score >= 4:
                break
    if best_table is None:
        log(f"No usable table found on {page['label']}.")
        return stats

    headers = best_headers or [_norm_header(c.text) for c in best_table[0]]
    def find(*names: str) -> int:
        for name in names:
            n = _norm_header(name)
            if n in headers:
                return headers.index(n)
        for i, h in enumerate(headers):
            for name in names:
                if _norm_header(name) in h or h in _norm_header(name):
                    return i
        return -1

    name_idx = find("Resource", "Name", "Item", "Weapon", "Garment", "Armor", "Vehicle Part", "Tool")
    type_idx = find("Type", "Category")
    desc_idx = find("Description", "Details", "Effect", "How to Get", "Location")
    if name_idx < 0:
        name_idx = 0

    for row in best_table[1:]:
        if not row or len(row) <= name_idx:
            continue
        name = _best_name_from_cell(row[name_idx])
        if not name or name.lower() in {"resource", "name", "item", "weapon", "armor", "tool"}:
            continue
        # Strip common Game8 duplicate snippets.
        name = re.sub(r"\s+(Image|Icon)$", "", name, flags=re.I).strip()
        type_text = _cell(row, type_idx) if type_idx >= 0 else ""
        if page.get("type_is_category"):
            category = _category_from_type(type_text)
            subcategory = ""
        else:
            category = page.get("category") or _category_from_type(type_text)
            subcategory = type_text
        if category == "Utility" and page.get("category"):
            category = page["category"]
        description = _cell(row, desc_idx) if desc_idx >= 0 else ""
        if not description:
            # Preserve remaining useful cells as description if there is no direct description column.
            extras = []
            for i, c in enumerate(row):
                if i not in {name_idx, type_idx}:
                    t = _clean(c.text)
                    if t and t != name:
                        extras.append(t)
            description = " | ".join(extras[:4])
        image_url = _pick_first_image(row)
        image_path = ""
        if image_url:
            try:
                image_path = _download_image(image_url, name, image_dir)
                if image_path:
                    stats["images"] += 1
            except Exception as exc:
                stats["errors"] += 1
                log(f"Image failed for {name}: {exc}")
        item_type = "Resource" if category in {"Raw Resources", "Refined Resources", "Components", "Fuel"} else category.rstrip("s") or "Item"
        try:
            db.upsert_catalog_item(name, category, subcategory, item_type, url, image_path, description, "Game8")
            stats["items"] += 1
        except Exception as exc:
            stats["errors"] += 1
            log(f"Import failed for {name}: {exc}")
    return stats


def import_catalog(progress: Callable[[str], None] | None = None, max_items: int | None = None) -> dict[str, int]:
    """Import catalog data from Game8 only.

    Game8 is now the only catalog provider. GitHub/Gizmo/Awakening API import paths
    were intentionally removed so stale fallback records cannot reappear.
    """
    def log(msg: str):
        if progress:
            progress(msg)

    log("Clearing old local catalog before Game8 import...")
    db.clear_local_catalog(skip_seed=True)
    image_dir = db.DATA_DIR / "catalog_images"
    total = {"items": 0, "images": 0, "pages": 0, "errors": 0}
    page_reports = []
    for page in GAME8_IMPORT_PAGES:
        try:
            log(f"Importing Game8 {page['label']}...")
            stats = _parse_page(page, progress, image_dir)
            total["items"] += stats.get("items", 0)
            total["images"] += stats.get("images", 0)
            total["errors"] += stats.get("errors", 0)
            total["pages"] += 1
            page_reports.append({"page": page, "stats": stats})
        except Exception as exc:
            total["errors"] += 1
            page_reports.append({"page": page, "error": str(exc)})
            log(f"Game8 import failed for {page['label']}: {exc}")
        time.sleep(REQUEST_DELAY_SECONDS)
    db.set_setting("catalog_imported_once", "1")
    db.set_setting("catalog_force_github_reimport", "1")
    db.set_setting("catalog_source", "Game8")
    report = {"source": "Game8", "total": total, "pages": page_reports}
    try:
        db.DATA_DIR.mkdir(parents=True, exist_ok=True)
        (db.DATA_DIR / "catalog_import_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    except Exception:
        pass
    if total["items"] <= 0:
        raise RuntimeError("Game8 import completed but no items were found. Check your internet connection or Game8 page layout.")
    log(f"Done. Imported {total['items']} Game8 items and {total['images']} images.")
    return total
