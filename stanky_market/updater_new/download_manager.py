from __future__ import annotations

from pathlib import Path
from urllib.request import Request, urlopen
from typing import Callable
import time

ProgressCallback = Callable[[str, int, int], None]


class DownloadManager:
    def __init__(self, download_dir: str | Path, user_agent: str = "StankyTools-Updater"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.user_agent = user_agent
        self.bytes_per_second_limit: int | None = None

    def set_bandwidth_limit(self, bytes_per_second: int | None) -> None:
        self.bytes_per_second_limit = bytes_per_second if bytes_per_second and bytes_per_second > 0 else None

    def download(self, url: str, filename: str, progress: ProgressCallback | None = None) -> Path:
        target = self.download_dir / filename
        part = target.with_suffix(target.suffix + ".part")
        existing = part.stat().st_size if part.exists() else 0
        headers = {"User-Agent": self.user_agent}
        if existing:
            headers["Range"] = f"bytes={existing}-"
        req = Request(url, headers=headers)
        with urlopen(req, timeout=60) as response, part.open("ab" if existing else "wb") as f:
            total_header = response.headers.get("Content-Length")
            total = (int(total_header) + existing) if total_header else 0
            downloaded = existing
            last_tick = time.monotonic()
            window_bytes = 0
            while True:
                chunk = response.read(1024 * 256)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                window_bytes += len(chunk)
                if progress:
                    progress(filename, downloaded, total)
                if self.bytes_per_second_limit:
                    elapsed = time.monotonic() - last_tick
                    if elapsed >= 1:
                        window_bytes = 0
                        last_tick = time.monotonic()
                    elif window_bytes > self.bytes_per_second_limit:
                        time.sleep(1 - elapsed)
                        window_bytes = 0
                        last_tick = time.monotonic()
        part.replace(target)
        return target
