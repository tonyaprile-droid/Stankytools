from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

try:
    from stanky_market.sync.sync_manager import sync_manager
except Exception:  # keeps legacy app launch safe if SyncManager is not installed yet
    sync_manager = None


POI_TABLE = "guild_pois"
BASE_TABLE = "guild_bases"


MANAGER_ROLES = {"owner", "admin", "officer"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_role(role: str | None) -> str:
    return (role or "").strip().lower()


def can_manage_any_marker(role: str | None) -> bool:
    return normalize_role(role) in MANAGER_ROLES


def can_delete_marker(role: str | None, current_user: str | None, created_by: str | None) -> bool:
    if can_manage_any_marker(role):
        return True
    return (current_user or "").strip().lower() == (created_by or "").strip().lower()


def remote_or_client_id(row: dict[str, Any] | Any, prefix: str) -> str:
    def get(key: str, default: Any = "") -> Any:
        if isinstance(row, dict):
            return row.get(key, default)
        try:
            return row[key] if key in row.keys() else default
        except Exception:
            return default

    remote_id = str(get("remote_id", "") or "").strip()
    if remote_id:
        return remote_id
    local_id = str(get("id", "") or "").strip()
    return f"{prefix}-{local_id or uuid4()}"


class DeepDesertSyncAdapter:
    """Local-first SyncManager adapter for Deep Desert POIs and Bases.

    This does not directly call Supabase. Existing UI/db code should save locally first,
    then call this adapter to queue the remote write. This makes failed network syncs
    retryable and prevents map markers from disappearing.
    """

    def __init__(self, guild_code: str, current_user: str = "", current_role: str = ""):
        self.guild_code = (guild_code or "").strip().upper()
        self.current_user = (current_user or "").strip()
        self.current_role = normalize_role(current_role)

    def _queue(self, table: str, action: str, payload: dict[str, Any]) -> None:
        payload.setdefault("guild_code", self.guild_code)
        payload.setdefault("updated_at", now_iso())
        if sync_manager is not None and hasattr(sync_manager, "queue_change"):
            sync_manager.queue_change(table, action, payload)
        elif sync_manager is not None and hasattr(sync_manager, "queue"):
            # Backward-compatible hook for older SyncManager implementations.
            sync_manager.queue(table, immediate=True)

    # -----------------------------
    # POIs
    # -----------------------------
    def queue_poi_upsert(self, row: dict[str, Any] | Any) -> str:
        remote_id = remote_or_client_id(row, "poi")

        def get(key: str, default: Any = "") -> Any:
            if isinstance(row, dict):
                return row.get(key, default)
            try:
                return row[key] if key in row.keys() else default
            except Exception:
                return default

        payload = {
            "id": remote_id,
            "guild_code": self.guild_code,
            "name": get("label") or get("name") or get("poi_type") or "Guild POI",
            "label": get("label") or get("name") or get("poi_type") or "Guild POI",
            "poi_type": get("poi_type") or get("type") or "Custom",
            "note": get("note") or "",
            "x": float(get("x") or 0),
            "y": float(get("y") or 0),
            "status": get("status") or "active",
            "pooped_on": bool(get("pooped_on") or False),
            "created_by": get("created_by") or self.current_user,
            "updated_by": self.current_user,
            "deleted_at": None,
        }
        self._queue(POI_TABLE, "upsert", payload)
        return remote_id

    def queue_poi_status(self, row: dict[str, Any] | Any, status: str) -> str:
        remote_id = remote_or_client_id(row, "poi")
        payload = {
            "id": remote_id,
            "guild_code": self.guild_code,
            "status": status,
            "updated_by": self.current_user,
        }
        self._queue(POI_TABLE, "upsert", payload)
        return remote_id

    def queue_poi_delete(self, row: dict[str, Any] | Any) -> str:
        remote_id = remote_or_client_id(row, "poi")
        payload = {
            "id": remote_id,
            "guild_code": self.guild_code,
            "deleted_at": now_iso(),
            "updated_by": self.current_user,
        }
        self._queue(POI_TABLE, "soft_delete", payload)
        return remote_id

    # -----------------------------
    # Bases
    # -----------------------------
    def queue_base_upsert(self, row: dict[str, Any] | Any) -> str:
        remote_id = remote_or_client_id(row, "base")

        def get(key: str, default: Any = "") -> Any:
            if isinstance(row, dict):
                return row.get(key, default)
            try:
                return row[key] if key in row.keys() else default
            except Exception:
                return default

        payload = {
            "id": remote_id,
            "guild_code": self.guild_code,
            "base_name": get("base_name") or get("name") or "Guild Base",
            "seitch": get("seitch") or get("note") or "",
            "x": float(get("x") or 0),
            "y": float(get("y") or 0),
            "status": get("status") or "friendly",
            "map_key": get("map_key") or "deep_desert",
            "created_by": get("created_by") or self.current_user,
            "updated_by": self.current_user,
            "deleted_at": None,
        }
        self._queue(BASE_TABLE, "upsert", payload)
        return remote_id

    def queue_base_status(self, row: dict[str, Any] | Any, status: str) -> str:
        remote_id = remote_or_client_id(row, "base")
        payload = {
            "id": remote_id,
            "guild_code": self.guild_code,
            "status": status,
            "updated_by": self.current_user,
        }
        self._queue(BASE_TABLE, "upsert", payload)
        return remote_id

    def queue_base_delete(self, row: dict[str, Any] | Any) -> str:
        remote_id = remote_or_client_id(row, "base")
        payload = {
            "id": remote_id,
            "guild_code": self.guild_code,
            "deleted_at": now_iso(),
            "updated_by": self.current_user,
        }
        self._queue(BASE_TABLE, "soft_delete", payload)
        return remote_id
