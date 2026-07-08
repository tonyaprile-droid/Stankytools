from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class PersistentQueueItem:
    table: str
    action: str
    payload: Dict
    id: str = field(default_factory=lambda: str(uuid4()))
    retries: int = 0
    created_at: str = field(default_factory=_utc_now)
    last_error: Optional[str] = None


class PersistentQueue:
    """JSON-backed offline queue safe for desktop app restarts."""

    def __init__(self, queue_path: Path) -> None:
        self.queue_path = Path(queue_path)
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        self._items: List[PersistentQueueItem] = []
        self.load()

    def load(self) -> None:
        if not self.queue_path.exists():
            self._items = []
            return
        try:
            raw = json.loads(self.queue_path.read_text(encoding="utf-8"))
            self._items = [PersistentQueueItem(**item) for item in raw]
        except Exception:
            backup = self.queue_path.with_suffix(".corrupt.json")
            try:
                self.queue_path.replace(backup)
            except Exception:
                pass
            self._items = []

    def save(self) -> None:
        tmp = self.queue_path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps([asdict(item) for item in self._items], indent=2),
            encoding="utf-8",
        )
        tmp.replace(self.queue_path)

    def add(self, table: str, action: str, payload: Dict) -> PersistentQueueItem:
        item = PersistentQueueItem(table=table, action=action, payload=payload)
        self._items.append(item)
        self.save()
        return item

    def peek(self) -> Optional[PersistentQueueItem]:
        return self._items[0] if self._items else None

    def remove(self, item_id: str) -> None:
        self._items = [item for item in self._items if item.id != item_id]
        self.save()

    def mark_failed(self, item_id: str, error: str) -> None:
        for item in self._items:
            if item.id == item_id:
                item.retries += 1
                item.last_error = error
                break
        self.save()

    def clear(self) -> None:
        self._items.clear()
        self.save()

    @property
    def pending(self) -> int:
        return len(self._items)

    @property
    def items(self) -> List[PersistentQueueItem]:
        return list(self._items)
