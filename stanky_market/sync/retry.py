from __future__ import annotations


class RetryPolicy:
    def __init__(self, delays: list[int] | None = None) -> None:
        self.delays = delays or [2, 5, 10, 30, 60, 300]

    def next_delay(self, attempt: int) -> int:
        if attempt < 0:
            attempt = 0
        if attempt >= len(self.delays):
            return self.delays[-1]
        return self.delays[attempt]
