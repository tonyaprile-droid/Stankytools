from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from stanky_market.updater2.patch_client import PatchClient
from stanky_market.updater2.paths import app_root


def launch_app(exe_name: str = "StankyTools.exe") -> int:
    root = app_root()
    exe = root / exe_name
    if not exe.exists():
        # dev fallback
        main_py = root / "main.py"
        if main_py.exists():
            return subprocess.Popen([sys.executable, str(main_py)], cwd=str(root)).wait()
        raise FileNotFoundError(f"Unable to find {exe}")
    return subprocess.Popen([str(exe)], cwd=str(root)).wait()


def main() -> int:
    parser = argparse.ArgumentParser(description="StankyTools Launcher")
    parser.add_argument("--skip-update", action="store_true")
    parser.add_argument("--manifest-url", default=None)
    args = parser.parse_args()

    if not args.skip_update:
        client = PatchClient(manifest_url=args.manifest_url)
        result = client.update_if_needed()
        if result.updated:
            print(f"Updated to {result.version}")
        elif result.error:
            print(f"Update skipped: {result.error}")

    return launch_app()


if __name__ == "__main__":
    raise SystemExit(main())
