from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def file_matches(path: Path, expected_sha256: str) -> bool:
    return path.exists() and sha256_file(path).lower() == expected_sha256.lower()
