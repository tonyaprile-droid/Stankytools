from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys


def restart_app(executable: str | Path, args: list[str] | None = None) -> None:
    args = args or []
    subprocess.Popen([str(executable), *args], cwd=str(Path(executable).parent), close_fds=True)
    os._exit(0)


def current_executable() -> Path:
    return Path(sys.executable).resolve()
