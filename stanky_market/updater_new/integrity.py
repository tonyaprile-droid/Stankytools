from __future__ import annotations

from pathlib import Path
import hashlib


def sha256_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_sha256(path: str | Path, expected: str) -> bool:
    if not expected:
        return False
    p = Path(path)
    if not p.exists() or not p.is_file():
        return False
    return sha256_file(p).lower() == expected.lower()
