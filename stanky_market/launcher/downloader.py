from __future__ import annotations

from pathlib import Path
from urllib.request import Request, urlopen

from .progress import ProgressCallback, UpdateProgress, noop_progress


class DownloadError(RuntimeError):
    pass


class ResumableDownloader:
    def __init__(self, user_agent: str = "StankyToolsUpdater/1.0") -> None:
        self.user_agent = user_agent

    def download(self, url: str, target: str | Path, progress: ProgressCallback = noop_progress) -> Path:
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_suffix(target.suffix + ".part")
        existing = partial.stat().st_size if partial.exists() else 0

        headers = {"User-Agent": self.user_agent}
        if existing:
            headers["Range"] = f"bytes={existing}-"

        req = Request(url, headers=headers)
        try:
            with urlopen(req, timeout=60) as response:
                total_header = response.headers.get("Content-Length")
                total = int(total_header or 0) + existing
                mode = "ab" if existing else "wb"
                downloaded = existing
                with partial.open(mode) as handle:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        handle.write(chunk)
                        downloaded += len(chunk)
                        percent = int(downloaded * 100 / total) if total else 0
                        progress(UpdateProgress("downloading", min(percent, 100), f"Downloaded {downloaded:,} bytes"))
        except Exception as exc:
            raise DownloadError(str(exc)) from exc

        partial.replace(target)
        progress(UpdateProgress("downloaded", 100, "Download complete"))
        return target
