from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(slots=True)
class UpdateProgress:
    stage: str
    percent: int = 0
    message: str = ""


ProgressCallback = Callable[[UpdateProgress], None]


def noop_progress(_: UpdateProgress) -> None:
    return None
