from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from .paths import data_dir

APP_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = data_dir()
DB_PATH = DATA_DIR / "stanky_market.sqlite3"

ALLOWED_CATEGORIES = [
    "Raw Resources",
    "Refined Resources",
    "Components",
    "Weapons",
    "Garments",
    "Vehicles",
    "Tools",
    "Utility",
    "Fuel",
]
CATEGORY_NORMALIZATION = {
    "augment": "Augmentations",
    "augments": "Augmentations",
    "augmentation": "Augmentations",
    "augmentations": "Augmentations",
    "components": "Components",
    "component": "Components",
    "unique vehicle parts": "Vehicles",
    "vehicle parts": "Vehicles",
    "vehicle part": "Vehicles",
    "schematics": "Utility",
    "tool": "Tools",
    "tools": "Tools",
    "unique tools": "Tools",
    "modules": "Utility",
    "consumables": "Utility",
    "resources": "Raw Resources",
    "resource": "Raw Resources",
    "raw": "Raw Resources",
    "raw resource": "Raw Resources",
    "raw resources": "Raw Resources",
    "refined": "Refined Resources",
    "refined resource": "Refined Resources",
    "refined resources": "Refined Resources",
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
    description TEXT DEFAULT '',
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

CREATE TABLE IF NOT EXISTS guild_bases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    map_key TEXT NOT NULL DEFAULT 'hagga_basin',
    x REAL NOT NULL,
    y REAL NOT NULL,
    base_name TEXT NOT NULL DEFAULT 'Guild Base',
    seitch TEXT NOT NULL DEFAULT '',
    guild_code TEXT DEFAULT '',
    created_by TEXT DEFAULT '',
    remote_id TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'friendly',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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

REFINED_RESOURCES: list[str] = []


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
    # If the user deleted the local catalog, do not silently reseed default rows.
    # This keeps Catalog truly empty until they import from GitHub/API again.
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT DEFAULT '')")
        row = conn.execute("SELECT value FROM app_settings WHERE key='catalog_force_github_reimport'").fetchone()
        if row and str(row[0]) == "1":
            return
    except Exception:
        pass
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


def upsert_catalog_item(name: str, category: str, subcategory: str, item_type: str, source_url: str = "", image_path: str = "", description: str = "", import_source: str = "") -> int:
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
            (name, category, subcategory, item_type, source_url, image_path, description, import_source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name, category, subcategory, item_type) DO UPDATE SET
                source_url = CASE WHEN excluded.source_url != '' THEN excluded.source_url ELSE catalog_items.source_url END,
                image_path = CASE WHEN excluded.image_path != '' THEN excluded.image_path ELSE catalog_items.image_path END,
                description = CASE WHEN excluded.description != '' THEN excluded.description ELSE catalog_items.description END,
                import_source = CASE WHEN excluded.import_source != '' THEN excluded.import_source ELSE catalog_items.import_source END
            """,
            (name, category, subcategory, item_type, source_url.strip(), image_path.strip(), description.strip(), import_source.strip()),
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


def dashboard_stats() -> dict:
    conn = connect()
    try:
        catalog_items = conn.execute("SELECT COUNT(*) AS n FROM catalog_items").fetchone()["n"]
        observed_items = conn.execute("SELECT COUNT(DISTINCT item_id) AS n FROM price_observations").fetchone()["n"]
        observations = conn.execute("SELECT COUNT(*) AS n FROM price_observations").fetchone()["n"]
        pois = conn.execute("SELECT COUNT(*) AS n FROM deep_desert_pois").fetchone()["n"]
        return {
            "catalog_items": catalog_items,
            "observed_items": observed_items,
            "observations": observations,
            "pois": pois,
        }
    finally:
        conn.close()


def category_progress() -> list[sqlite3.Row]:
    conn = connect()
    try:
        return conn.execute(
            """
            SELECT
                c.category,
                COUNT(DISTINCT c.id) AS total,
                COUNT(DISTINCT p.item_id) AS observed
            FROM catalog_items c
            LEFT JOIN price_observations p ON p.item_id = c.id
            GROUP BY c.category
            ORDER BY c.category
            """
        ).fetchall()
    finally:
        conn.close()


def recent_observations(limit: int = 10) -> list[sqlite3.Row]:
    conn = connect()
    try:
        return conn.execute(
            """
            SELECT c.name, p.price, p.observed_at
            FROM price_observations p
            JOIN catalog_items c ON c.id = p.item_id
            ORDER BY p.observed_at DESC, p.id DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
    finally:
        conn.close()

# App Settings and lightweight guild sync support

def _ensure_runtime_columns(conn: sqlite3.Connection) -> None:
    # Add columns safely for existing local databases.
    try:
        catalog_cols = {row['name'] for row in conn.execute("PRAGMA table_info(catalog_items)").fetchall()}
        if 'description' not in catalog_cols:
            conn.execute("ALTER TABLE catalog_items ADD COLUMN description TEXT DEFAULT ''")
        if 'import_source' not in catalog_cols:
            conn.execute("ALTER TABLE catalog_items ADD COLUMN import_source TEXT DEFAULT ''")
    except Exception:
        pass
    try:
        poi_cols = {row['name'] for row in conn.execute("PRAGMA table_info(deep_desert_pois)").fetchall()}
        if 'guild_code' not in poi_cols:
            conn.execute("ALTER TABLE deep_desert_pois ADD COLUMN guild_code TEXT DEFAULT ''")
        if 'remote_id' not in poi_cols:
            conn.execute("ALTER TABLE deep_desert_pois ADD COLUMN remote_id TEXT DEFAULT ''")
        if 'updated_at' not in poi_cols:
            conn.execute("ALTER TABLE deep_desert_pois ADD COLUMN updated_at TEXT DEFAULT CURRENT_TIMESTAMP")
        if 'poi_type' not in poi_cols:
            conn.execute("ALTER TABLE deep_desert_pois ADD COLUMN poi_type TEXT DEFAULT 'Custom'")
        if 'created_by' not in poi_cols:
            conn.execute("ALTER TABLE deep_desert_pois ADD COLUMN created_by TEXT DEFAULT ''")
        if 'last_updated_by' not in poi_cols:
            conn.execute("ALTER TABLE deep_desert_pois ADD COLUMN last_updated_by TEXT DEFAULT ''")
        if 'pooped_on' not in poi_cols:
            conn.execute("ALTER TABLE deep_desert_pois ADD COLUMN pooped_on INTEGER NOT NULL DEFAULT 0")
        if 'status' not in poi_cols:
            conn.execute("ALTER TABLE deep_desert_pois ADD COLUMN status TEXT DEFAULT 'active'")
        if 'archived_at' not in poi_cols:
            conn.execute("ALTER TABLE deep_desert_pois ADD COLUMN archived_at TEXT DEFAULT ''")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_deep_desert_pois_guild ON deep_desert_pois(guild_code)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_deep_desert_pois_remote ON deep_desert_pois(remote_id)")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS guild_bases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                map_key TEXT NOT NULL DEFAULT 'hagga_basin',
                x REAL NOT NULL,
                y REAL NOT NULL,
                base_name TEXT NOT NULL DEFAULT 'Guild Base',
                seitch TEXT NOT NULL DEFAULT '',
                guild_code TEXT DEFAULT '',
                created_by TEXT DEFAULT '',
                remote_id TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        base_cols = {row['name'] for row in conn.execute("PRAGMA table_info(guild_bases)").fetchall()}
        if 'status' not in base_cols:
            conn.execute("ALTER TABLE guild_bases ADD COLUMN status TEXT NOT NULL DEFAULT 'friendly'")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_guild_bases_guild ON guild_bases(guild_code)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_guild_bases_remote ON guild_bases(remote_id)")
    except Exception:
        pass
    conn.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS guild_news_cache (
            remote_id TEXT PRIMARY KEY,
            guild_code TEXT DEFAULT '',
            title TEXT DEFAULT '',
            body TEXT DEFAULT '',
            created_by TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS guild_events_cache (
            remote_id TEXT PRIMARY KEY,
            guild_code TEXT DEFAULT '',
            title TEXT DEFAULT '',
            body TEXT DEFAULT '',
            created_by TEXT DEFAULT '',
            event_at TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS guild_activity_cache (
            remote_id TEXT PRIMARY KEY,
            guild_code TEXT DEFAULT '',
            message TEXT DEFAULT '',
            actor TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS guild_links_cache (
            remote_id TEXT PRIMARY KEY,
            guild_code TEXT DEFAULT '',
            title TEXT DEFAULT '',
            url TEXT DEFAULT '',
            created_by TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

# Wrap original connect so new runtime columns/settings are always present.
_original_connect = connect

def connect() -> sqlite3.Connection:  # type: ignore[no-redef]
    conn = _original_connect()
    _ensure_runtime_columns(conn)
    return conn


def get_setting(key: str, default: str = "") -> str:
    conn = connect()
    try:
        row = conn.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default
    finally:
        conn.close()


def set_setting(key: str, value: str) -> None:
    conn = connect()
    try:
        conn.execute(
            "INSERT INTO app_settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        conn.commit()
    finally:
        conn.close()


def add_poi(
    x: float,
    y: float,
    label: str,
    note: str = "",
    map_key: str = "deep_desert",
    guild_code: str = "",
    poi_type: str = "Custom",
    created_by: str = "",
) -> int:  # type: ignore[no-redef]
    label = label.strip()
    if not label:
        raise ValueError("POI label is required.")
    conn = connect()
    try:
        cur = conn.execute(
            """
            INSERT INTO deep_desert_pois
                (map_key, x, y, label, note, guild_code, poi_type, created_by, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                map_key,
                float(x),
                float(y),
                label,
                note.strip(),
                guild_code.strip(),
                (poi_type or "Custom").strip(),
                created_by.strip(),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def upsert_remote_poi(
    remote_id: str,
    x: float,
    y: float,
    label: str,
    note: str,
    guild_code: str,
    map_key: str = "deep_desert",
    poi_type: str = "Custom",
    created_by: str = "",
    last_updated_by: str = "",
    pooped_on: bool = False,
) -> None:
    remote_id = str(remote_id or "").strip()
    if not remote_id:
        return
    conn = connect()
    try:
        existing = conn.execute("SELECT id FROM deep_desert_pois WHERE remote_id=?", (remote_id,)).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE deep_desert_pois
                SET x=?, y=?, label=?, note=?, guild_code=?, poi_type=?, created_by=?, last_updated_by=?, pooped_on=?, updated_at=CURRENT_TIMESTAMP
                WHERE remote_id=?
                """,
                (
                    float(x),
                    float(y),
                    label.strip(),
                    note.strip(),
                    guild_code.strip(),
                    (poi_type or "Custom").strip(),
                    created_by.strip(),
                    (last_updated_by or created_by).strip(),
                    1 if pooped_on else 0,
                    remote_id,
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO deep_desert_pois
                    (map_key, x, y, label, note, guild_code, remote_id, poi_type, created_by, last_updated_by, pooped_on, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    map_key,
                    float(x),
                    float(y),
                    label.strip(),
                    note.strip(),
                    guild_code.strip(),
                    remote_id,
                    (poi_type or "Custom").strip(),
                    created_by.strip(),
                    (last_updated_by or created_by).strip(),
                    1 if pooped_on else 0,
                ),
            )
        conn.commit()
    finally:
        conn.close()


def set_poi_remote_id(local_id: int, remote_id: str) -> None:
    conn = connect()
    try:
        conn.execute(
            "UPDATE deep_desert_pois SET remote_id=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (remote_id.strip(), int(local_id)),
        )
        conn.commit()
    finally:
        conn.close()


def list_unsynced_pois(guild_code: str = "", map_key: str = "deep_desert") -> list[sqlite3.Row]:
    conn = connect()
    try:
        if guild_code:
            return conn.execute(
                """
                SELECT * FROM deep_desert_pois
                WHERE map_key=? AND guild_code=?
                ORDER BY id DESC
                """,
                (map_key, guild_code),
            ).fetchall()
        return conn.execute("SELECT * FROM deep_desert_pois WHERE map_key=? ORDER BY id DESC", (map_key,)).fetchall()
    finally:
        conn.close()


# Hagga Basin Guild Bases

def list_bases(guild_code: str = "", map_key: str = "hagga_basin") -> list[sqlite3.Row]:
    conn = connect()
    try:
        if guild_code:
            return conn.execute(
                "SELECT * FROM guild_bases WHERE map_key=? AND guild_code=? ORDER BY created_by, base_name, id",
                (map_key, guild_code),
            ).fetchall()
        return conn.execute("SELECT * FROM guild_bases WHERE map_key=? ORDER BY created_by, base_name, id", (map_key,)).fetchall()
    finally:
        conn.close()


def add_base(x: float, y: float, base_name: str, seitch: str, guild_code: str, created_by: str, map_key: str = "hagga_basin", status: str = "friendly") -> int:
    conn = connect()
    try:
        cur = conn.execute(
            """
            INSERT INTO guild_bases (map_key, x, y, base_name, seitch, guild_code, created_by, status, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (map_key, float(x), float(y), base_name.strip(), seitch.strip(), guild_code.strip(), created_by.strip(), (status or "friendly").strip().lower()),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def get_base(base_id: int) -> sqlite3.Row | None:
    conn = connect()
    try:
        return conn.execute("SELECT * FROM guild_bases WHERE id=?", (int(base_id),)).fetchone()
    finally:
        conn.close()


def update_base(base_id: int, base_name: str, seitch: str) -> None:
    conn = connect()
    try:
        conn.execute(
            "UPDATE guild_bases SET base_name=?, seitch=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (base_name.strip(), seitch.strip(), int(base_id)),
        )
        conn.commit()
    finally:
        conn.close()


def update_base_position(base_id: int, x: float, y: float) -> None:
    conn = connect()
    try:
        conn.execute(
            "UPDATE guild_bases SET x=?, y=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (float(x), float(y), int(base_id)),
        )
        conn.commit()
    finally:
        conn.close()


def update_base_status(base_id: int, status: str) -> None:
    status = (status or "friendly").strip().lower()
    if status not in {"friendly", "enemy", "defeated", "gone"}:
        status = "friendly"
    conn = connect()
    try:
        conn.execute(
            "UPDATE guild_bases SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (status, int(base_id)),
        )
        conn.commit()
    finally:
        conn.close()


def delete_base(base_id: int) -> None:
    conn = connect()
    try:
        conn.execute("DELETE FROM guild_bases WHERE id=?", (int(base_id),))
        conn.commit()
    finally:
        conn.close()


def upsert_remote_base(remote_id: str, x: float, y: float, base_name: str, seitch: str, guild_code: str, created_by: str, map_key: str = "hagga_basin", status: str = "friendly") -> None:
    remote_id = str(remote_id or "").strip()
    if not remote_id:
        return
    conn = connect()
    try:
        existing = conn.execute("SELECT id FROM guild_bases WHERE remote_id=?", (remote_id,)).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE guild_bases
                SET x=?, y=?, base_name=?, seitch=?, guild_code=?, created_by=?, status=?, updated_at=CURRENT_TIMESTAMP
                WHERE remote_id=?
                """,
                (float(x), float(y), base_name.strip(), seitch.strip(), guild_code.strip(), created_by.strip(), (status or "friendly").strip().lower(), remote_id),
            )
        else:
            conn.execute(
                """
                INSERT INTO guild_bases (map_key, x, y, base_name, seitch, guild_code, created_by, remote_id, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (map_key, float(x), float(y), base_name.strip(), seitch.strip(), guild_code.strip(), created_by.strip(), remote_id, (status or "friendly").strip().lower()),
            )
        conn.commit()
    finally:
        conn.close()


def list_unsynced_bases(guild_code: str = "", map_key: str = "hagga_basin") -> list[sqlite3.Row]:
    conn = connect()
    try:
        if guild_code:
            return conn.execute(
                "SELECT * FROM guild_bases WHERE map_key=? AND guild_code=? ORDER BY id DESC",
                (map_key, guild_code),
            ).fetchall()
        return conn.execute("SELECT * FROM guild_bases WHERE map_key=? ORDER BY id DESC", (map_key,)).fetchall()
    finally:
        conn.close()


def set_base_remote_id(local_id: int, remote_id: str) -> None:
    conn = connect()
    try:
        conn.execute(
            "UPDATE guild_bases SET remote_id=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (remote_id.strip(), int(local_id)),
        )
        conn.commit()
    finally:
        conn.close()



def get_poi(poi_id: int) -> sqlite3.Row | None:
    conn = connect()
    try:
        return conn.execute("SELECT * FROM deep_desert_pois WHERE id=?", (int(poi_id),)).fetchone()
    finally:
        conn.close()


def update_poi(poi_id: int, poi_type: str, note: str, pooped_on: bool = False, updated_by: str = "") -> None:
    conn = connect()
    try:
        conn.execute(
            """
            UPDATE deep_desert_pois
            SET label=?, poi_type=?, note=?, pooped_on=?, last_updated_by=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            ((poi_type or "Custom").strip(), (poi_type or "Custom").strip(), note.strip(), 1 if pooped_on else 0, updated_by.strip(), int(poi_id)),
        )
        conn.commit()
    finally:
        conn.close()




def update_poi_status(poi_id: int, status: str, updated_by: str = "") -> None:
    clean = (status or "active").strip().lower()
    if clean not in {"active", "friendly", "enemy", "defeated", "gone"}:
        clean = "active"
    archived_expr = "CURRENT_TIMESTAMP" if clean in {"defeated", "gone"} else "''"
    conn = connect()
    try:
        conn.execute(
            f"""
            UPDATE deep_desert_pois
            SET status=?, pooped_on=?, last_updated_by=?, archived_at={archived_expr}, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (clean, 1 if clean == "defeated" else 0, updated_by.strip(), int(poi_id)),
        )
        conn.commit()
    finally:
        conn.close()

def clear_local_guild_cache(guild_code: str = "") -> None:
    """Remove cached local guild POIs and bases.

    Supabase remains the source of truth; this prevents ghost bases/POIs after
    leaving or switching guilds. If guild_code is blank, all local guild map
    data is cleared.
    """
    conn = connect()
    try:
        guild = (guild_code or "").strip().upper()
        if guild:
            conn.execute("DELETE FROM deep_desert_pois WHERE UPPER(COALESCE(guild_code, ''))=?", (guild,))
            conn.execute("DELETE FROM guild_bases WHERE UPPER(COALESCE(guild_code, ''))=?", (guild,))
            conn.execute("DELETE FROM guild_news_cache WHERE UPPER(COALESCE(guild_code, ''))=?", (guild,))
            conn.execute("DELETE FROM guild_activity_cache WHERE UPPER(COALESCE(guild_code, ''))=?", (guild,))
            conn.execute("DELETE FROM guild_links_cache WHERE UPPER(COALESCE(guild_code, ''))=?", (guild,))
        else:
            conn.execute("DELETE FROM deep_desert_pois")
            conn.execute("DELETE FROM guild_bases")
            conn.execute("DELETE FROM guild_news_cache")
            conn.execute("DELETE FROM guild_activity_cache")
            conn.execute("DELETE FROM guild_links_cache")
        conn.commit()
    finally:
        conn.close()


def clear_orphan_guild_cache() -> None:
    """Remove local map records that are not tied to any guild."""
    conn = connect()
    try:
        conn.execute("DELETE FROM deep_desert_pois WHERE COALESCE(guild_code, '')='' ")
        conn.execute("DELETE FROM guild_bases WHERE COALESCE(guild_code, '')='' ")
        conn.commit()
    finally:
        conn.close()


# Guild dashboard cache helpers

def cache_guild_news(rows: list[dict], guild_code: str) -> None:
    conn = connect()
    try:
        guild = (guild_code or "").strip().upper()
        conn.execute("DELETE FROM guild_news_cache WHERE guild_code=?", (guild,))
        for row in rows or []:
            conn.execute(
                """
                INSERT OR REPLACE INTO guild_news_cache
                (remote_id, guild_code, title, body, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(row.get("id", row.get("remote_id", ""))),
                    guild,
                    str(row.get("title", "")),
                    str(row.get("body", row.get("message", ""))),
                    str(row.get("created_by", row.get("actor", ""))),
                    str(row.get("created_at", "")),
                ),
            )
        conn.commit()
    finally:
        conn.close()


def list_guild_news(guild_code: str = "", limit: int = 20) -> list[sqlite3.Row]:
    conn = connect()
    try:
        guild = (guild_code or "").strip().upper()
        return conn.execute(
            "SELECT * FROM guild_news_cache WHERE guild_code=? ORDER BY created_at DESC LIMIT ?",
            (guild, int(limit)),
        ).fetchall()
    finally:
        conn.close()


def cache_guild_activity(rows: list[dict], guild_code: str) -> None:
    conn = connect()
    try:
        guild = (guild_code or "").strip().upper()
        conn.execute("DELETE FROM guild_activity_cache WHERE guild_code=?", (guild,))
        for row in rows or []:
            conn.execute(
                """
                INSERT OR REPLACE INTO guild_activity_cache
                (remote_id, guild_code, message, actor, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(row.get("id", row.get("remote_id", ""))),
                    guild,
                    str(row.get("message", row.get("body", ""))),
                    str(row.get("actor", row.get("created_by", ""))),
                    str(row.get("created_at", "")),
                ),
            )
        conn.commit()
    finally:
        conn.close()


def list_guild_activity(guild_code: str = "", limit: int = 30) -> list[sqlite3.Row]:
    conn = connect()
    try:
        guild = (guild_code or "").strip().upper()
        return conn.execute(
            "SELECT * FROM guild_activity_cache WHERE guild_code=? ORDER BY created_at DESC LIMIT ?",
            (guild, int(limit)),
        ).fetchall()
    finally:
        conn.close()


def cache_guild_links(rows: list[dict], guild_code: str) -> None:
    conn = connect()
    try:
        guild = (guild_code or "").strip().upper()
        conn.execute("DELETE FROM guild_links_cache WHERE guild_code=?", (guild,))
        for row in rows or []:
            conn.execute(
                """
                INSERT OR REPLACE INTO guild_links_cache
                (remote_id, guild_code, title, url, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(row.get("id", row.get("remote_id", ""))),
                    guild,
                    str(row.get("title", "")),
                    str(row.get("url", "")),
                    str(row.get("created_by", "")),
                    str(row.get("created_at", "")),
                ),
            )
        conn.commit()
    finally:
        conn.close()


def list_guild_links(guild_code: str = "", limit: int = 30) -> list[sqlite3.Row]:
    conn = connect()
    try:
        guild = (guild_code or "").strip().upper()
        return conn.execute(
            "SELECT * FROM guild_links_cache WHERE guild_code=? ORDER BY title COLLATE NOCASE LIMIT ?",
            (guild, int(limit)),
        ).fetchall()
    finally:
        conn.close()

# ---- Local/offline guild support used when Supabase is not configured ----
def ensure_local_guild_tables() -> None:
    conn = connect()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS local_guild_members (
                guild_code TEXT NOT NULL,
                display_name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'member',
                joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_code, display_name)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS member_specializations (
                guild_code TEXT NOT NULL,
                display_name TEXT NOT NULL,
                combat INTEGER NOT NULL DEFAULT 1,
                exploration INTEGER NOT NULL DEFAULT 1,
                crafting INTEGER NOT NULL DEFAULT 1,
                gathering INTEGER NOT NULL DEFAULT 1,
                sabotage INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_code, display_name)
            )
        """)
        conn.commit()
    finally:
        conn.close()


def upsert_local_member(guild_code: str, display_name: str, role: str = "member") -> None:
    ensure_local_guild_tables()
    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO local_guild_members(guild_code, display_name, role)
            VALUES(?, ?, ?)
            ON CONFLICT(guild_code, display_name) DO UPDATE SET role=excluded.role
            """,
            ((guild_code or "").strip().upper(), (display_name or "").strip(), (role or "member").strip().lower()),
        )
        conn.commit()
    finally:
        conn.close()


def list_local_members(guild_code: str = "") -> list[sqlite3.Row]:
    ensure_local_guild_tables()
    conn = connect()
    try:
        guild = (guild_code or "").strip().upper()
        return conn.execute(
            "SELECT display_name, role, joined_at FROM local_guild_members WHERE guild_code=? ORDER BY CASE role WHEN 'owner' THEN 0 WHEN 'officer' THEN 1 ELSE 2 END, display_name COLLATE NOCASE",
            (guild,),
        ).fetchall()
    finally:
        conn.close()



def upsert_member_specializations(guild_code: str, display_name: str, combat: int = 1, exploration: int = 1, crafting: int = 1, gathering: int = 1, sabotage: int = 1) -> None:
    ensure_local_guild_tables()
    guild = (guild_code or "").strip().upper()
    name = (display_name or "").strip()
    def clamp(value):
        try:
            return max(1, min(100, int(value)))
        except Exception:
            return 1
    if not guild or not name:
        return
    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO member_specializations
                (guild_code, display_name, combat, exploration, crafting, gathering, sabotage, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(guild_code, display_name) DO UPDATE SET
                combat=excluded.combat, exploration=excluded.exploration, crafting=excluded.crafting,
                gathering=excluded.gathering, sabotage=excluded.sabotage, updated_at=CURRENT_TIMESTAMP
            """,
            (guild, name, clamp(combat), clamp(exploration), clamp(crafting), clamp(gathering), clamp(sabotage)),
        )
        conn.commit()
    finally:
        conn.close()


def get_member_specializations(guild_code: str, display_name: str) -> dict:
    ensure_local_guild_tables()
    guild = (guild_code or "").strip().upper()
    name = (display_name or "").strip()
    conn = connect()
    try:
        row = conn.execute(
            "SELECT combat, exploration, crafting, gathering, sabotage FROM member_specializations WHERE guild_code=? AND display_name=?",
            (guild, name),
        ).fetchone()
        if not row:
            return {"combat": 1, "exploration": 1, "crafting": 1, "gathering": 1, "sabotage": 1}
        return {k: int(row[k] or 1) for k in ("combat", "exploration", "crafting", "gathering", "sabotage")}
    finally:
        conn.close()


def list_member_specializations(guild_code: str = "") -> list[sqlite3.Row]:
    ensure_local_guild_tables()
    guild = (guild_code or "").strip().upper()
    conn = connect()
    try:
        return conn.execute(
            """
            SELECT m.display_name, m.role,
                   COALESCE(s.combat,1) AS combat, COALESCE(s.exploration,1) AS exploration,
                   COALESCE(s.crafting,1) AS crafting, COALESCE(s.gathering,1) AS gathering,
                   COALESCE(s.sabotage,1) AS sabotage
            FROM local_guild_members m
            LEFT JOIN member_specializations s ON s.guild_code=m.guild_code AND s.display_name=m.display_name
            WHERE m.guild_code=?
            ORDER BY CASE m.role WHEN 'owner' THEN 0 WHEN 'officer' THEN 1 ELSE 2 END, m.display_name COLLATE NOCASE
            """,
            (guild,),
        ).fetchall()
    finally:
        conn.close()

def remove_local_member(guild_code: str, display_name: str) -> None:
    ensure_local_guild_tables()
    conn = connect()
    try:
        guild = (guild_code or "").strip().upper()
        name = (display_name or "").strip()
        conn.execute("DELETE FROM local_guild_members WHERE guild_code=? AND display_name=?", (guild, name))
        conn.execute("DELETE FROM member_specializations WHERE guild_code=? AND display_name=?", (guild, name))
        conn.commit()
    finally:
        conn.close()


def add_local_guild_news(guild_code: str, title: str, body: str, created_by: str) -> str:
    import uuid
    rid = "local-" + uuid.uuid4().hex
    conn = connect()
    try:
        guild = (guild_code or "").strip().upper()
        conn.execute(
            """
            INSERT INTO guild_news_cache(remote_id, guild_code, title, body, created_by, created_at)
            VALUES(?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (rid, guild, (title or "").strip(), (body or "").strip(), (created_by or "").strip()),
        )
        conn.commit()
        return rid
    finally:
        conn.close()


def delete_local_guild_news(remote_id: str) -> None:
    conn = connect()
    try:
        conn.execute("DELETE FROM guild_news_cache WHERE remote_id=?", ((remote_id or "").strip(),))
        conn.commit()
    finally:
        conn.close()


def cache_guild_events(rows: list[dict], guild_code: str) -> None:
    guild = (guild_code or "").strip().upper()
    conn = connect()
    try:
        conn.execute("DELETE FROM guild_events_cache WHERE guild_code=?", (guild,))
        for row in rows or []:
            conn.execute(
                """
                INSERT OR REPLACE INTO guild_events_cache
                (remote_id, guild_code, title, body, created_by, event_at, created_at)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(row.get("id") or row.get("remote_id") or ""),
                    guild,
                    row.get("title") or "",
                    row.get("body") or row.get("notes") or "",
                    row.get("created_by") or "",
                    row.get("event_at") or row.get("starts_at") or "",
                    row.get("created_at") or "",
                ),
            )
        conn.commit()
    finally:
        conn.close()


def list_guild_events(guild_code: str = "", limit: int = 20) -> list[sqlite3.Row]:
    guild = (guild_code or "").strip().upper()
    conn = connect()
    try:
        return conn.execute(
            "SELECT * FROM guild_events_cache WHERE guild_code=? ORDER BY COALESCE(NULLIF(event_at,''), created_at) DESC LIMIT ?",
            (guild, int(limit or 20)),
        ).fetchall()
    finally:
        conn.close()


def add_local_guild_event(guild_code: str, title: str, body: str, created_by: str, event_at: str = "") -> str:
    import uuid
    rid = "local-event-" + uuid.uuid4().hex
    conn = connect()
    try:
        guild = (guild_code or "").strip().upper()
        conn.execute(
            """
            INSERT INTO guild_events_cache(remote_id, guild_code, title, body, created_by, event_at, created_at)
            VALUES(?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (rid, guild, (title or "").strip(), (body or "").strip(), (created_by or "").strip(), (event_at or "").strip()),
        )
        conn.commit()
        return rid
    finally:
        conn.close()


def delete_local_guild_event(remote_id: str) -> None:
    conn = connect()
    try:
        conn.execute("DELETE FROM guild_events_cache WHERE remote_id=?", ((remote_id or "").strip(),))
        conn.commit()
    finally:
        conn.close()


def clear_local_catalog(skip_seed: bool = True) -> None:
    """Remove every local catalog listing and dependent local market data."""
    conn = connect()
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("DELETE FROM price_observations")
        conn.execute("DELETE FROM catalog_items")
        conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('catalog_items', 'price_observations')")
        if skip_seed:
            conn.execute("CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT DEFAULT '')")
            conn.execute("INSERT INTO app_settings(key, value) VALUES('catalog_force_github_reimport','1') ON CONFLICT(key) DO UPDATE SET value='1'")
            conn.execute("INSERT INTO app_settings(key, value) VALUES('catalog_imported_once','') ON CONFLICT(key) DO UPDATE SET value=''")
        conn.commit()
        try:
            conn.execute("VACUUM")
        except Exception:
            pass
    finally:
        conn.close()
