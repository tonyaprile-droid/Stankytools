from __future__ import annotations

from pathlib import Path
from urllib.request import Request, urlopen
import json

from stanky_market.updater.manifest_v2 import ManifestV2


class UpdaterClient:
    def __init__(self, manifest_url: str, user_agent: str = "StankyTools-Launcher"):
        self.manifest_url = manifest_url
        self.user_agent = user_agent

    def fetch_manifest(self) -> ManifestV2:
        req = Request(self.manifest_url, headers={"User-Agent": self.user_agent})
        with urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        return ManifestV2.from_dict(data)

    def save_manifest_copy(self, manifest: ManifestV2, path: str | Path) -> None:
        manifest.save(path)
