from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

APP_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = APP_DIR / "data"
DB_PATH = DATA_DIR / "stanky_market.sqlite3"

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
CATEGORY_NORMALIZATION = {
    "augment": "Augmentations",
    "augments": "Augmentations",
    "augmentation": "Augmentations",
    "augmentations": "Augmentations",
    "components": "Components",
    "component": "Components",
    "schematics": "Utility",
    "tools": "Utility",
    "modules": "Utility",
    "consumables": "Utility",
    "resources": "Raw Resources",
    "resource": "Raw Resources",
    "rawresources": "Raw Resources",
    "raw resources": "Raw Resources",
    "refinedresources": "Refined Resources",
    "refined resources": "Refined Resources",
    "weapon": "Weapons",
    "weapons": "Weapons",
    "garment": "Garments",
    "garments": "Garments",
    "vehicle": "Vehicles",
    "vehicles": "Vehicles",
    "fuel": "Fuel",
    "utility": "Utility",
    "utilities": "Utility",
}

def normalize_category(category: str) -> str:
    raw = (category or "").strip()
    if not raw:
        return "Utility"
    key = raw.lower().replace("-", " ").strip()
    compact = key.replace(" ", "")
    if key in CATEGORY_NORMALIZATION:
        return CATEGORY_NORMALIZATION[key]
    if compact in CATEGORY_NORMALIZATION:
        return CATEGORY_NORMALIZATION[compact]
    for allowed in ALLOWED_CATEGORIES:
        if key == allowed.lower() or allowed.lower() in key or key in allowed.lower():
            return allowed
    return "Utility"

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS catalog_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT DEFAULT '',
    item_type TEXT NOT NULL DEFAULT 'Item',
    source_url TEXT DEFAULT '',
    image_path TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, category, subcategory, item_type)
);

CREATE TABLE IF NOT EXISTS price_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    grade INTEGER,
    price INTEGER NOT NULL,
    observed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    note TEXT DEFAULT '',
    FOREIGN KEY(item_id) REFERENCES catalog_items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS deep_desert_pois (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    map_key TEXT NOT NULL DEFAULT 'deep_desert',
    x REAL NOT NULL,
    y REAL NOT NULL,
    label TEXT NOT NULL,
    note TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE VIEW IF NOT EXISTS market_summary AS
SELECT
    c.id AS item_id,
    c.name,
    c.category,
    c.subcategory,
    c.item_type,
    p.grade,
    MIN(p.price) AS low_price,
    ROUND(AVG(p.price)) AS avg_price,
    MAX(p.price) AS high_price,
    COUNT(p.id) AS seen_count,
    MAX(p.observed_at) AS last_seen
FROM catalog_items c
LEFT JOIN price_observations p ON p.item_id = c.id
GROUP BY c.id, p.grade;
"""

REFINED_RESOURCES = [
    "Aluminum Ingot",
    "Cobalt Paste",
    "Copper Ingot",
    "Duraluminum Ingot",
    "Iron Ingot",
    "Plastanium Ingot",
    "Plastone",
    "Silicone Block",
    "Spice Melange",
    "Steel Ingot",
    "Stravidium Fiber",
]


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    normalize_existing_categories(conn)
    seed_catalog(conn)
    return conn


def normalize_existing_categories(conn: sqlite3.Connection) -> None:
    rows = conn.execute("SELECT id, category FROM catalog_items").fetchall()
    changed = False
    for row in rows:
        normalized = normalize_category(row["category"])
        if normalized != row["category"]:
            conn.execute("UPDATE catalog_items SET category=?, subcategory='' WHERE id=?", (normalized, row["id"]))
            changed = True
    if changed:
        conn.commit()

def seed_catalog(conn: sqlite3.Connection) -> None:
    for name in REFINED_RESOURCES:
        conn.execute(
            """
            INSERT OR IGNORE INTO catalog_items
            (name, category, subcategory, item_type)
            VALUES (?, 'Refined Resources', '', 'Resource')
            """,
            (name,),
        )
    conn.commit()


def list_catalog(search: str = "", category: str = "") -> list[sqlite3.Row]:
    conn = connect()
    try:
        where = []
        params: list[str] = []
        if search.strip():
            where.append("name LIKE ?")
            params.append(f"%{search.strip()}%")
        if category.strip() and category.strip() != "All Categories":
            where.append("category = ?")
            params.append(category.strip())
        clause = ("WHERE " + " AND ".join(where)) if where else ""
        return conn.execute(
            f"SELECT * FROM catalog_items {clause} ORDER BY category, name",
            params,
        ).fetchall()
    finally:
        conn.close()


def catalog_categories() -> list[str]:
    conn = connect()
    try:
        existing = {row["category"] for row in conn.execute(
            "SELECT DISTINCT category FROM catalog_items WHERE category != ''"
        ).fetchall()}
        # Always expose only the approved category list, keeping a stable order.
        return [cat for cat in ALLOWED_CATEGORIES if cat in existing or cat in set(ALLOWED_CATEGORIES)]
    finally:
        conn.close()


def add_catalog_item(name: str, category: str, subcategory: str, item_type: str, source_url: str = "", image_path: str = "") -> int:
    name = name.strip()
    category = normalize_category(category.strip())
    item_type = item_type.strip() or "Item"
    if not name or not category:
        raise ValueError("Name and category are required.")
    conn = connect()
    try:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO catalog_items
            (name, category, subcategory, item_type, source_url, image_path)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, category, subcategory.strip(), item_type, source_url.strip(), image_path.strip()),
        )
        conn.commit()
        if cur.lastrowid:
            return int(cur.lastrowid)
        row = conn.execute(
            """
            SELECT id FROM catalog_items
            WHERE name=? AND category=? AND subcategory=? AND item_type=?
            """,
            (name, category, subcategory.strip(), item_type),
        ).fetchone()
        return int(row["id"])
    finally:
        conn.close()


def upsert_catalog_item(name: str, category: str, subcategory: str, item_type: str, source_url: str = "", image_path: str = "") -> int:
    """Insert a catalog item or update its URL/image if it already exists."""
    name = name.strip()
    category = category.strip()
    subcategory = subcategory.strip()
    item_type = item_type.strip() or "Item"
    if not name or not category:
        raise ValueError("Name and category are required.")
    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO catalog_items
            (name, category, subcategory, item_type, source_url, image_path)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(name, category, subcategory, item_type) DO UPDATE SET
                source_url = CASE WHEN excluded.source_url != '' THEN excluded.source_url ELSE catalog_items.source_url END,
                image_path = CASE WHEN excluded.image_path != '' THEN excluded.image_path ELSE catalog_items.image_path END
            """,
            (name, category, subcategory, item_type, source_url.strip(), image_path.strip()),
        )
        conn.commit()
        row = conn.execute(
            """
            SELECT id FROM catalog_items
            WHERE name=? AND category=? AND subcategory=? AND item_type=?
            """,
            (name, category, subcategory, item_type),
        ).fetchone()
        return int(row["id"])
    finally:
        conn.close()


def record_price(item_id: int, price: int, grade: int | None = None, note: str = "") -> None:
    if price <= 0:
        raise ValueError("Price must be greater than zero.")
    if grade is not None and not 0 <= grade <= 5:
        raise ValueError("Grade must be 0 through 5, or blank.")
    conn = connect()
    try:
        conn.execute(
            "INSERT INTO price_observations (item_id, grade, price, note) VALUES (?, ?, ?, ?)",
            (item_id, grade, price, note.strip()),
        )
        conn.commit()
    finally:
        conn.close()


def market_summary(search: str = "") -> list[sqlite3.Row]:
    conn = connect()
    try:
        if search.strip():
            q = f"%{search.strip()}%"
            return conn.execute(
                """
                SELECT * FROM market_summary
                WHERE name LIKE ? OR category LIKE ? OR item_type LIKE ?
                ORDER BY category, name, grade
                """,
                (q, q, q),
            ).fetchall()
        return conn.execute(
            "SELECT * FROM market_summary ORDER BY category, name, grade"
        ).fetchall()
    finally:
        conn.close()


def price_history(item_id: int) -> list[sqlite3.Row]:
    conn = connect()
    try:
        return conn.execute(
            """
            SELECT p.*, c.name FROM price_observations p
            JOIN catalog_items c ON c.id = p.item_id
            WHERE p.item_id=?
            ORDER BY p.observed_at DESC
            """,
            (item_id,),
        ).fetchall()
    finally:
        conn.close()


# Deep Desert POIs

def list_pois(map_key: str = "deep_desert") -> list[sqlite3.Row]:
    conn = connect()
    try:
        return conn.execute(
            "SELECT * FROM deep_desert_pois WHERE map_key=? ORDER BY created_at DESC, id DESC",
            (map_key,),
        ).fetchall()
    finally:
        conn.close()


def add_poi(x: float, y: float, label: str, note: str = "", map_key: str = "deep_desert") -> int:
    label = label.strip()
    if not label:
        raise ValueError("POI label is required.")
    conn = connect()
    try:
        cur = conn.execute(
            "INSERT INTO deep_desert_pois (map_key, x, y, label, note) VALUES (?, ?, ?, ?, ?)",
            (map_key, float(x), float(y), label, note.strip()),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def delete_poi(poi_id: int) -> None:
    conn = connect()
    try:
        conn.execute("DELETE FROM deep_desert_pois WHERE id=?", (int(poi_id),))
        conn.commit()
    finally:
        conn.close()
