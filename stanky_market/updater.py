from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .release_config import (
    PUBLIC_LATEST_RELEASE_API,
    PUBLIC_LIST_RELEASES_API,
    PUBLIC_RELEASE_OWNER,
    PUBLIC_RELEASE_REPO,
    PUBLIC_RELEASES_URL,
)

APP_VERSION = "4.2.0"
GITHUB_OWNER = PUBLIC_RELEASE_OWNER
# Public, releases-only repository. Keep the source repository private.
# Attach only compiled Windows assets here; the updater ignores GitHub source archives.
GITHUB_REPO = PUBLIC_RELEASE_REPO
RELEASES_URL = PUBLIC_RELEASES_URL
LATEST_RELEASE_API = PUBLIC_LATEST_RELEASE_API
LIST_RELEASES_API = PUBLIC_LIST_RELEASES_API

ProgressCallback = Callable[[int, int], None]


@dataclass(frozen=True)
class UpdateInfo:
    current_version: str
    latest_version: str
    update_available: bool
    release_name: str
    html_url: str
    body: str
    asset_urls: list[str]
    message: str = ""


def local_app_data_dir() -> Path:
    """Return the writable StankyTools app-data folder used by updater/cache/logs."""
    base = os.environ.get("LOCALAPPDATA")
    if base:
        root = Path(base) / "StankyTools"
    else:
        root = Path.home() / ".stankytools"
    root.mkdir(parents=True, exist_ok=True)
    return root


def updates_dir() -> Path:
    path = local_app_data_dir() / "updates"
    path.mkdir(parents=True, exist_ok=True)
    return path


def extracted_update_dir() -> Path:
    path = updates_dir() / "extracted"
    path.mkdir(parents=True, exist_ok=True)
    return path


def logs_dir() -> Path:
    path = local_app_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def update_log_path() -> Path:
    return logs_dir() / "updater.log"


def update_state_path() -> Path:
    return updates_dir() / "update_state.json"


def _log(message: str) -> None:
    try:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with update_log_path().open("a", encoding="utf-8") as f:
            f.write(f"[{stamp}] {message}\n")
    except Exception:
        pass


def _write_state(**state: Any) -> None:
    try:
        payload = {"updated_at": datetime.now().isoformat(timespec="seconds"), **state}
        update_state_path().write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception:
        pass


def _version_tuple(value: str) -> tuple[int, ...]:
    nums = re.findall(r"\d+", value or "")
    if not nums:
        return (0,)
    return tuple(int(n) for n in nums[:4])


def is_newer(latest: str, current: str = APP_VERSION) -> bool:
    latest_tuple = _version_tuple(latest)
    current_tuple = _version_tuple(current)
    max_len = max(len(latest_tuple), len(current_tuple))
    latest_tuple += (0,) * (max_len - len(latest_tuple))
    current_tuple += (0,) * (max_len - len(current_tuple))
    return latest_tuple > current_tuple


def _github_get_json(url: str, timeout: int = 12) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"StankyTools/{APP_VERSION}",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _release_info(data: dict[str, Any]) -> UpdateInfo:
    tag = str(data.get("tag_name") or data.get("name") or "0.0.0")
    html_url = str(data.get("html_url") or RELEASES_URL)
    assets = data.get("assets") or []
    asset_urls = [str(a.get("browser_download_url")) for a in assets if a.get("browser_download_url")]
    return UpdateInfo(
        current_version=APP_VERSION,
        latest_version=tag,
        update_available=is_newer(tag, APP_VERSION),
        release_name=str(data.get("name") or tag),
        html_url=html_url,
        body=str(data.get("body") or ""),
        asset_urls=asset_urls,
    )


def check_for_update(timeout: int = 12) -> UpdateInfo:
    try:
        data = _github_get_json(LATEST_RELEASE_API, timeout=timeout)
        return _release_info(data)
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise

    try:
        releases = _github_get_json(LIST_RELEASES_API, timeout=timeout)
        if releases:
            return _release_info(releases[0])
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise

    return UpdateInfo(
        current_version=APP_VERSION,
        latest_version=APP_VERSION,
        update_available=False,
        release_name="No published release found",
        html_url=RELEASES_URL,
        body="No published GitHub release was found in the public StankyTools releases repository.",
        asset_urls=[],
        message="No published GitHub release found in the public StankyTools releases repository.",
    )


def is_packaged_app() -> bool:
    return bool(getattr(sys, "frozen", False))


def current_app_dir() -> Path:
    if is_packaged_app():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def current_executable() -> Path:
    return Path(sys.executable).resolve()


def _asset_file_name(url: str) -> str:
    return Path(urllib.parse.urlparse(url).path).name.lower()


def _looks_like_source_archive(url: str) -> bool:
    lower = url.lower()
    name = _asset_file_name(url)
    if "/zipball/" in lower or "/tarball/" in lower or "/archive/" in lower:
        return True
    return any(token in name for token in ("source", "source-code", "source_code", "src"))


def _supported_update_asset(url: str) -> bool:
    name = _asset_file_name(url)
    if _looks_like_source_archive(url):
        return False
    if name.endswith((".exe", ".msi")):
        return True
    if not name.endswith(".zip"):
        return False
    # Portable ZIPs are supported, but avoid the ambiguous uploaded project/source ZIP.
    return any(token in name for token in ("windows", "win", "portable", "installer", "release", "dist"))


def choose_update_asset(info: UpdateInfo) -> str:
    if not info.asset_urls:
        raise RuntimeError("This release has no Windows installer or portable ZIP asset. Attach StankyTools-Setup-vX.X.X.exe or StankyTools-Portable-vX.X.X.zip to the public GitHub Release.")

    candidates = [url for url in info.asset_urls if _supported_update_asset(url)]
    if not candidates:
        raise RuntimeError("No Windows installer/EXE or portable ZIP update asset was found. Source-code ZIPs are ignored by the updater.")

    preferred_patterns = (
        r"^stankytools[-_]?portable[-_]?v?\d+(?:\.\d+)*\.zip$",
        r"^stankytools[-_]?setup[-_]?v?\d+(?:\.\d+)*\.exe$",
        r"^stankytools[-_]?installer[-_]?v?\d+(?:\.\d+)*\.exe$",
        r"^stankytools[-_]?(?:windows|win)[-_]?v?\d*(?:\.\d+)*\.zip$",
        r"^stankytools[-_]?(?:windows|win)[-_]?v?\d*(?:\.\d+)*\.exe$",
        r"^stankytools[-_]?v?\d+(?:\.\d+)*\.msi$",
    )
    lower_pairs = [(_asset_file_name(url), url) for url in candidates]
    for pattern in preferred_patterns:
        for file_name, original in lower_pairs:
            if re.match(pattern, file_name):
                return original
    for extension in (".zip", ".exe", ".msi"):
        for file_name, original in lower_pairs:
            if file_name.endswith(extension):
                return original
    raise RuntimeError("No supported Windows update asset was found in the latest release.")

def download_update(info: UpdateInfo, progress: ProgressCallback | None = None, timeout: int = 30, target_dir: Path | None = None) -> Path:
    """Download the selected update asset to %LOCALAPPDATA%\\StankyTools\\updates."""
    asset_url = choose_update_asset(info)
    target_dir = target_dir or updates_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / Path(urllib.parse.urlparse(asset_url).path).name
    if not target.suffix:
        target = target.with_suffix(".zip")

    partial = target.with_suffix(target.suffix + ".part")
    for old in (partial,):
        if old.exists():
            old.unlink(missing_ok=True)

    _write_state(status="downloading", version=info.latest_version, package_path=str(target), zip_path=str(target) if target.suffix.lower() == ".zip" else "", release_url=info.html_url)
    _log(f"Downloading {asset_url} -> {target}")

    req = urllib.request.Request(asset_url, headers={"User-Agent": f"StankyTools/{APP_VERSION}"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        with partial.open("wb") as f:
            while True:
                chunk = response.read(1024 * 512)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total)
    partial.replace(target)

    # Validate before returning so bad downloads never get staged.
    suffix = target.suffix.lower()
    if suffix == ".zip":
        with zipfile.ZipFile(target, "r") as zf:
            names = zf.namelist()
            if not any(name.lower().endswith("stankytools.exe") for name in names):
                raise RuntimeError("Update ZIP does not contain StankyTools.exe. Check the GitHub Release asset.")
        zip_path = str(target)
        package_kind = "portable_zip"
    elif suffix in (".exe", ".msi"):
        if target.stat().st_size < 1024 * 1024:
            raise RuntimeError("Downloaded installer is unexpectedly small. Check the GitHub Release asset.")
        zip_path = ""
        package_kind = "installer"
    else:
        raise RuntimeError("Unsupported update package type. Use a Windows installer EXE/MSI or portable ZIP.")

    if progress:
        progress(target.stat().st_size, target.stat().st_size)
    _write_state(status="downloaded", version=info.latest_version, package_kind=package_kind, package_path=str(target), zip_path=zip_path, release_url=info.html_url)
    _log(f"Downloaded and validated update package: {target}")
    return target

def _escape_ps(value: Path | str) -> str:
    return str(value).replace("'", "''")


def _write_windows_update_script(zip_path: Path, app_dir: Path, exe_path: Path) -> Path:
    work = updates_dir()
    script_path = work / "apply_stankytools_update.bat"
    extract_dir = extracted_update_dir()

    zip_s = _escape_ps(zip_path)
    extract_s = _escape_ps(extract_dir)
    app_s = _escape_ps(app_dir)
    exe_s = _escape_ps(exe_path)
    log_s = _escape_ps(update_log_path())
    state_s = _escape_ps(update_state_path())

    ps_lines = [
        "$ErrorActionPreference = 'Stop'",
        f"Add-Content -LiteralPath '{log_s}' -Value ('[' + (Get-Date) + '] Applying update from {zip_s}')",
        f"Remove-Item -LiteralPath '{extract_s}' -Recurse -Force -ErrorAction SilentlyContinue",
        f"New-Item -ItemType Directory -Force -Path '{extract_s}' | Out-Null",
        f"Expand-Archive -LiteralPath '{zip_s}' -DestinationPath '{extract_s}' -Force",
        f"$candidate = '{extract_s}'",
        "$children = Get-ChildItem -LiteralPath $candidate -Force",
        "if ($children.Count -eq 1 -and $children[0].PSIsContainer) { $candidate = $children[0].FullName }",
        "$nested = Join-Path $candidate 'StankyTools'; if (Test-Path $nested) { $candidate = $nested }",
        "$distNested = Join-Path $candidate 'dist\\StankyTools'; if (Test-Path $distNested) { $candidate = $distNested }",
        f"Copy-Item -LiteralPath ($candidate + '\\*') -Destination '{app_s}' -Recurse -Force",
        f"Set-Content -LiteralPath '{state_s}' -Value '{{\"status\":\"installed\",\"updated_at\":\"' + (Get-Date).ToString('s') + '\"}}'",
        f"Add-Content -LiteralPath '{log_s}' -Value ('[' + (Get-Date) + '] Update installed. Restarting StankyTools.')",
        f"Start-Process -FilePath '{exe_s}'",
    ]
    ps = "; ".join(ps_lines)
    script = f"""@echo off
setlocal
cd /d "{app_dir}"
timeout /t 2 /nobreak >nul
powershell -NoProfile -ExecutionPolicy Bypass -Command "{ps}"
endlocal
"""
    script_path.write_text(script, encoding="utf-8")
    _log(f"Wrote updater script: {script_path}")
    return script_path


def stage_update_and_restart(zip_path: Path) -> None:
    """Stage a downloaded ZIP update and restart into the new version."""
    if os.name != "nt":
        raise RuntimeError("Automatic install is currently supported only on Windows builds.")
    if not is_packaged_app():
        raise RuntimeError("Automatic install works after the app is packaged as StankyTools.exe. While running with `py main.py`, the update ZIP remains in the updates folder.")
    app_dir = current_app_dir()
    exe_path = current_executable()
    if not zip_path.exists():
        raise FileNotFoundError(str(zip_path))

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        if not any(name.lower().endswith("stankytools.exe") for name in names):
            raise RuntimeError("Update ZIP does not contain StankyTools.exe. Check the GitHub Release asset.")

    _write_state(status="staged", zip_path=str(zip_path), app_dir=str(app_dir), exe_path=str(exe_path))
    script = _write_windows_update_script(zip_path.resolve(), app_dir, exe_path)
    subprocess.Popen(["cmd", "/c", str(script)], close_fds=True)
    _log("Updater script launched; app should quit now.")
