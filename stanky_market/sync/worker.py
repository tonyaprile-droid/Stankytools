from __future__ import annotations

import threading
import time
from typing import Callable


class SyncWorker:
    def __init__(self, tick: Callable[[], None], interval_seconds: float = 1.0) -> None:
        self.tick = tick
        self.interval_seconds = interval_seconds
        self.running = False
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, name="StankySyncWorker", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.running = False

    def _run(self) -> None:
        while self.running:
            self.tick()
            time.sleep(self.interval_seconds)
