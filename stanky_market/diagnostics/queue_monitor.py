\
from __future__ import annotations


class QueueMonitor:
    def __init__(self):
        self.pending = 0
        self.failed = 0
        self.last_item = None

    def update_from_queue(self, queue) -> None:
        self.pending = getattr(queue, "pending", 0)
        if callable(self.pending):
            self.pending = self.pending()

        items = getattr(queue, "items", [])
        if items:
            self.last_item = items[-1]

    def mark_failed(self) -> None:
        self.failed += 1

    def to_dict(self) -> dict:
        return {
            "pending": self.pending,
            "failed": self.failed,
            "last_item": str(self.last_item) if self.last_item else None,
        }
