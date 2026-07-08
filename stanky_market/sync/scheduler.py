from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class ScheduledTask:
    name: str
    interval_seconds: float
    callback: Callable[[], None]
    run_immediately: bool = False
    enabled: bool = True
    last_run: float = field(default=0.0)


class TaskScheduler:
    def __init__(self) -> None:
        self._tasks: dict[str, ScheduledTask] = {}
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.RLock()

    def add(self, name: str, interval_seconds: float, callback: Callable[[], None], *, run_immediately: bool = False) -> None:
        with self._lock:
            self._tasks[name] = ScheduledTask(name, interval_seconds, callback, run_immediately)

    def remove(self, name: str) -> None:
        with self._lock:
            self._tasks.pop(name, None)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="StankySyncScheduler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _loop(self) -> None:
        while self._running:
            now = time.time()
            with self._lock:
                tasks = list(self._tasks.values())
            for task in tasks:
                if not task.enabled:
                    continue
                should_run = task.run_immediately and task.last_run == 0.0
                should_run = should_run or (now - task.last_run >= task.interval_seconds)
                if not should_run:
                    continue
                try:
                    task.callback()
                finally:
                    task.last_run = time.time()
                    task.run_immediately = False
            time.sleep(0.5)
