from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import os


class RestartManager:
    def __init__(self, executable: str | Path | None = None):
        self.executable = Path(executable) if executable else Path(sys.argv[0])

    def restart(self, args: list[str] | None = None) -> None:
        command = [str(self.executable)] + (args or [])
        subprocess.Popen(command, cwd=str(self.executable.parent), close_fds=True)
        os._exit(0)
