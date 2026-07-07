from __future__ import annotations

"""Game8 catalog importer for StankyTools.

Imports the Dune: Awakening resource table from Game8. The table columns are:
Resource, Type, Details. In StankyTools the Game8 Type column is used directly
as the catalog category, per app owner request.
"""

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
from .paths import data_dir, local_app_data_dir

GAME8_RESOURCES_URL = "https://game8.co/games/Dune-Awakening/archives/524002"
USER_AGENT = "StankyToolsGame8Importer/1.0 (+local catalog import)"
REQUEST_TIMEOUT = 25
DETAIL_DELAY_SECONDS = 0.08


@dataclass
class Game8Resource:
    name: str
    category: str
    description: str
    source_url: str = ""
    image_url: str = ""


def _clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def _abs_url(url: str) -> str:
    return urllib.parse.urljoin(GAME8_RESOURCES_URL, url or "")


def _fetch_bytes(url: str, timeout: int = REQUEST_TIMEOUT) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def _fetch_text(url: str, timeout: int = REQUEST_TIMEOUT) -> str:
    payload = _fetch_bytes(url, timeout=timeout)
    return payload.decode("utf-8", errors="replace")


def _best_src_from_attrs(attrs: dict[str, str]) -> str:
    for key in ("src", "data-src", "data-original", "data-lazy-src", "data-img", "data-image"):
        value = attrs.get(key) or ""
        if value and not value.startswith("data:"):
            return value
    srcset = attrs.get("srcset") or attrs.get("data-srcset") or ""
    if srcset:
        choices: list[tuple[int, str]] = []
        for piece in srcset.split(","):
            parts = piece.strip().split()
            if not parts:
                continue
            width = 0
            if len(parts) > 1 and parts[1].endswith("w"):
                try:
                    width = int(parts[1][:-1])
                except Exception:
                    width = 0
            choices.append((width, parts[0]))
        if choices:
            return sorted(choices)[-1][1]
    return ""


class _ResourceTableParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows: list[Game8Resource] = []
        self._in_tr = False
        self._in_cell = False
        self._cell_text: list[str] = []
        self._cells: list[str] = []
        self._cell_links: list[str] = []
        self._cell_images: list[str] = []
        self._row_links: list[str] = []
        self._row_images: list[str] = []
        self._href: str | None = None

    def handle_starttag(self, tag: str, attrs):
        d = {k: (v or "") for k, v in attrs if k}
        if tag == "tr":
            self._in_tr = True
            self._cells = []
            self._row_links = []
            self._row_images = []
        elif self._in_tr and tag in {"td", "th"}:
            self._in_cell = True
            self._cell_text = []
            self._cell_links = []
            self._cell_images = []
        elif self._in_tr and tag == "a" and d.get("href"):
            self._href = d.get("href")
            self._row_links.append(_abs_url(self._href))
            if self._in_cell:
                self._cell_links.append(_abs_url(self._href))
        elif self._in_tr and tag in {"img", "source"}:
            src = _best_src_from_attrs(d)
            if src:
                src = _abs_url(src)
                self._row_images.append(src)
                if self._in_cell:
                    self._cell_images.append(src)

    def handle_endtag(self, tag: str):
        if tag in {"td", "th"} and self._in_cell:
            self._cells.append(_clean(" ".join(self._cell_text)))
            self._in_cell = False
        elif tag == "a":
            self._href = None
        elif tag == "tr" and self._in_tr:
            self._finish_row()
            self._in_tr = False

    def handle_data(self, data: str):
        if self._in_cell:
            self._cell_text.append(data)

    def _finish_row(self):
        if len(self._cells) < 3:
            return
        name, category, description = (self._cells[0], self._cells[1], self._cells[2])
        if not name or name.lower() in {"resource", "resources"}:
            return
        if not category or category.lower() == "type":
            return
        if not description or description.lower() in {"details", "description"}:
            return
        # Game8 table contains exactly Resource / Type / Details; ignore unrelated tables.
        known_types = {"raw", "refined", "component", "misc", "currency"}
        if category.strip().lower() not in known_types:
            return
        source_url = self._row_links[0] if self._row_links else GAME8_RESOURCES_URL
        image_url = self._row_images[0] if self._row_images else ""
        self.rows.append(Game8Resource(name=name, category=category, description=description, source_url=source_url, image_url=image_url))


class _DetailImageParser(html.parser.HTMLParser):
    def __init__(self, item_name: str):
        super().__init__(convert_charrefs=True)
        self.item_name = item_name.lower()
        self.meta_images: list[str] = []
        self.named_images: list[str] = []
        self.any_images: list[str] = []

    def handle_starttag(self, tag: str, attrs):
        d = {k: (v or "") for k, v in attrs if k}
        if tag == "meta":
            key = (d.get("property") or d.get("name") or "").lower()
            if key in {"og:image", "twitter:image", "twitter:image:src"} and d.get("content"):
                self.meta_images.append(_abs_url(d["content"]))
        elif tag in {"img", "source"}:
            src = _best_src_from_attrs(d)
            if not src:
                return
            src = _abs_url(src)
            alt = (d.get("alt") or "").lower()
            self.any_images.append(src)
            if self.item_name and self.item_name in alt:
                self.named_images.append(src)

    def best(self) -> str:
        for collection in (self.named_images, self.meta_images, self.any_images):
            for url in collection:
                if url and not url.startswith("data:"):
                    return url
        return ""


def parse_resources(html: str) -> list[Game8Resource]:
    parser = _ResourceTableParser()
    parser.feed(html)
    # Deduplicate by name/category while preserving order.
    seen: set[tuple[str, str]] = set()
    out: list[Game8Resource] = []
    for item in parser.rows:
        key = (item.name.lower(), item.category.lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _sanitize_filename(name: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip()).strip("._")
    return safe[:120] or "item"


def _extension_from_url(url: str) -> str:
    path = urllib.parse.urlparse(url).path.lower()
    for ext in (".webp", ".png", ".jpg", ".jpeg", ".gif"):
        if path.endswith(ext):
            return ext
    return ".webp"


def _discover_detail_image(item: Game8Resource) -> str:
    if item.image_url:
        return item.image_url
    if not item.source_url or item.source_url == GAME8_RESOURCES_URL:
        return ""
    try:
        html = _fetch_text(item.source_url, timeout=REQUEST_TIMEOUT)
        parser = _DetailImageParser(item.name)
        parser.feed(html)
        return parser.best()
    except Exception:
        return ""


def _download_image(item: Game8Resource, image_url: str) -> str:
    if not image_url:
        return ""
    folder = local_app_data_dir() / "item_images" / "game8"
    folder.mkdir(parents=True, exist_ok=True)
    ext = _extension_from_url(image_url)
    target = folder / f"{_sanitize_filename(item.name)}{ext}"
    if target.exists() and target.stat().st_size > 128:
        return str(target)
    try:
        payload = _fetch_bytes(image_url, timeout=REQUEST_TIMEOUT)
        if len(payload) > 128:
            target.write_bytes(payload)
            return str(target)
    except Exception:
        return ""
    return ""


def import_game8_resources(progress: Callable[[str], None] | None = None, clear_existing: bool = True, include_images: bool = True) -> dict:
    progress = progress or (lambda _m: None)
    progress("Downloading Game8 resource table...")
    html = _fetch_text(GAME8_RESOURCES_URL)
    resources = parse_resources(html)
    if not resources:
        raise RuntimeError("No resources were found on the Game8 resource table.")

    if clear_existing:
        progress("Clearing existing local catalog...")
        db.clear_local_catalog(skip_seed=True)

    imported = 0
    images = 0
    errors: list[str] = []
    total = len(resources)
    for idx, item in enumerate(resources, start=1):
        progress(f"Importing {idx}/{total}: {item.name}")
        image_path = ""
        if include_images:
            try:
                image_url = _discover_detail_image(item)
                if image_url:
                    image_path = _download_image(item, image_url)
                    if image_path:
                        images += 1
                time.sleep(DETAIL_DELAY_SECONDS)
            except Exception as exc:
                errors.append(f"{item.name} image: {exc}")
        try:
            db.upsert_catalog_item(
                item.name,
                item.category,
                "",
                "Resource",
                item.source_url,
                image_path,
                description=item.description,
            )
            imported += 1
        except TypeError:
            # Older db.py fallback if description has not been added yet.
            db.upsert_catalog_item(item.name, item.category, "", "Resource", item.source_url, image_path)
            imported += 1
        except Exception as exc:
            errors.append(f"{item.name}: {exc}")

    db.set_setting("catalog_imported_once", "1")
    db.set_setting("catalog_force_github_reimport", "")
    db.set_setting("catalog_source", "Game8 Resources")
    db.set_setting("catalog_last_import_count", str(imported))
    db.set_setting("catalog_last_import_at", str(int(time.time())))

    report = {
        "source": "Game8 Resources",
        "url": GAME8_RESOURCES_URL,
        "items": imported,
        "images": images,
        "errors": errors,
        "updated_at": int(time.time()),
    }
    try:
        (data_dir() / "catalog_import_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    except Exception:
        pass
    return report
