from __future__ import annotations

from pathlib import Path
import hashlib


def sha256_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_file(path: str | Path, expected_sha256: str) -> bool:
    p = Path(path)
    if not p.exists() or not expected_sha256:
        return False
    return sha256_file(p).lower() == expected_sha256.lower()
