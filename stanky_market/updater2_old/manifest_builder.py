from __future__ import annotations

import argparse
import json
from pathlib import Path

from .hash_utils import sha256_file

EXCLUDE_DIRS = {"__pycache__", "build", "dist", ".git"}


def build_manifest(root: Path, base_url: str, version: str) -> dict:
    files = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in EXCLUDE_DIRS for part in path.parts):
            continue
        rel = path.relative_to(root).as_posix()
        files.append({
            "path": rel,
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
            "url": f"{base_url.rstrip('/')}/{rel}",
        })
    return {"version": version, "files": files}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    manifest = build_manifest(Path(args.root), args.base_url, args.version)
    Path(args.out).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
