from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .cache import cache_manager

QUEUE_FILE = cache_manager.queue / "pending_sync.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class QueueItem:
    table: str
    action: str
    payload: dict[str, Any]
    id: str = field(default_factory=lambda: str(uuid4()))
    retries: int = 0
    created_at: str = field(default_factory=now_iso)
    last_error: str | None = None


class SyncQueue:
    def __init__(self) -> None:
        self._items: list[QueueItem] = []
        self.load()

    def add(self, table: str, action: str, payload: dict[str, Any]) -> QueueItem:
        item = QueueItem(table=table, action=action, payload=payload)
        self._items.append(item)
        self.save()
        return item

    def remove(self, item_id: str) -> None:
        self._items = [item for item in self._items if item.id != item_id]
        self.save()

    def next(self) -> QueueItem | None:
        return self._items[0] if self._items else None

    def clear(self) -> None:
        self._items.clear()
        self.save()

    def mark_error(self, item_id: str, error: str) -> None:
        for item in self._items:
            if item.id == item_id:
                item.retries += 1
                item.last_error = error
                break
        self.save()

    def save(self) -> None:
        cache_manager.write_json(QUEUE_FILE, [asdict(item) for item in self._items])

    def load(self) -> None:
        raw = cache_manager.read_json(QUEUE_FILE, []) or []
        self._items = []
        for row in raw:
            try:
                self._items.append(QueueItem(**row))
            except TypeError:
                continue

    @property
    def pending(self) -> int:
        return len(self._items)

    @property
    def items(self) -> list[QueueItem]:
        return list(self._items)
