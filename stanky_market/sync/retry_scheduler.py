from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict


@dataclass
class RetryState:
    attempts: int = 0
    next_allowed_at: float = 0.0


class RetryScheduler:
    def __init__(self, delays: tuple[int, ...] = (2, 5, 10, 30, 60, 300)) -> None:
        self.delays = delays
        self._states: Dict[str, RetryState] = {}

    def can_run(self, key: str) -> bool:
        state = self._states.get(key)
        return state is None or time.time() >= state.next_allowed_at

    def record_failure(self, key: str) -> int:
        state = self._states.setdefault(key, RetryState())
        delay = self.delays[min(state.attempts, len(self.delays) - 1)]
        state.attempts += 1
        state.next_allowed_at = time.time() + delay
        return delay

    def record_success(self, key: str) -> None:
        self._states.pop(key, None)
