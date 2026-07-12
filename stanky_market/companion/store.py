from __future__ import annotations

import json
import os
import re
import sqlite3
import shutil
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from ..paths import data_dir, resource_path

DB_PATH = data_dir() / "stanky_companion.sqlite3"

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS companion_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL DEFAULT 'Item',
    tier TEXT DEFAULT '',
    rarity TEXT DEFAULT '',
    stack_size TEXT DEFAULT '',
    weight TEXT DEFAULT '',
    template_id TEXT DEFAULT '',
    volume TEXT DEFAULT '',
    tags_json TEXT DEFAULT '',
    source TEXT DEFAULT 'manual',
    notes TEXT DEFAULT '',
    raw_json TEXT DEFAULT '',
    image_path TEXT DEFAULT '',
    source_url TEXT DEFAULT '',
    subcategory TEXT DEFAULT '',
    item_id TEXT DEFAULT '',
    power_cost REAL DEFAULT 0,
    power_generated REAL DEFAULT 0,
    water_gained_per_day REAL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS companion_recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    output_item TEXT NOT NULL,
    output_qty INTEGER NOT NULL DEFAULT 1,
    station TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS companion_recipe_materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id INTEGER NOT NULL,
    material_name TEXT NOT NULL,
    quantity REAL NOT NULL DEFAULT 1,
    FOREIGN KEY(recipe_id) REFERENCES companion_recipes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS companion_blueprints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    base_type TEXT DEFAULT '',
    players_recommended TEXT DEFAULT '',
    tags TEXT DEFAULT '',
    power_notes TEXT DEFAULT '',
    material_notes TEXT DEFAULT '',
    layout_json TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS companion_timers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    timer_type TEXT NOT NULL DEFAULT 'custom',
    duration_seconds INTEGER NOT NULL DEFAULT 2700,
    started_at TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    UNIQUE(name, timer_type)
);

CREATE TABLE IF NOT EXISTS companion_crafting_sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    targets_json TEXT NOT NULL DEFAULT '[]',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS companion_mod_backups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    backup_path TEXT NOT NULL,
    label TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS companion_settings (
    key TEXT PRIMARY KEY,
    value TEXT DEFAULT ''
);
"""

# Sample/placeholder data intentionally removed.
# StankyTools now relies on real bundled exports/catalog data or user-created records.
SAMPLE_ITEMS = []
SAMPLE_RECIPES = []
SAMPLE_BLUEPRINTS = []
SAMPLE_TIMERS = []



def bundled_catalog_db_path() -> Path:
    return resource_path("assets", "catalog", "catalog.sqlite3")


def resolve_catalog_asset_path(path_value: str) -> str:
    """Resolve catalog image paths stored as package-relative paths."""
    text = str(path_value or "").strip()
    if not text:
        return ""
    path = Path(text)
    if path.is_absolute() and path.exists():
        return str(path)
    resolved = resource_path(*Path(text).parts)
    if resolved.exists():
        return str(resolved)
    return text


def _install_bundled_catalog_if_empty(conn: sqlite3.Connection) -> None:
    """Seed the user database from the optimized bundled catalog once.

    The release package ships one compact SQLite catalog plus WebP thumbnails.
    This avoids parsing JSON or copying huge exports on startup.
    """
    try:
        existing = conn.execute("SELECT COUNT(*) FROM companion_items").fetchone()[0]
    except Exception:
        existing = 0
    if existing:
        return
    try:
        disabled = conn.execute("SELECT value FROM companion_settings WHERE key='catalog_disabled'").fetchone()
        if disabled and str(disabled[0]) == '1':
            return
    except Exception:
        pass
    bundled = bundled_catalog_db_path()
    if not bundled.exists():
        return
    try:
        conn.execute("ATTACH DATABASE - AS bundled_catalog", (str(bundled),))
        conn.execute("""
            INSERT OR IGNORE INTO companion_items
            (name, category, tier, rarity, stack_size, weight, template_id, volume, tags_json, source, notes, raw_json, image_path, source_url, subcategory, item_id, power_cost, power_generated, water_gained_per_day, created_at, updated_at)
            SELECT name, category, tier, rarity, stack_size, weight, template_id, volume, tags_json, source, notes, raw_json, image_path, source_url, subcategory, item_id, COALESCE(power_cost, 0), COALESCE(power_generated, 0), COALESCE(water_gained_per_day, 0), created_at, updated_at
            FROM bundled_catalog.companion_items
        """)
        conn.execute("""
            INSERT OR IGNORE INTO companion_recipes
            (id, name, output_item, output_qty, station, notes, created_at)
            SELECT id, name, output_item, output_qty, station, notes, created_at
            FROM bundled_catalog.companion_recipes
        """)
        conn.execute("""
            INSERT OR IGNORE INTO companion_recipe_materials
            (id, recipe_id, material_name, quantity)
            SELECT id, recipe_id, material_name, quantity
            FROM bundled_catalog.companion_recipe_materials
        """)
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        try:
            conn.execute("DETACH DATABASE bundled_catalog")
        except Exception:
            pass


def reload_bundled_catalog(progress=None) -> dict[str, int]:
    """Replace the local catalog with the optimized bundled SQLite catalog."""
    bundled = bundled_catalog_db_path()
    if not bundled.exists():
        raise FileNotFoundError(f"Bundled catalog database not found: {bundled}")
    conn = connect()
    try:
        if progress:
            progress("Loading optimized bundled catalog database...")
        conn.execute("DELETE FROM companion_recipe_materials")
        conn.execute("DELETE FROM companion_recipes")
        conn.execute("DELETE FROM companion_items")
        conn.execute("INSERT OR REPLACE INTO companion_settings (key, value) VALUES ('catalog_disabled', '0')")
        conn.commit()
        _install_bundled_catalog_if_empty(conn)
        stats = catalog_stats()
        if progress:
            progress(f"Loaded {stats.get('items', 0):,} items and {stats.get('recipes', 0):,} recipes from bundled catalog.")
        return {"items": stats.get("items", 0), "recipes": stats.get("recipes", 0), "source": str(bundled)}
    finally:
        conn.close()

def connect() -> sqlite3.Connection:
    data_dir().mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    # Lightweight migrations for users who already created older databases.
    for column, ddl in (
        ("template_id", "ALTER TABLE companion_items ADD COLUMN template_id TEXT DEFAULT ''"),
        ("volume", "ALTER TABLE companion_items ADD COLUMN volume TEXT DEFAULT ''"),
        ("tags_json", "ALTER TABLE companion_items ADD COLUMN tags_json TEXT DEFAULT ''"),
        ("image_path", "ALTER TABLE companion_items ADD COLUMN image_path TEXT DEFAULT ''"),
        ("source_url", "ALTER TABLE companion_items ADD COLUMN source_url TEXT DEFAULT ''"),
        ("subcategory", "ALTER TABLE companion_items ADD COLUMN subcategory TEXT DEFAULT ''"),
        ("item_id", "ALTER TABLE companion_items ADD COLUMN item_id TEXT DEFAULT ''"),
        ("power_cost", "ALTER TABLE companion_items ADD COLUMN power_cost REAL DEFAULT 0"),
        ("power_generated", "ALTER TABLE companion_items ADD COLUMN power_generated REAL DEFAULT 0"),
        ("water_gained_per_day", "ALTER TABLE companion_items ADD COLUMN water_gained_per_day REAL DEFAULT 0"),
    ):
        try:
            conn.execute(ddl)
        except sqlite3.OperationalError:
            pass
    _install_bundled_catalog_if_empty(conn)
    return conn


def seed_samples(force: bool = False) -> None:
    """Legacy compatibility hook.

    Sample/placeholder catalog data has been removed. Existing sample rows
    from older builds are cleaned up so only real imported/export data remains.
    """
    conn = connect()
    try:
        conn.execute("DELETE FROM companion_recipe_materials WHERE recipe_id IN (SELECT id FROM companion_recipes WHERE name LIKE 'SAMPLE %' OR notes LIKE 'SAMPLE%')")
        conn.execute("DELETE FROM companion_recipes WHERE name LIKE 'SAMPLE %' OR notes LIKE 'SAMPLE%'")
        conn.execute("DELETE FROM companion_items WHERE source='sample' OR name LIKE 'SAMPLE %'")
        conn.execute("DELETE FROM companion_blueprints WHERE name LIKE 'SAMPLE %' OR layout_json LIKE '%sample%'")
        conn.commit()
    finally:
        conn.close()

def counts() -> dict[str, int]:
    conn = connect()
    try:
        return {
            "items": conn.execute("SELECT COUNT(*) FROM companion_items").fetchone()[0],
            "recipes": conn.execute("SELECT COUNT(*) FROM companion_recipes").fetchone()[0],
            "blueprints": conn.execute("SELECT COUNT(*) FROM companion_blueprints").fetchone()[0],
            "timers": conn.execute("SELECT COUNT(*) FROM companion_timers").fetchone()[0],
            "backups": conn.execute("SELECT COUNT(*) FROM companion_mod_backups").fetchone()[0],
        }
    finally:
        conn.close()



def clear_imported_catalog_items(include_recipes: bool = True) -> dict[str, int]:
    """Delete web/imported catalog items so the user can start fresh.

    Sample rows are left intact unless they were imported from the web. Recipes are
    normally removed too because imported recipe targets/materials may reference
    deleted items.
    """
    conn = connect()
    try:
        item_count = conn.execute("SELECT COUNT(*) FROM companion_items").fetchone()[0]
        recipe_count = 0
        material_count = 0
        if include_recipes:
            recipe_count = conn.execute("SELECT COUNT(*) FROM companion_recipes").fetchone()[0]
            material_count = conn.execute("SELECT COUNT(*) FROM companion_recipe_materials").fetchone()[0]
            conn.execute("DELETE FROM companion_recipe_materials")
            conn.execute("DELETE FROM companion_recipes")
        conn.execute("DELETE FROM companion_items")
        conn.execute("INSERT OR REPLACE INTO companion_settings (key, value) VALUES ('catalog_disabled', '1')")
        conn.commit()
        return {"items": int(item_count), "recipes": int(recipe_count), "materials": int(material_count)}
    finally:
        conn.close()

def list_items(search: str = "", category: str = "") -> list[sqlite3.Row]:
    conn = connect()
    try:
        where = []
        params: list[str] = []
        if search.strip():
            where.append("(name LIKE - OR notes LIKE - OR template_id LIKE - OR tags_json LIKE ?)")
            params.extend([f"%{search.strip()}%", f"%{search.strip()}%", f"%{search.strip()}%", f"%{search.strip()}%"] )
        if category.strip() and category != "All":
            where.append("category = ?")
            params.append(category)
        clause = "WHERE " + " AND ".join(where) if where else ""
        return conn.execute(f"SELECT * FROM companion_items {clause} ORDER BY category, name", params).fetchall()
    finally:
        conn.close()


def item_categories() -> list[str]:
    conn = connect()
    try:
        rows = conn.execute("SELECT DISTINCT category FROM companion_items ORDER BY category").fetchall()
        return [r[0] for r in rows if r[0]]
    finally:
        conn.close()


def list_recipes(search: str = "") -> list[sqlite3.Row]:
    conn = connect()
    try:
        params: list[str] = []
        clause = ""
        if search.strip():
            clause = "WHERE name LIKE - OR output_item LIKE - OR station LIKE ?"
            params = [f"%{search.strip()}%"] * 3
        return conn.execute(f"SELECT * FROM companion_recipes {clause} ORDER BY name", params).fetchall()
    finally:
        conn.close()


def recipe_materials(recipe_id: int, qty: int = 1) -> list[tuple[str, float]]:
    conn = connect()
    try:
        recipe = conn.execute("SELECT output_qty FROM companion_recipes WHERE id=?", (recipe_id,)).fetchone()
        multiplier = max(1, qty) / max(1, int(recipe[0] if recipe else 1))
        rows = conn.execute("SELECT material_name, quantity FROM companion_recipe_materials WHERE recipe_id=? ORDER BY material_name", (recipe_id,)).fetchall()
        return [(r[0], float(r[1]) * multiplier) for r in rows]
    finally:
        conn.close()




def craftable_recipes(search: str = "") -> list[sqlite3.Row]:
    """Return recipes sorted for the calculator target picker."""
    conn = connect()
    try:
        params: list[str] = []
        clause = ""
        if search.strip():
            clause = "WHERE name LIKE - OR output_item LIKE - OR station LIKE ?"
            params = [f"%{search.strip()}%"] * 3
        return conn.execute(
            f"SELECT * FROM companion_recipes {clause} ORDER BY output_item, station, name",
            params,
        ).fetchall()
    finally:
        conn.close()


def aggregate_recipe_materials(targets: list[dict]) -> tuple[list[dict], list[tuple[str, float]]]:
    """Aggregate direct recipe materials for calculator targets.

    targets format: [{"recipe_id": int, "qty": int}]. This intentionally uses
    direct recipe materials only for speed and reliability. Recursive sub-component
    expansion can be added later once recipe coverage is complete.
    """
    conn = connect()
    output_rows: list[dict] = []
    totals: dict[str, float] = {}
    try:
        for target in targets or []:
            try:
                recipe_id = int(target.get("recipe_id"))
                desired_qty = max(1, int(target.get("qty", 1)))
            except Exception:
                continue
            recipe = conn.execute("SELECT * FROM companion_recipes WHERE id=?", (recipe_id,)).fetchone()
            if not recipe:
                continue
            output_qty = max(1, int(recipe["output_qty"] or 1))
            multiplier = desired_qty / output_qty
            output_rows.append({
                "recipe_id": recipe_id,
                "name": recipe["name"],
                "output_item": recipe["output_item"],
                "station": recipe["station"] or "Unknown",
                "qty": desired_qty,
                "output_qty": output_qty,
            })
            mats = conn.execute(
                "SELECT material_name, quantity FROM companion_recipe_materials WHERE recipe_id=? ORDER BY material_name",
                (recipe_id,),
            ).fetchall()
            for mat in mats:
                material = mat["material_name"]
                qty = float(mat["quantity"] or 0) * multiplier
                totals[material] = totals.get(material, 0.0) + qty
        return output_rows, sorted(totals.items(), key=lambda x: x[0].lower())
    finally:
        conn.close()


def save_crafting_set(name: str, targets: list[dict], notes: str = "") -> None:
    name = (name or "").strip()
    if not name:
        raise ValueError("Crafting set name is required.")
    payload = []
    for target in targets or []:
        try:
            payload.append({"recipe_id": int(target.get("recipe_id")), "qty": max(1, int(target.get("qty", 1)))})
        except Exception:
            continue
    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO companion_crafting_sets (name, targets_json, notes, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(name) DO UPDATE SET
                targets_json=excluded.targets_json,
                notes=excluded.notes,
                updated_at=CURRENT_TIMESTAMP
            """,
            (name, json.dumps(payload), notes or ""),
        )
        conn.commit()
    finally:
        conn.close()


def list_crafting_sets() -> list[sqlite3.Row]:
    conn = connect()
    try:
        return conn.execute("SELECT * FROM companion_crafting_sets ORDER BY updated_at DESC, name").fetchall()
    finally:
        conn.close()


def load_crafting_set(set_id: int) -> list[dict]:
    conn = connect()
    try:
        row = conn.execute("SELECT targets_json FROM companion_crafting_sets WHERE id=?", (set_id,)).fetchone()
        if not row:
            return []
        data = json.loads(row["targets_json"] or "[]")
        return data if isinstance(data, list) else []
    finally:
        conn.close()


def delete_crafting_set(set_id: int) -> None:
    conn = connect()
    try:
        conn.execute("DELETE FROM companion_crafting_sets WHERE id=?", (set_id,))
        conn.commit()
    finally:
        conn.close()

def list_blueprints(search: str = "") -> list[sqlite3.Row]:
    conn = connect()
    try:
        params: list[str] = []
        clause = ""
        if search.strip():
            clause = "WHERE name LIKE - OR base_type LIKE - OR tags LIKE - OR material_notes LIKE ?"
            params = [f"%{search.strip()}%"] * 4
        return conn.execute(f"SELECT * FROM companion_blueprints {clause} ORDER BY updated_at DESC, name", params).fetchall()
    finally:
        conn.close()


def save_blueprint(name: str, base_type: str, tags: str, notes: str, layout_json: str) -> None:
    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO companion_blueprints (name, base_type, tags, material_notes, layout_json, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(name) DO UPDATE SET
                base_type=excluded.base_type,
                tags=excluded.tags,
                material_notes=excluded.material_notes,
                layout_json=excluded.layout_json,
                updated_at=CURRENT_TIMESTAMP
            """,
            (name, base_type, tags, notes, layout_json),
        )
        conn.commit()
    finally:
        conn.close()


def list_timers() -> list[sqlite3.Row]:
    conn = connect()
    try:
        return conn.execute("SELECT * FROM companion_timers ORDER BY timer_type, name").fetchall()
    finally:
        conn.close()


def set_setting(key: str, value: str) -> None:
    conn = connect()
    try:
        conn.execute("INSERT OR REPLACE INTO companion_settings (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
    finally:
        conn.close()


def get_setting(key: str, default: str = "") -> str:
    conn = connect()
    try:
        row = conn.execute("SELECT value FROM companion_settings WHERE key=?", (key,)).fetchone()
        return str(row[0]) if row else default
    finally:
        conn.close()



def _config_candidates(root: str) -> list[Path]:
    base = Path(root).expanduser() if root else Path.home()
    if not base.exists():
        return []
    wanted = {"Engine.ini", "GameUserSettings.ini"}
    if base.is_file():
        return [base] if base.name in wanted else []
    found: list[Path] = []
    # Prefer files directly under the selected folder, then do a bounded recursive scan.
    for name in wanted:
        direct = base / name
        if direct.exists():
            found.append(direct)
    try:
        for path in base.rglob("*.ini"):
            if path.name in wanted and path not in found:
                found.append(path)
            if len(found) >= 12:
                break
    except Exception:
        pass
    return found

def _backup_root() -> Path:
    root = data_dir() / "companion_backups" / "game_configs"
    root.mkdir(parents=True, exist_ok=True)
    return root

def backup_game_configs(root: str) -> dict[str, object]:
    files = _config_candidates(root)
    if not files:
        raise FileNotFoundError("No Engine.ini or GameUserSettings.ini files were found in the selected folder.")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target_dir = _backup_root() / stamp
    target_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    conn = connect()
    try:
        for src in files:
            safe_name = src.name
            if len(files) > 2:
                safe_name = f"{abs(hash(str(src))) % 100000}_{src.name}"
            dst = target_dir / safe_name
            shutil.copy2(src, dst)
            manifest.append({"source": str(src), "backup": str(dst)})
            conn.execute(
                "INSERT INTO companion_mod_backups (file_path, backup_path, label) VALUES (?, ?, ?)",
                (str(src), str(dst), "Game Manager backup"),
            )
        (target_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        conn.commit()
    finally:
        conn.close()
    return {"files": len(manifest), "folder": str(target_dir)}

def restore_latest_game_config_backup() -> dict[str, object]:
    root = _backup_root()
    manifests = sorted(root.glob("*/manifest.json"), reverse=True)
    if not manifests:
        raise FileNotFoundError("No StankyTools config backups were found.")
    manifest_path = manifests[0]
    entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    restored = 0
    for entry in entries:
        src = Path(entry.get("backup", ""))
        dst = Path(entry.get("source", ""))
        if src.exists() and dst.parent.exists():
            shutil.copy2(src, dst)
            restored += 1
    if not restored:
        raise FileNotFoundError("The latest backup could not be restored because the original paths are missing.")
    return {"files": restored, "folder": str(manifest_path.parent)}

def scan_game_manager_status(root: str) -> dict[str, object]:
    files = _config_candidates(root)
    conn = connect()
    try:
        backups = conn.execute("SELECT COUNT(*) FROM companion_mod_backups").fetchone()[0]
    finally:
        conn.close()
    profile_detected = False
    enabled_tweaks: list[str] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "STANKYTOOLS PROFILE" in text or "STANKYTOOLS TWEAKS" in text:
                profile_detected = True
            for label, values in ENGINE_TWEAKS.values():
                if any(value in text for value in values) and label not in enabled_tweaks:
                    enabled_tweaks.append(label)
        except Exception:
            pass
    return {
        "path": root,
        "config_count": len(files),
        "config_files": [str(p) for p in files],
        "backup_count": backups,
        "profile_detected": profile_detected,
        "enabled_tweaks": enabled_tweaks,
    }


ENGINE_TWEAKS: dict[str, tuple[str, list[str]]] = {
    "motion_blur": ("Disable Motion Blur", ["r.MotionBlurQuality=0", "r.MotionBlur.Max=0"]),
    "film_grain": ("Disable Film Grain", ["r.FilmGrain=0"]),
    "lens_flare": ("Disable Lens Flare", ["r.LensFlareQuality=0"]),
    "soften_bloom": ("Reduce Bloom", ["r.BloomQuality=3"]),
    "sharpen": ("Light Sharpening", ["r.Tonemapper.Sharpen=0.5"]),
}

LAUNCH_TWEAKS: dict[str, tuple[str, str]] = {
    "no_splash": ("No Splash Screen", "-nostartupscreen"),
}

def detect_dune_game_folder() -> str:
    """Best-effort local detection for Dune Awakening game/config folders."""
    candidates: list[Path] = []
    local_app = os.environ.get("LOCALAPPDATA")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    steam_roots = [
        Path(program_files_x86) / "Steam" / "steamapps" / "common" / "Dune Awakening",
        Path(program_files) / "Steam" / "steamapps" / "common" / "Dune Awakening",
        Path(r"C:\SteamLibrary") / "steamapps" / "common" / "Dune Awakening",
        Path(r"D:\SteamLibrary") / "steamapps" / "common" / "Dune Awakening",
        Path(r"E:\SteamLibrary") / "steamapps" / "common" / "Dune Awakening",
    ]
    candidates.extend(steam_roots)
    if local_app:
        candidates.extend([
            Path(local_app) / "DuneSandbox" / "Saved" / "Config" / "WindowsNoEditor",
            Path(local_app) / "DuneSandbox" / "Saved" / "Config" / "Windows",
            Path(local_app) / "DuneAwakening" / "Saved" / "Config" / "WindowsNoEditor",
            Path(local_app) / "DuneAwakening" / "Saved" / "Config" / "Windows",
            Path(local_app) / "WS" / "Saved" / "Config" / "WindowsNoEditor",
            Path(local_app) / "Warlords" / "Saved" / "Config" / "Windows",
        ])
    for candidate in candidates:
        try:
            if candidate.exists():
                return str(candidate)
        except Exception:
            continue
    return ""

def apply_engine_tweaks(root: str, tweaks: list[str]) -> dict[str, object]:
    if not tweaks:
        raise ValueError("Select at least one tweak before applying.")
    files = _config_candidates(root)
    engine = next((p for p in files if p.name == "Engine.ini"), None)
    if engine is None:
        base = Path(root).expanduser() if root else Path.home()
        if not base.exists():
            raise FileNotFoundError("Selected folder does not exist.")
        engine = base / "Engine.ini"
        if not engine.exists():
            engine.write_text("", encoding="utf-8")
    backup_game_configs(str(engine.parent))
    text = engine.read_text(encoding="utf-8", errors="ignore") if engine.exists() else ""
    start = "; BEGIN STANKYTOOLS TWEAKS"
    end = "; END STANKYTOOLS TWEAKS"
    while start in text and end in text:
        a = text.index(start)
        b = text.index(end, a) + len(end)
        text = text[:a].rstrip() + "\n" + text[b:].lstrip()
    lines = [start, "; Reversible user-selected StankyTools tweaks. Backups are created before edits.", "[SystemSettings]"]
    labels = []
    seen = set()
    engine_keys = [key for key in tweaks if key in ENGINE_TWEAKS]
    for key in engine_keys:
        label, values = ENGINE_TWEAKS[key]
        labels.append(label)
        lines.append(f"; {label}")
        for value in values:
            if value not in seen:
                lines.append(value)
                seen.add(value)
    if engine_keys:
        lines.append(end)
        engine.write_text(text.rstrip() + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
    launch_options = []
    for key in tweaks:
        if key in LAUNCH_TWEAKS:
            label, option = LAUNCH_TWEAKS[key]
            labels.append(label)
            launch_options.append(option)
    return {"file": str(engine), "tweaks": labels, "count": len(labels), "launch_options": launch_options}

def clear_engine_tweaks(root: str) -> dict[str, object]:
    files = _config_candidates(root)
    engine = next((p for p in files if p.name == "Engine.ini"), None)
    if engine is None or not engine.exists():
        raise FileNotFoundError("Engine.ini was not found in the selected folder.")
    backup_game_configs(str(engine.parent))
    text = engine.read_text(encoding="utf-8", errors="ignore")
    removed = 0
    for start, end in (("; BEGIN STANKYTOOLS TWEAKS", "; END STANKYTOOLS TWEAKS"), ("; BEGIN STANKYTOOLS PROFILE", "; END STANKYTOOLS PROFILE")):
        while start in text and end in text:
            a = text.index(start)
            b = text.index(end, a) + len(end)
            text = text[:a].rstrip() + "\n" + text[b:].lstrip()
            removed += 1
    engine.write_text(text.rstrip() + "\n", encoding="utf-8")
    return {"file": str(engine), "removed": removed}


def apply_engine_profile(root: str, profile: str) -> dict[str, object]:
    files = _config_candidates(root)
    engine = next((p for p in files if p.name == "Engine.ini"), None)
    if engine is None:
        base = Path(root).expanduser() if root else Path.home()
        if not base.exists():
            raise FileNotFoundError("Selected folder does not exist.")
        engine = base / "Engine.ini"
        if not engine.exists():
            engine.write_text("", encoding="utf-8")
    backup_game_configs(str(engine.parent))
    text = engine.read_text(encoding="utf-8", errors="ignore") if engine.exists() else ""
    start = "; BEGIN STANKYTOOLS PROFILE"
    end = "; END STANKYTOOLS PROFILE"
    while start in text and end in text:
        a = text.index(start)
        b = text.index(end, a) + len(end)
        text = text[:a].rstrip() + "\n" + text[b:].lstrip()
    if profile == "performance":
        block = """
; BEGIN STANKYTOOLS PROFILE performance
; Reversible quality-of-life profile. Review values before use.
[SystemSettings]
r.MotionBlurQuality=0
r.FilmGrain=0
r.BloomQuality=3
r.LensFlareQuality=0
; END STANKYTOOLS PROFILE
"""
    else:
        block = """
; BEGIN STANKYTOOLS PROFILE balanced
; Reversible balanced profile. Review values before use.
[SystemSettings]
r.MotionBlurQuality=0
r.FilmGrain=0
r.BloomQuality=4
r.LensFlareQuality=1
; END STANKYTOOLS PROFILE
"""
    engine.write_text(text.rstrip() + "\n" + block.lstrip(), encoding="utf-8")
    return {"file": str(engine), "profile": profile}

def _first_value(obj: dict, keys: Iterable[str], default: str = "") -> str:
    for key in keys:
        if key in obj and obj.get(key) not in (None, ""):
            value = obj.get(key)
            if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=False)
            return str(value)
    return default


def _flatten_json_rows(data) -> list[dict]:
    """Return candidate item rows from dune-admin JSON structures.

    dune-admin has shipped data in files such as item-data.json, quality-data.json,
    skillModules.json, tags-data.json, and vehicles.json. This importer accepts list
    files, object maps keyed by template ID/name, and wrappers like {items,data,rows}.
    """
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if not isinstance(data, dict):
        return []
    for key in ("items", "data", "rows", "results", "records", "templates", "vehicles", "skillModules", "tags"):
        value = data.get(key)
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]
        if isinstance(value, dict):
            return _flatten_json_rows(value)
    rows: list[dict] = []
    for key, value in data.items():
        if isinstance(value, dict):
            row = dict(value)
            row.setdefault("templateId", key)
            rows.append(row)
    return rows


def _infer_category(row: dict, source_name: str) -> str:
    explicit = _first_value(row, ("category", "Category", "type", "Type", "itemType", "kind", "group", "class"), "")
    if explicit:
        return explicit
    lower = source_name.lower()
    if "vehicle" in lower:
        return "Vehicle"
    if "skill" in lower:
        return "Skill Module"
    if "tag" in lower:
        return "Tag"
    if "quality" in lower:
        return "Quality"
    return "Item"


def _display_name(row: dict) -> str:
    return _first_value(row, (
        "name", "displayName", "display_name", "itemName", "friendlyName", "localizedName",
        "label", "title", "Name", "DisplayName", "FriendlyName", "templateName", "templateId", "id"
    ), "").strip()


def import_dune_admin_json(path: str | Path) -> int:
    """Import dune-admin JSON data into the local companion catalog.

    Supported best-effort files include item-data.json, quality-data.json,
    skillModules.json, tags-data.json, vehicles.json, and similarly shaped exports.
    """
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    candidates = _flatten_json_rows(data)
    conn = connect()
    imported = 0
    try:
        for obj in candidates:
            if not isinstance(obj, dict):
                continue
            name = _display_name(obj)
            if not name:
                continue
            category = _infer_category(obj, p.name)
            tier = _first_value(obj, ("tier", "Tier", "itemTier", "ItemTier", "grade", "level"), "")
            rarity = _first_value(obj, ("rarity", "quality", "Quality", "Rarity", "qualityName"), "")
            stack = _first_value(obj, ("stackSize", "maxStack", "MaxStack", "stack", "stack_limit", "stackLimit"), "")
            weight = _first_value(obj, ("weight", "Weight", "mass"), "")
            volume = _first_value(obj, ("volume", "Volume", "itemVolume"), "")
            template_id = _first_value(obj, ("templateId", "template_id", "TemplateId", "id", "guid"), "")
            tags = obj.get("tags") or obj.get("Tags") or obj.get("tagIds") or obj.get("tag_ids") or []
            notes_bits = []
            if template_id:
                notes_bits.append(f"Template: {template_id}")
            if volume:
                notes_bits.append(f"Volume: {volume}")
            conn.execute(
                """
                INSERT INTO companion_items
                    (name, category, tier, rarity, stack_size, weight, template_id, volume, tags_json, source, notes, raw_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'dune-admin-json', ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(name) DO UPDATE SET
                    category=excluded.category,
                    tier=excluded.tier,
                    rarity=excluded.rarity,
                    stack_size=excluded.stack_size,
                    weight=excluded.weight,
                    template_id=excluded.template_id,
                    volume=excluded.volume,
                    tags_json=excluded.tags_json,
                    source=excluded.source,
                    notes=excluded.notes,
                    raw_json=excluded.raw_json,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (name, category, tier, rarity, stack, weight, template_id, volume, json.dumps(tags, ensure_ascii=False), " • ".join(notes_bits), json.dumps(obj, ensure_ascii=False)),
            )
            imported += 1
        conn.commit()
        return imported
    finally:
        conn.close()


def import_dune_admin_folder(folder: str | Path) -> dict[str, int]:
    folder_path = Path(folder)
    preferred = [
        "item-data.json",
        "quality-data.json",
        "skillModules.json",
        "tags-data.json",
        "vehicles.json",
    ]
    files: list[Path] = []
    for name in preferred:
        matches = list(folder_path.rglob(name))
        files.extend(matches)
    if not files:
        files = list(folder_path.rglob("*.json"))
    total = 0
    used = 0
    seen: set[Path] = set()
    for file_path in files:
        if file_path in seen:
            continue
        seen.add(file_path)
        try:
            count = import_dune_admin_json(file_path)
        except Exception:
            continue
        if count:
            used += 1
            total += count
    return {"files": used, "items": total}


# -----------------------------
# Web catalog / recipe importers
# -----------------------------

DUNE_ADMIN_RAW_URLS = [
    "https://raw.githubusercontent.com/Icehunter/dune-admin/main/item-data.json",
    "https://raw.githubusercontent.com/Icehunter/dune-admin/main/quality-data.json",
    "https://raw.githubusercontent.com/Icehunter/dune-admin/main/skillModules.json",
    "https://raw.githubusercontent.com/Icehunter/dune-admin/main/tags-data.json",
    "https://raw.githubusercontent.com/Icehunter/dune-admin/main/vehicles.json",
]

SERVER_MANAGER_CATALOG_URLS = [
    "https://raw.githubusercontent.com/the4rchangel/dune-awakening-server-manager/main/public/data/item-catalog.json",
    "https://raw.githubusercontent.com/the4rchangel/dune-awakening-server-manager/main/public/data/cosmetic-catalog.json",
]

GAMING_TOOLS_CRAFTING_URL = "https://dune.gaming.tools/crafting-calculator"
GAMING_TOOLS_BASE = "https://dune.gaming.tools"


def _http_get_text(url: str, timeout: int = 45) -> str:
    import urllib.request
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "StankyTools/1.0 (+https://github.com/TheStankylegTools/Stankytools)",
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    return data.decode("utf-8", errors="replace")


def _import_dune_admin_data(name: str, data) -> int:
    candidates = _flatten_json_rows(data)
    # item-data.json in dune-admin is a huge map of template_id -> display name.
    if not candidates and isinstance(data, dict):
        candidates = [{"templateId": k, "name": v} for k, v in data.items() if isinstance(v, str)]
    conn = connect()
    imported = 0
    try:
        for obj in candidates:
            if not isinstance(obj, dict):
                continue
            name_value = _display_name(obj)
            if not name_value:
                continue
            category = _infer_category(obj, name)
            tier = _first_value(obj, ("tier", "Tier", "itemTier", "ItemTier", "grade", "level"), "")
            rarity = _first_value(obj, ("rarity", "quality", "Quality", "Rarity", "qualityName"), "")
            stack = _first_value(obj, ("stackSize", "maxStack", "MaxStack", "stack", "stack_limit", "stackLimit"), "")
            weight = _first_value(obj, ("weight", "Weight", "mass"), "")
            volume = _first_value(obj, ("volume", "Volume", "itemVolume"), "")
            template_id = _first_value(obj, ("templateId", "template_id", "TemplateId", "id", "guid"), "")
            tags = obj.get("tags") or obj.get("Tags") or obj.get("tagIds") or obj.get("tag_ids") or []
            notes_bits = []
            if template_id:
                notes_bits.append(f"Template: {template_id}")
            if volume:
                notes_bits.append(f"Volume: {volume}")
            conn.execute(
                """
                INSERT INTO companion_items
                    (name, category, tier, rarity, stack_size, weight, template_id, volume, tags_json, source, notes, raw_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(name) DO UPDATE SET
                    category=CASE WHEN excluded.category != 'Item' THEN excluded.category ELSE companion_items.category END,
                    tier=COALESCE(NULLIF(excluded.tier,''), companion_items.tier),
                    rarity=COALESCE(NULLIF(excluded.rarity,''), companion_items.rarity),
                    stack_size=COALESCE(NULLIF(excluded.stack_size,''), companion_items.stack_size),
                    weight=COALESCE(NULLIF(excluded.weight,''), companion_items.weight),
                    template_id=COALESCE(NULLIF(excluded.template_id,''), companion_items.template_id),
                    volume=COALESCE(NULLIF(excluded.volume,''), companion_items.volume),
                    tags_json=COALESCE(NULLIF(excluded.tags_json,'[]'), companion_items.tags_json),
                    source=excluded.source,
                    notes=COALESCE(NULLIF(excluded.notes,''), companion_items.notes),
                    raw_json=excluded.raw_json,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (name_value, category, tier, rarity, stack, weight, template_id, volume, json.dumps(tags, ensure_ascii=False), f"web:{name}", " • ".join(notes_bits), json.dumps(obj, ensure_ascii=False)),
            )
            imported += 1
        conn.commit()
    finally:
        conn.close()
    return imported


def import_catalog_from_web(progress=None) -> dict[str, int]:
    """Download and import the best open-source catalog JSON sources.

    This intentionally uses public GitHub raw files from open-source repositories,
    not process memory, game files, or private APIs.
    """
    stats = {"files": 0, "items": 0, "errors": 0}
    for url in DUNE_ADMIN_RAW_URLS + SERVER_MANAGER_CATALOG_URLS:
        try:
            if progress:
                progress(f"Downloading {url.rsplit('/', 1)[-1]}...")
            text = _http_get_text(url)
            data = json.loads(text)
            count = _import_dune_admin_data(url.rsplit('/', 1)[-1], data)
            stats["files"] += 1
            stats["items"] += count
            if progress:
                progress(f"Imported {count} rows from {url.rsplit('/', 1)[-1]}.")
        except Exception as exc:
            stats["errors"] += 1
            if progress:
                progress(f"Skipped {url}: {exc}")
    return stats


def _upsert_item_from_web(name: str, category: str = "Item", tier: str = "", rarity: str = "", stack: str = "", volume: str = "", url: str = "") -> None:
    if not name:
        return
    conn = connect()
    try:
        notes = f"Source: {url}" if url else "Imported from web."
        conn.execute(
            """
            INSERT INTO companion_items (name, category, tier, rarity, stack_size, volume, source, notes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'gaming-tools-web', ?, CURRENT_TIMESTAMP)
            ON CONFLICT(name) DO UPDATE SET
                category=COALESCE(NULLIF(excluded.category,''), companion_items.category),
                tier=COALESCE(NULLIF(excluded.tier,''), companion_items.tier),
                rarity=COALESCE(NULLIF(excluded.rarity,''), companion_items.rarity),
                stack_size=COALESCE(NULLIF(excluded.stack_size,''), companion_items.stack_size),
                volume=COALESCE(NULLIF(excluded.volume,''), companion_items.volume),
                source=excluded.source,
                updated_at=CURRENT_TIMESTAMP
            """,
            (name, category or "Item", tier, rarity, stack, volume, notes),
        )
        conn.commit()
    finally:
        conn.close()


def _insert_recipe(name: str, output_item: str, output_qty: int, station: str, materials: list[tuple[str, float]], notes: str = "") -> bool:
    if not output_item or not materials:
        return False
    recipe_name = name or f"{output_item} ({station or 'Crafting'})"
    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO companion_recipes (name, output_item, output_qty, station, notes)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                output_item=excluded.output_item,
                output_qty=excluded.output_qty,
                station=excluded.station,
                notes=excluded.notes
            """,
            (recipe_name, output_item, int(output_qty or 1), station, notes),
        )
        recipe_id = conn.execute("SELECT id FROM companion_recipes WHERE name=?", (recipe_name,)).fetchone()[0]
        conn.execute("DELETE FROM companion_recipe_materials WHERE recipe_id=?", (recipe_id,))
        for material, qty in materials:
            if material and qty:
                conn.execute(
                    "INSERT INTO companion_recipe_materials (recipe_id, material_name, quantity) VALUES (?, ?, ?)",
                    (recipe_id, material, float(qty)),
                )
                _upsert_item_from_web(material, "Material")
        conn.commit()
        return True
    finally:
        conn.close()


def _clean_web_text(text: str) -> str:
    import html, re
    text = html.unescape(text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_page_title(html_text: str) -> str:
    import re
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html_text, flags=re.I | re.S)
    if m:
        return _clean_web_text(re.sub(r"<[^>]+>", " ", m.group(1)))
    m = re.search(r"<title[^>]*>(.*?)</title>", html_text, flags=re.I | re.S)
    if m:
        return _clean_web_text(re.sub(r"\s*-\s*Dune.*$", "", re.sub(r"<[^>]+>", " ", m.group(1))))
    return ""


def _extract_basic_item_info(html_text: str) -> dict[str, str]:
    import re
    text = _clean_web_text(re.sub(r"<[^>]+>", " ", html_text))
    info = {"tier": "", "rarity": "", "volume": "", "stack": "", "category": "Item"}
    m = re.search(r"Tier\s+(\d+)\s+([A-Za-z]+)\s+([0-9.]+)V\s+Stack:\s*([0-9,]+)", text)
    if m:
        info.update({"tier": f"Tier {m.group(1)}", "rarity": m.group(2), "volume": m.group(3), "stack": m.group(4).replace(',', '')})
    m = re.search(r"##\s*([^#\n]+?)\s*(?:dune\.gaming\.tools|Info Comments|Crafting)", text)
    if m:
        info["category"] = _clean_web_text(m.group(1)) or "Item"
    return info


def import_gaming_tools_recipe_url(url: str) -> dict[str, int]:
    """Import recipes from one gaming.tools item/placeable page.

    This importer is intentionally page-based and user-initiated. It reads visible
    page text such as Station, Time, Output, Ingredients, and Building Ingredients.
    """
    import re
    html_text = _http_get_text(url)
    page_title = _extract_page_title(html_text)
    if not page_title:
        raise ValueError("Could not identify item name on page.")
    basic = _extract_basic_item_info(html_text)
    _upsert_item_from_web(page_title, basic.get("category", "Item"), basic.get("tier", ""), basic.get("rarity", ""), basic.get("stack", ""), basic.get("volume", ""), url)

    # Strip tags while preserving line breaks near common separators.
    text = re.sub(r"<\s*(br|/p|/div|/section|/tr|/li|h[1-6])[^>]*>", "\n", html_text, flags=re.I)
    text = _clean_web_text(re.sub(r"<[^>]+>", " ", text))

    imported = 0
    # Building Ingredients format: item xqty item xqty
    if "Building Ingredients" in text:
        seg = text.split("Building Ingredients", 1)[1]
        seg = re.split(r"Craftable Items|Used for Crafting|Sold By|Drop Locations|Comments|For Websites", seg, maxsplit=1)[0]
        mats = []
        for mat, qty in re.findall(r"([A-Z][A-Za-z0-9'’\- ]{2,80})\s+x([0-9,.]+)", seg):
            mat = _clean_web_text(mat)
            if mat.lower() in {"image", "name", "ingredients", "station", "time", "output"}:
                continue
            mats.append((mat, float(qty.replace(',', ''))))
        if mats:
            if _insert_recipe(f"{page_title} (Building)", page_title, 1, "Building", mats, f"Imported from {url}"):
                imported += 1

    # Crafting sections: Station <station> Time <time> Output xN Ingredients <mat> xQ ...
    parts = text.split("Crafting")
    for idx, part in enumerate(parts[1:], start=1):
        part = re.split(r"Additional Outputs|Sold By|Drop Locations|Used for Crafting|Craftable Items|Comments|For Websites|Crafting\s+Station", part, maxsplit=1)[0]
        station = ""
        m_station = re.search(r"Station\s+(.+?)\s+Time\s+", part)
        if m_station:
            station = _clean_web_text(m_station.group(1))
        out_qty = 1
        m_output = re.search(r"Output\s+x([0-9,.]+)", part)
        if m_output:
            out_qty = int(float(m_output.group(1).replace(',', '')))
        mats = []
        if "Ingredients" in part:
            ing = part.split("Ingredients", 1)[1]
            for mat, qty in re.findall(r"([A-Z][A-Za-z0-9'’\- ]{2,80})\s+x([0-9,.]+)", ing):
                mat = _clean_web_text(mat)
                if mat.lower() in {"image", "name", "ingredients", "station", "time", "output"}:
                    continue
                mats.append((mat, float(qty.replace(',', ''))))
        if mats:
            recipe_name = f"{page_title} ({station or 'Crafting'} #{idx})"
            if _insert_recipe(recipe_name, page_title, out_qty, station, mats, f"Imported from {url}"):
                imported += 1
    return {"items": 1, "recipes": imported}


def import_gaming_tools_crafting_index(limit: int = 75, progress=None) -> dict[str, int]:
    """Best-effort import of visible recipes from gaming.tools item/placeable pages.

    Set limit=0 for all found links. This can take a long time because it visits item
    pages politely and imports only visible crafting/building data.
    """
    import re, time as _time, urllib.parse
    index = _http_get_text(GAMING_TOOLS_CRAFTING_URL)
    hrefs = []
    for href in re.findall(r'href=["\']([^"\']+)["\']', index):
        if href.startswith("/items/") or href.startswith("/placeables/") or href.startswith("/buildables/"):
            full = urllib.parse.urljoin(GAMING_TOOLS_BASE, href)
            if full not in hrefs:
                hrefs.append(full)
    # Default to a safe limited import; the UI runs this in a background thread.
    if limit and limit > 0:
        hrefs = hrefs[:limit]
    stats = {"pages": 0, "recipes": 0, "errors": 0}
    for i, link in enumerate(hrefs, start=1):
        try:
            if progress:
                progress(f"[{i}/{len(hrefs)}] Importing recipes from {link}")
            result = import_gaming_tools_recipe_url(link)
            stats["pages"] += 1
            stats["recipes"] += result.get("recipes", 0)
            _time.sleep(0.5)
        except Exception as exc:
            stats["errors"] += 1
            if progress:
                progress(f"Skipped {link}: {exc}")
    return stats


def recipes_for_item(item_name: str) -> list[sqlite3.Row]:
    """Return recipes/building requirements that create the selected item."""
    conn = connect()
    try:
        return conn.execute(
            "SELECT * FROM companion_recipes WHERE output_item = - OR name = - ORDER BY name",
            (item_name, item_name),
        ).fetchall()
    finally:
        conn.close()


def import_recipe_url_auto(url: str, progress=None) -> dict[str, int]:
    """Import a single recipe page from the best supported public sources."""
    url = (url or "").strip()
    if not url:
        raise ValueError("No URL provided.")
    if progress:
        progress(f"Reading {url}")
    if "awakening.wiki" in url:
        return import_awakening_wiki_recipe_url(url, progress=progress)
    # Existing parser handles visible gaming.tools pages and works as a fallback.
    return import_gaming_tools_recipe_url(url)


def _normalize_amount(text: str) -> float:
    import re
    value = (text or "").replace(",", "")
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)", value)
    return float(m.group(1)) if m else 0.0


def _strip_html_lines(html_text: str) -> list[str]:
    import re, html
    # Remove script/style and image-only clutter, then turn structural tags into line breaks.
    html_text = re.sub(r"<script[^>]*>.*?</script>|<style[^>]*>.*?</style>", " ", html_text, flags=re.I | re.S)
    html_text = re.sub(r"<\s*(br|/p|/div|/tr|/li|/h[1-6]|/td|/th|/section)[^>]*>", "\n", html_text, flags=re.I)
    text = html.unescape(re.sub(r"<[^>]+>", " ", html_text))
    lines = []
    for line in text.splitlines():
        clean = " ".join(line.split()).strip()
        if clean and clean not in {"Image", "Jump to navigation", "Jump to search"}:
            lines.append(clean)
    return lines


def _extract_awakening_title(lines: list[str], fallback: str = "") -> str:
    bad = {"From Dune: Awakening Community Wiki", "Contents", "Media", "Crafting"}
    for line in lines[:12]:
        if line and line not in bad and not line.startswith("#"):
            return line.replace(" - Dune: Awakening Community Wiki", "").strip()
    return fallback


def _parse_awakening_crafted_by(lines: list[str], output_item: str, url: str = "") -> int:
    """Parse the Community Wiki 'Crafted By' lines into recipes.

    The wiki exposes pages like Spice_Melange with a Crafting > Crafted By table.
    This parser reads the visible table text: production station, ingredients,
    water/time, output, and additional outputs. It intentionally skips the
    'Ingredient In' section so double-clicking a catalog item shows what makes it.
    """
    try:
        start = next(i for i, line in enumerate(lines) if line.lower() == "crafted by")
    except StopIteration:
        return 0
    end = len(lines)
    for marker in ("Ingredient In", "Item Data", "Media"):
        for i in range(start + 1, len(lines)):
            if lines[i].lower() == marker.lower():
                end = min(end, i)
                break
    chunk = lines[start + 1:end]
    if not chunk:
        return 0
    # Known production/station line tends not to contain xN, mL, or seconds.
    recipes = []
    current_station = ""
    mats: list[tuple[str, float]] = []
    output_qty = 1
    for raw in chunk:
        line = raw.strip()
        low = line.lower()
        if not line or low in {"production types ingredients products", "ingredients", "products"}:
            continue
        if low.endswith("s") and _normalize_amount(line) and " " not in line.replace(".0s", ""):
            # time-only line like 450.0s
            continue
        # Material lines: "Spice Sand x750", "700mL Water", "Spice Melange x10".
        mat_name = ""
        qty = 0.0
        import re
        m = re.match(r"(.+?)\s+x([0-9,.]+)$", line)
        if m:
            mat_name = m.group(1).strip()
            qty = _normalize_amount(m.group(2))
        else:
            m = re.match(r"([0-9,.]+)\s*mL\s+(.+)$", line, flags=re.I)
            if m:
                mat_name = m.group(2).strip()
                qty = _normalize_amount(m.group(1))
        if mat_name:
            # Output line appears after ingredients and matches the page item.
            if mat_name.lower() == output_item.lower():
                output_qty = int(qty or 1)
                if mats:
                    recipes.append((current_station or "Crafting", output_qty, list(mats)))
                mats = []
                output_qty = 1
            else:
                mats.append((mat_name, qty or 1))
                _upsert_item_from_web(mat_name, "Material", url=url)
            continue
        # New station starts. If a previous station had uncommitted mats, preserve it.
        if line.lower() not in {output_item.lower(), "crafted by"}:
            if mats:
                recipes.append((current_station or "Crafting", output_qty, list(mats)))
                mats = []
                output_qty = 1
            current_station = line
    if mats:
        recipes.append((current_station or "Crafting", output_qty, list(mats)))
    imported = 0
    for idx, (station, out_qty, materials) in enumerate(recipes, start=1):
        clean_mats = [(m, q) for m, q in materials if m and m.lower() != output_item.lower()]
        if clean_mats and _insert_recipe(f"{output_item} ({station} #{idx})", output_item, out_qty or 1, station, clean_mats, f"Imported from Awakening Wiki: {url}"):
            imported += 1
    return imported


def import_awakening_wiki_recipe_url(url: str, progress=None) -> dict[str, int]:
    html_text = _http_get_text(url)
    lines = _strip_html_lines(html_text)
    title = _extract_awakening_title(lines, Path(url).name.replace("_", " "))
    if not title:
        raise ValueError("Could not identify item name from Awakening Wiki page.")
    _upsert_item_from_web(title, "Item", url=url)
    recipes = _parse_awakening_crafted_by(lines, title, url=url)
    if progress:
        progress(f"Imported {recipes} recipe(s) from {title}")
    return {"items": 1, "recipes": recipes, "pages": 1, "errors": 0}


AWAKENING_WIKI_SEED_PAGES = [
    "https://awakening.wiki/Category:Recipes_by_ingredient",
    "https://awakening.wiki/Category:Items",
    "https://awakening.wiki/Category:Components",
    "https://awakening.wiki/Category:Resources",
    "https://awakening.wiki/Category:Vehicles",
    "https://awakening.wiki/Category:Placeables",
]


def _extract_awakening_links(html_text: str) -> list[str]:
    import re, urllib.parse
    links = []
    for href in re.findall(r'href=["\'](/[^"\'#?:]+)["\']', html_text):
        if any(skip in href for skip in ("/File:", "/Template:", "/Special:", "/Help:", "/User:", "/Category:")):
            continue
        if href == "/Main_Page":
            continue
        full = urllib.parse.urljoin("https://awakening.wiki", href)
        if full not in links:
            links.append(full)
    return links


def import_recipes_from_best_web_sources(progress=None, max_pages: int = 40, stop_check=None) -> dict[str, int]:
    """Background-safe best-effort recipe importer.

    Primary source: Awakening Community Wiki recipe sections because item pages
    expose 'Crafted By' tables with ingredients and outputs. This avoids the old
    blocking gaming.tools bulk scan that could appear frozen. Gaming.tools remains
    only a limited fallback because it has a public calculator but no confirmed
    open recipe JSON feed.
    """
    import time as _time
    stats = {"pages": 0, "recipes": 0, "errors": 0}
    candidate_pages: list[str] = []
    for seed in AWAKENING_WIKI_SEED_PAGES:
        try:
            if progress:
                progress(f"Scanning {seed}")
            html_text = _http_get_text(seed, timeout=30)
            for link in _extract_awakening_links(html_text):
                if link not in candidate_pages:
                    candidate_pages.append(link)
        except Exception as exc:
            stats["errors"] += 1
            if progress:
                progress(f"Skipped seed {seed}: {exc}")
    # Keep the first run practical. Users can import direct URLs for anything missing.
    try:
        max_pages = max(1, int(max_pages or 40))
    except Exception:
        max_pages = 40
    candidate_pages = candidate_pages[:max_pages]
    if not candidate_pages and progress:
        progress("No Awakening Wiki links found; trying limited gaming.tools fallback.")
    for idx, link in enumerate(candidate_pages, start=1):
        if stop_check and stop_check():
            if progress:
                progress(f"Import cancelled after {stats.get('pages', 0)} pages.")
            break
        try:
            if progress:
                progress(f"[{idx}/{len(candidate_pages)}] Reading {link.rsplit('/', 1)[-1].replace('_', ' ')}")
            result = import_awakening_wiki_recipe_url(link, progress=None)
            stats["pages"] += 1
            stats["recipes"] += result.get("recipes", 0)
            _time.sleep(0.1)
        except Exception:
            stats["errors"] += 1
    if stats["recipes"] == 0 and not (stop_check and stop_check()):
        try:
            if progress:
                progress("Trying limited gaming.tools fallback import...")
            gt = import_gaming_tools_crafting_index(limit=40, progress=progress)
            stats["pages"] += gt.get("pages", 0)
            stats["recipes"] += gt.get("recipes", 0)
            stats["errors"] += gt.get("errors", 0)
        except Exception:
            stats["errors"] += 1
    return stats


BLUEPRINT_MARKET_URLS = [
    "https://dune.layout.tools/",
    "https://dune.layout.tools/api/blueprints",
    "https://dune.layout.tools/api/layouts",
]


def _upsert_blueprint_from_web(name: str, base_type: str = "", players: str = "", tags: str = "", power_notes: str = "", material_notes: str = "", layout_json: str = "") -> bool:
    name = (name or "").strip()
    if not name:
        return False
    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO companion_blueprints
            (name, base_type, players_recommended, tags, power_notes, material_notes, layout_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(name) DO UPDATE SET
                base_type=COALESCE(NULLIF(excluded.base_type,''), companion_blueprints.base_type),
                players_recommended=COALESCE(NULLIF(excluded.players_recommended,''), companion_blueprints.players_recommended),
                tags=COALESCE(NULLIF(excluded.tags,''), companion_blueprints.tags),
                power_notes=COALESCE(NULLIF(excluded.power_notes,''), companion_blueprints.power_notes),
                material_notes=COALESCE(NULLIF(excluded.material_notes,''), companion_blueprints.material_notes),
                layout_json=COALESCE(NULLIF(excluded.layout_json,''), companion_blueprints.layout_json),
                updated_at=CURRENT_TIMESTAMP
            """,
            (name, base_type, players, tags, power_notes, material_notes, layout_json),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def _import_blueprint_objects(data) -> int:
    """Best-effort import for blueprint-market/API style JSON objects."""
    def flatten(obj):
        if isinstance(obj, list):
            for v in obj:
                yield from flatten(v)
        elif isinstance(obj, dict):
            # Treat dictionaries with a name/title as candidate blueprint records, but also walk nested lists.
            if any(k in obj for k in ("name", "title", "displayName", "display_name")):
                yield obj
            for v in obj.values():
                if isinstance(v, (list, dict)):
                    yield from flatten(v)
    count = 0
    for obj in flatten(data):
        name = _first_value(obj, ("name", "title", "displayName", "display_name", "blueprintName"))
        base_type = _first_value(obj, ("base_type", "type", "category", "kind"))
        players = _first_value(obj, ("players", "players_recommended", "recommendedPlayers"))
        tags_val = obj.get("tags", "") if isinstance(obj, dict) else ""
        if isinstance(tags_val, list):
            tags = ", ".join(str(t) for t in tags_val)
        elif isinstance(tags_val, dict):
            tags = ", ".join(str(v) for v in tags_val.values())
        else:
            tags = str(tags_val or "")
        power_notes = _first_value(obj, ("power_notes", "power", "powerNotes"))
        material_notes = _first_value(obj, ("material_notes", "materials", "cost", "description", "notes"))
        layout_json = json.dumps(obj, ensure_ascii=False)
        if _upsert_blueprint_from_web(name, base_type, players, tags, power_notes, material_notes, layout_json):
            count += 1
    return count


def import_blueprints_from_web(progress=None) -> dict[str, int]:
    """Best-effort import from the public blueprint market concept.

    The endpoint format may change, so this tries common JSON endpoints first and
    then falls back to visible page titles/cards if JSON is not available.
    """
    import re
    stats = {"blueprints": 0, "errors": 0}
    for url in BLUEPRINT_MARKET_URLS:
        try:
            if progress:
                progress(f"Checking {url}")
            text = _http_get_text(url)
            try:
                data = json.loads(text)
                stats["blueprints"] += _import_blueprint_objects(data)
                continue
            except Exception:
                pass
            # HTML fallback: import visible card/title-like names, if any.
            titles = []
            for pattern in (r'<h[123][^>]*>(.*?)</h[123]>', r'title["\']?\s*[:=]\s*["\']([^"\']{3,100})'):
                for match in re.findall(pattern, text, flags=re.I | re.S):
                    clean = _clean_web_text(re.sub(r"<[^>]+>", " ", match))
                    if clean and clean.lower() not in {"dune layout tools", "blueprints", "login"} and clean not in titles:
                        titles.append(clean)
            for title in titles:
                if _upsert_blueprint_from_web(title, "Blueprint Market", "", "web-import", "", f"Imported/seen from {url}", ""):
                    stats["blueprints"] += 1
        except Exception:
            stats["errors"] += 1
    return stats

# ---------------------------------------------------------------------------
# Local export catalog support (built from bundled exports data)
# ---------------------------------------------------------------------------

def _ensure_export_columns(conn: sqlite3.Connection) -> None:
    for ddl in (
        "ALTER TABLE companion_items ADD COLUMN image_path TEXT DEFAULT ''",
        "ALTER TABLE companion_items ADD COLUMN source_url TEXT DEFAULT ''",
        "ALTER TABLE companion_items ADD COLUMN subcategory TEXT DEFAULT ''",
        "ALTER TABLE companion_items ADD COLUMN item_id TEXT DEFAULT ''",
        "ALTER TABLE companion_items ADD COLUMN power_cost REAL DEFAULT 0",
        "ALTER TABLE companion_items ADD COLUMN power_generated REAL DEFAULT 0",
        "ALTER TABLE companion_items ADD COLUMN water_gained_per_day REAL DEFAULT 0",
    ):
        try:
            conn.execute(ddl)
        except sqlite3.OperationalError:
            pass


def _exports_root() -> Path:
    candidates = [
        Path(__file__).resolve().parents[2] / "assets" / "exports",
        Path.cwd() / "assets" / "exports",
        data_dir() / "exports",
        Path(__file__).resolve().parents[2] / "data" / "exports",
        Path.cwd() / "data" / "exports",
    ]
    for candidate in candidates:
        if (candidate / "dune_catalog.json").exists():
            return candidate
    return candidates[0]


def export_catalog_available() -> bool:
    return (_exports_root() / "dune_catalog.json").exists()


def export_catalog_path() -> str:
    return str(_exports_root() / "dune_catalog.json")


def _safe_json_load(value, default):
    if isinstance(value, (dict, list)):
        return value
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def _clean_text(value: object) -> str:
    return str(value or "").replace("\u00a0", " ").strip()


def _normalize_tier(value: object) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    digits = "".join(ch for ch in text if ch.isdigit())
    return digits or text


def _parse_materials_from_segment(segment: str) -> list[tuple[str, float]]:
    segment = _clean_text(segment)
    if not segment:
        return []
    # Remove common table words and time suffixes from the input side.
    segment = re.sub(r"\b(Production Types|Ingredients|Products|Output)\b", " ", segment, flags=re.I)
    segment = re.sub(r"\b\d+(?:\.\d+)?s\b", " ", segment)
    materials: list[tuple[str, float]] = []
    matches = list(re.finditer(r"\s+x\s*(\d+(?:\.\d+)?)", segment, flags=re.I))
    start = 0
    for match in matches:
        name = segment[start:match.start()].strip(" ,;|-/")
        if name:
            name = re.sub(r"\s+", " ", name)
            try:
                qty = float(match.group(1))
            except Exception:
                qty = 1.0
            materials.append((name, qty))
        start = match.end()
    tail = segment[start:]
    for water_qty in re.findall(r"(\d+(?:\.\d+)?)\s*mL\s+Water", tail, flags=re.I):
        try:
            materials.append(("Water", float(water_qty)))
        except Exception:
            pass
    # Deduplicate within a recipe.
    totals: dict[str, float] = {}
    for name, qty in materials:
        if len(name) > 80:
            continue
        if name.lower() in {"and", "or", "products", "ingredients"}:
            continue
        totals[name] = totals.get(name, 0.0) + qty
    return sorted(totals.items(), key=lambda x: x[0].lower())


def _recipe_rows_from_export_item(item: dict) -> list[dict]:
    name = _clean_text(item.get("name"))
    if not name:
        return []
    recipe_payload = _safe_json_load(item.get("recipe"), {})
    raw_payload = _safe_json_load(item.get("raw"), {})
    sections = raw_payload.get("sections", {}) if isinstance(raw_payload, dict) else {}
    fields = raw_payload.get("fields", {}) if isinstance(raw_payload, dict) else {}
    text = _clean_text(recipe_payload.get("Crafted By") if isinstance(recipe_payload, dict) else "")
    if not text and isinstance(sections, dict):
        text = _clean_text(sections.get("Crafted By"))
    rows: list[dict] = []
    station_names = []
    if isinstance(fields, dict):
        for key in fields.keys():
            k = _clean_text(key)
            if any(word in k.lower() for word in ("fabricator", "refinery", "processor", "assembler", "furnace", "purifier")):
                station_names.append(k)
    if not station_names:
        station_names = [
            "Advanced Weapons Fabricator", "Weapons Fabricator", "Advanced Vehicle Fabricator", "Vehicle Fabricator",
            "Advanced Garment Fabricator", "Wearables Fabricator", "Advanced Survival Fabricator", "Survival Fabricator",
            "Large Ore Refinery", "Medium Ore Refinery", "Small Ore Refinery", "Chemical Refinery",
            "Fabricator", "Refinery",
        ]
    station_names = sorted(set(station_names), key=len, reverse=True)
    if text:
        positions = []
        for station in station_names:
            idx = text.find(station)
            while idx >= 0:
                positions.append((idx, station))
                idx = text.find(station, idx + 1)
        positions.sort()
        for i, (idx, station) in enumerate(positions):
            start = idx + len(station)
            end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
            segment = text[start:end].strip()
            time_match = re.search(r"\d+(?:\.\d+)?s", segment)
            before_time = segment[:time_match.start()].strip() if time_match else segment
            after_time = segment[time_match.end():].strip() if time_match else ""
            output_qty = 1
            out_match = re.search(re.escape(name) + r"\s+x\s*(\d+(?:\.\d+)?)", after_time, flags=re.I)
            if out_match:
                try:
                    output_qty = max(1, int(float(out_match.group(1))))
                except Exception:
                    output_qty = 1
            materials = _parse_materials_from_segment(before_time)
            if materials:
                rows.append({"station": station, "output_qty": output_qty, "materials": materials})
    # Fallback for single craftable item pages where fields contain the station recipe directly.
    if not rows and isinstance(fields, dict):
        for station, value in fields.items():
            station = _clean_text(station)
            if not any(word in station.lower() for word in ("fabricator", "refinery", "processor", "assembler")):
                continue
            segment = _clean_text(value)
            time_match = re.search(r"\d+(?:\.\d+)?s", segment)
            before_time = segment[:time_match.start()].strip() if time_match else segment
            materials = _parse_materials_from_segment(before_time)
            if materials:
                rows.append({"station": station, "output_qty": 1, "materials": materials})
    # Avoid importing obvious "used in" rows for raw resources that don't produce the current item.
    cleaned: list[dict] = []
    seen = set()
    for row in rows:
        key = (row["station"], tuple(row["materials"]))
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(row)
    return cleaned


def import_catalog_from_exports(progress=None, reset: bool = False) -> dict[str, int]:
    """Import the bundled exports catalog and recipe data into the companion DB."""
    root = _exports_root()
    catalog_file = root / "dune_catalog.json"
    if not catalog_file.exists():
        return reload_bundled_catalog(progress=progress)
    if progress:
        progress("Reading bundled Dune export catalog...")
    data = json.loads(catalog_file.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("dune_catalog.json must contain a list of items")
    conn = connect()
    _ensure_export_columns(conn)
    imported_items = imported_recipes = imported_materials = errors = 0
    try:
        if reset:
            conn.execute("DELETE FROM companion_recipe_materials")
            conn.execute("DELETE FROM companion_recipes")
            conn.execute("DELETE FROM companion_items")
        for index, item in enumerate(data, 1):
            try:
                name = _clean_text(item.get("name"))
                if not name:
                    continue
                if progress and (index == 1 or index % 75 == 0):
                    progress(f"Importing catalog {index:,}/{len(data):,}: {name}")
                raw = _safe_json_load(item.get("raw"), {})
                fields = raw.get("fields", {}) if isinstance(raw, dict) else {}
                image_path = _clean_text(item.get("local_image"))
                if image_path:
                    image_path = image_path.replace("exports\\", "").replace("exports/", "")
                    possible = root / image_path.replace("\\", "/")
                    image_path = str(possible) if possible.exists() else ""
                category = _clean_text(item.get("category")) or "Item"
                subcategory = _clean_text(item.get("subcategory"))
                tier = _normalize_tier(item.get("tier") or item.get("grade"))
                rarity = _clean_text(item.get("rarity"))
                stack_size = _clean_text(item.get("stack_size") or fields.get("Stack Size") if isinstance(fields, dict) else "")
                weight = _clean_text(item.get("weight"))
                volume = _clean_text(item.get("volume") or fields.get("Volume") if isinstance(fields, dict) else "")
                notes = _clean_text(item.get("description"))
                item_id = _clean_text(item.get("template_id") or fields.get("Item ID") or fields.get("Name") if isinstance(fields, dict) else "")
                conn.execute(
                    """
                    INSERT INTO companion_items
                    (name, category, subcategory, tier, rarity, stack_size, weight, template_id, item_id, volume, source, source_url, image_path, notes, raw_json, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'export', ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(name) DO UPDATE SET
                        category=excluded.category,
                        subcategory=excluded.subcategory,
                        tier=excluded.tier,
                        rarity=excluded.rarity,
                        stack_size=excluded.stack_size,
                        weight=excluded.weight,
                        template_id=excluded.template_id,
                        item_id=excluded.item_id,
                        volume=excluded.volume,
                        source='export',
                        source_url=excluded.source_url,
                        image_path=excluded.image_path,
                        notes=excluded.notes,
                        raw_json=excluded.raw_json,
                        updated_at=CURRENT_TIMESTAMP
                    """,
                    (name, category, subcategory, tier, rarity, stack_size, weight, _clean_text(item.get("template_id")), item_id, volume, _clean_text(item.get("source_url")), image_path, notes, json.dumps(item, ensure_ascii=False)),
                )
                imported_items += 1
                for rec_index, recipe in enumerate(_recipe_rows_from_export_item(item), 1):
                    recipe_name = f"{name} - {recipe['station']}"
                    conn.execute(
                        """
                        INSERT INTO companion_recipes (name, output_item, output_qty, station, notes)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(name) DO UPDATE SET
                            output_item=excluded.output_item,
                            output_qty=excluded.output_qty,
                            station=excluded.station,
                            notes=excluded.notes
                        """,
                        (recipe_name, name, int(recipe.get("output_qty") or 1), recipe["station"], "Imported from bundled exports catalog."),
                    )
                    recipe_id = conn.execute("SELECT id FROM companion_recipes WHERE name=?", (recipe_name,)).fetchone()[0]
                    conn.execute("DELETE FROM companion_recipe_materials WHERE recipe_id=?", (recipe_id,))
                    for mat_name, qty in recipe["materials"]:
                        conn.execute(
                            "INSERT INTO companion_recipe_materials (recipe_id, material_name, quantity) VALUES (?, ?, ?)",
                            (recipe_id, mat_name, float(qty)),
                        )
                        imported_materials += 1
                    imported_recipes += 1
            except Exception:
                errors += 1
        conn.commit()
        if progress:
            progress(f"Imported {imported_items:,} items and {imported_recipes:,} recipes from bundled exports.")
        return {"items": imported_items, "recipes": imported_recipes, "materials": imported_materials, "errors": errors, "source": str(catalog_file)}
    finally:
        conn.close()


def import_catalog_from_web(progress=None) -> dict[str, int]:
    """Compatibility name: use the bundled exports instead of slow web importing."""
    return import_catalog_from_exports(progress=progress, reset=False)


def clear_imported_catalog_items(include_recipes: bool = True) -> dict[str, int]:
    conn = connect()
    _ensure_export_columns(conn)
    try:
        item_count = conn.execute("SELECT COUNT(*) FROM companion_items").fetchone()[0]
        recipe_count = material_count = 0
        if include_recipes:
            recipe_count = conn.execute("SELECT COUNT(*) FROM companion_recipes").fetchone()[0]
            material_count = conn.execute("SELECT COUNT(*) FROM companion_recipe_materials").fetchone()[0]
            conn.execute("DELETE FROM companion_recipe_materials")
            conn.execute("DELETE FROM companion_recipes")
        conn.execute("DELETE FROM companion_items")
        conn.execute("INSERT OR REPLACE INTO companion_settings (key, value) VALUES ('catalog_disabled', '1')")
        conn.commit()
        return {"items": int(item_count), "recipes": int(recipe_count), "materials": int(material_count)}
    finally:
        conn.close()


def build_calculator_items() -> list[sqlite3.Row]:
    conn = connect()
    _ensure_export_columns(conn)
    try:
        return conn.execute(
            "SELECT id, name, category, subcategory, image_path, "
            "COALESCE(power_cost, 0) AS power_cost, "
            "COALESCE(power_generated, 0) AS power_generated, "
            "COALESCE(water_gained_per_day, 0) AS water_gained_per_day "
            "FROM companion_items "
            "WHERE LOWER(COALESCE(category, '')) = 'placeable' "
            "AND (COALESCE(power_cost, 0) != 0 OR COALESCE(power_generated, 0) != 0 OR COALESCE(water_gained_per_day, 0) != 0) "
            "ORDER BY name"
        ).fetchall()
    finally:
        conn.close()


def list_items(search: str = "", category: str = "") -> list[sqlite3.Row]:
    conn = connect()
    _ensure_export_columns(conn)
    try:
        where = []
        params: list[str] = []
        if search.strip():
            where.append("(name LIKE - OR notes LIKE - OR template_id LIKE - OR item_id LIKE - OR tags_json LIKE - OR subcategory LIKE ?)")
            params.extend([f"%{search.strip()}%"] * 6)
        if category.strip() and category != "All":
            where.append("category = ?")
            params.append(category)
        clause = "WHERE " + " AND ".join(where) if where else ""
        return conn.execute(f"SELECT * FROM companion_items {clause} ORDER BY category, subcategory, name LIMIT 600", params).fetchall()
    finally:
        conn.close()


def get_item(name: str) -> sqlite3.Row | None:
    conn = connect()
    _ensure_export_columns(conn)
    try:
        return conn.execute("SELECT * FROM companion_items WHERE name=?", (name,)).fetchone()
    finally:
        conn.close()


def item_categories() -> list[str]:
    conn = connect()
    _ensure_export_columns(conn)
    try:
        rows = conn.execute("SELECT DISTINCT category FROM companion_items ORDER BY category").fetchall()
        return [r[0] for r in rows if r[0]]
    finally:
        conn.close()



def craftable_item_names() -> set[str]:
    conn = connect()
    try:
        return {str(r[0]) for r in conn.execute("SELECT DISTINCT output_item FROM companion_recipes WHERE COALESCE(output_item,'') != ''").fetchall()}
    finally:
        conn.close()

def catalog_stats() -> dict[str, int]:
    conn = connect()
    _ensure_export_columns(conn)
    try:
        return {
            "items": conn.execute("SELECT COUNT(*) FROM companion_items").fetchone()[0],
            "recipes": conn.execute("SELECT COUNT(*) FROM companion_recipes").fetchone()[0],
            "categories": conn.execute("SELECT COUNT(DISTINCT category) FROM companion_items WHERE COALESCE(category,'') != ''").fetchone()[0],
            "images": conn.execute("SELECT COUNT(*) FROM companion_items WHERE COALESCE(image_path,'') != ''").fetchone()[0],
        }
    finally:
        conn.close()

# Improve the export import with useful category inference when the export rows are sparse.
def _infer_export_category(item: dict, fields: dict) -> tuple[str, str]:
    name = _clean_text(item.get("name"))
    hay = (name + " " + " ".join(str(k) for k in (fields or {}).keys()) + " " + " ".join(str(v) for v in (fields or {}).values())).lower()
    if any(k in hay for k in ("fire mode", "damage type", "rpm", "magazine", "lasgun", "pistol", "rifle", "sword", "dirk", "rapier", "drillshot", "disruptor", "vulcan", "jabal", "kindjal")):
        return "Weapons", "Ranged" if any(k in hay for k in ("pistol", "rifle", "gun", "lasgun", "drillshot", "disruptor", "vulcan", "jabal", "dart")) else "Melee"
    if any(k in hay for k in ("garment type", "armor value", "mitigation", "stillsuit", "boots", "chestplate", "gauntlets", "helmet", "pants", "jacket", "gloves", "mask", "hood")):
        return "Garments", "Armor"
    if any(k in hay for k in ("ornithopter", "buggy", "sandbike", "crawler", "vehicle", "chassis", "cabin", "cockpit", "engine", "thruster", "wing module", "tread")):
        return "Vehicle", "Parts"
    if any(k in hay for k in ("fabricator", "refinery", "deathstill", "sub-fief", "console", "generator", "placeable", "lights set", "furniture set")):
        return "Placeables", "Stations/Utilities"
    if any(k in hay for k in ("roof", "wall", "door", "foundation", "stairs", "ramp", "floor", "building")):
        return "Buildings", "Pieces"
    if any(k in hay for k in ("ingot", "ore", "dust", "water", "fiber", "parts", "plating", "silicone", "spice", "cobalt", "crystal", "paste", "resource", "component", "mechanical", "machinery", "capacitor", "compressor")):
        return "Misc", "Resource / Component"
    if any(k in hay for k in ("schematic", "intel", "log", "report", "letter")):
        return "Misc", "Intel / Schematic"
    return "Item", ""

# Final override after category inference helpers are defined.
def import_catalog_from_exports(progress=None, reset: bool = False) -> dict[str, int]:
    if reset and bundled_catalog_db_path().exists():
        return reload_bundled_catalog(progress=progress)
    root = _exports_root()
    catalog_file = root / "dune_catalog.json"
    if not catalog_file.exists():
        return reload_bundled_catalog(progress=progress)
    if progress:
        progress("Reading bundled Dune export catalog...")
    data = json.loads(catalog_file.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("dune_catalog.json must contain a list of items")
    conn = connect()
    _ensure_export_columns(conn)
    imported_items = imported_recipes = imported_materials = errors = 0
    try:
        if reset:
            conn.execute("DELETE FROM companion_recipe_materials")
            conn.execute("DELETE FROM companion_recipes")
            conn.execute("DELETE FROM companion_items")
        for index, item in enumerate(data, 1):
            try:
                name = _clean_text(item.get("name"))
                if not name:
                    continue
                if progress and (index == 1 or index % 75 == 0):
                    progress(f"Importing catalog {index:,}/{len(data):,}: {name}")
                raw = _safe_json_load(item.get("raw"), {})
                fields = raw.get("fields", {}) if isinstance(raw, dict) else {}
                image_path = _clean_text(item.get("local_image"))
                if image_path:
                    image_path = image_path.replace("exports\\", "").replace("exports/", "")
                    possible = root / image_path.replace("\\", "/")
                    image_path = str(possible) if possible.exists() else ""
                inferred_category, inferred_sub = _infer_export_category(item, fields if isinstance(fields, dict) else {})
                category = _clean_text(item.get("category")) or inferred_category
                if category.lower() in {"added", "key", "value", "all categories"}:
                    category = inferred_category
                subcategory = _clean_text(item.get("subcategory")) or inferred_sub
                tier = _normalize_tier(item.get("tier") or item.get("grade"))
                rarity = _clean_text(item.get("rarity")) or ("Unique" if _clean_text(fields.get("Unique Schematic") if isinstance(fields, dict) else "").lower() == "yes" else "")
                stack_size = _clean_text(item.get("stack_size") or (fields.get("Stack Size") if isinstance(fields, dict) else ""))
                weight = _clean_text(item.get("weight"))
                volume = _clean_text(item.get("volume") or (fields.get("Volume") if isinstance(fields, dict) else ""))
                notes = _clean_text(item.get("description") or (fields.get("Long Description") if isinstance(fields, dict) else ""))
                item_id = _clean_text(item.get("template_id") or (fields.get("Item ID") if isinstance(fields, dict) else "") or (fields.get("Name") if isinstance(fields, dict) else ""))
                conn.execute(
                    """
                    INSERT INTO companion_items
                    (name, category, subcategory, tier, rarity, stack_size, weight, template_id, item_id, volume, source, source_url, image_path, notes, raw_json, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'export', ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(name) DO UPDATE SET
                        category=excluded.category,
                        subcategory=excluded.subcategory,
                        tier=excluded.tier,
                        rarity=excluded.rarity,
                        stack_size=excluded.stack_size,
                        weight=excluded.weight,
                        template_id=excluded.template_id,
                        item_id=excluded.item_id,
                        volume=excluded.volume,
                        source='export',
                        source_url=excluded.source_url,
                        image_path=excluded.image_path,
                        notes=excluded.notes,
                        raw_json=excluded.raw_json,
                        updated_at=CURRENT_TIMESTAMP
                    """,
                    (name, category, subcategory, tier, rarity, stack_size, weight, _clean_text(item.get("template_id")), item_id, volume, _clean_text(item.get("source_url")), image_path, notes, json.dumps(item, ensure_ascii=False)),
                )
                imported_items += 1
                for recipe in _recipe_rows_from_export_item(item):
                    recipe_name = f"{name} - {recipe['station']}"
                    conn.execute(
                        """
                        INSERT INTO companion_recipes (name, output_item, output_qty, station, notes)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(name) DO UPDATE SET
                            output_item=excluded.output_item,
                            output_qty=excluded.output_qty,
                            station=excluded.station,
                            notes=excluded.notes
                        """,
                        (recipe_name, name, int(recipe.get("output_qty") or 1), recipe["station"], "Imported from bundled exports catalog."),
                    )
                    recipe_id = conn.execute("SELECT id FROM companion_recipes WHERE name=?", (recipe_name,)).fetchone()[0]
                    conn.execute("DELETE FROM companion_recipe_materials WHERE recipe_id=?", (recipe_id,))
                    for mat_name, qty in recipe["materials"]:
                        conn.execute("INSERT INTO companion_recipe_materials (recipe_id, material_name, quantity) VALUES (?, ?, ?)", (recipe_id, mat_name, float(qty)))
                        imported_materials += 1
                    imported_recipes += 1
            except Exception:
                errors += 1
        conn.commit()
        if progress:
            progress(f"Imported {imported_items:,} items and {imported_recipes:,} recipes from bundled exports.")
        return {"items": imported_items, "recipes": imported_recipes, "materials": imported_materials, "errors": errors, "source": str(catalog_file)}
    finally:
        conn.close()

# Keep compatibility after overriding import_catalog_from_exports.
def import_catalog_from_web(progress=None) -> dict[str, int]:
    return import_catalog_from_exports(progress=progress, reset=False)
