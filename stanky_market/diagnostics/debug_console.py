\
from __future__ import annotations

from pathlib import Path


class DebugConsole:
    """
    Lightweight text sink for a future Settings > System Health UI.
    """

    def __init__(self, max_lines: int = 500):
        self.max_lines = max_lines
        self.lines: list[str] = []

    def write(self, message: str) -> None:
        self.lines.append(str(message))
        if len(self.lines) > self.max_lines:
            self.lines = self.lines[-self.max_lines:]

    def clear(self) -> None:
        self.lines.clear()

    def text(self) -> str:
        return "\n".join(self.lines)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.text(), encoding="utf-8")
