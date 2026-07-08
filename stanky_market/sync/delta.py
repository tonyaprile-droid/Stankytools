from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .cache import SYNC_STATE_DIR


class DeltaState:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (SYNC_STATE_DIR / "last_sync.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._state: dict[str, str] = self._load()

    def key(self, guild_id: str, table: str) -> str:
        return f"{guild_id}:{table}"

    def get(self, guild_id: str, table: str) -> str | None:
        return self._state.get(self.key(guild_id, table))

    def set_now(self, guild_id: str, table: str) -> str:
        value = datetime.now(timezone.utc).isoformat()
        self._state[self.key(guild_id, table)] = value
        self.save()
        return value

    def set(self, guild_id: str, table: str, value: str) -> None:
        self._state[self.key(guild_id, table)] = value
        self.save()

    def clear_guild(self, guild_id: str) -> None:
        prefix = f"{guild_id}:"
        self._state = {k: v for k, v in self._state.items() if not k.startswith(prefix)}
        self.save()

    def _load(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def save(self) -> None:
        self.path.write_text(json.dumps(self._state, indent=2, sort_keys=True), encoding="utf-8")
