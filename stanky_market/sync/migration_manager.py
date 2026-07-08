from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

@dataclass
class MigrationStep:
    name: str
    apply: Callable[[], None]
    rollback: Callable[[], None] | None = None
    completed: bool = False

class MigrationManager:
    def __init__(self):
        self.steps: list[MigrationStep] = []

    def add_step(self, name: str, apply: Callable[[], None], rollback: Callable[[], None] | None = None) -> None:
        self.steps.append(MigrationStep(name=name, apply=apply, rollback=rollback))

    def run(self) -> None:
        completed: list[MigrationStep] = []
        try:
            for step in self.steps:
                step.apply()
                step.completed = True
                completed.append(step)
        except Exception:
            for step in reversed(completed):
                if step.rollback:
                    step.rollback()
            raise
