\
from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field


@dataclass
class PerformanceSample:
    name: str
    elapsed_ms: float
    timestamp: float = field(default_factory=time.time)


class PerformanceTracker:
    def __init__(self, max_samples: int = 500):
        self.max_samples = max_samples
        self.samples: list[PerformanceSample] = []

    @contextmanager
    def measure(self, name: str):
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self.add(name, elapsed_ms)

    def add(self, name: str, elapsed_ms: float) -> None:
        self.samples.append(PerformanceSample(name=name, elapsed_ms=elapsed_ms))
        if len(self.samples) > self.max_samples:
            self.samples = self.samples[-self.max_samples:]

    def average(self, name: str) -> float | None:
        matches = [s.elapsed_ms for s in self.samples if s.name == name]
        if not matches:
            return None
        return sum(matches) / len(matches)

    def summary(self) -> dict:
        grouped: dict[str, list[float]] = {}
        for sample in self.samples:
            grouped.setdefault(sample.name, []).append(sample.elapsed_ms)

        return {
            name: {
                "count": len(values),
                "avg_ms": round(sum(values) / len(values), 2),
                "max_ms": round(max(values), 2),
                "min_ms": round(min(values), 2),
            }
            for name, values in grouped.items()
        }
