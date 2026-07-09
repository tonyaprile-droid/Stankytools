from __future__ import annotations

from pathlib import Path

from ..paths import asset_dir

PACKAGE_ASSET_ROOT = Path(__file__).resolve().parents[1] / "assets"
SHARED_ASSET_ROOT = asset_dir()
THEME_KEYS = {"dune", "atreides", "harkonnen", "spice"}


def normalize_theme(theme: str | None) -> str:
    key = (theme or "dune").strip().lower()
    return key if key in THEME_KEYS else "dune"


def asset_path(*parts: str) -> Path:
    return SHARED_ASSET_ROOT.joinpath(*parts)


def package_asset_path(*parts: str) -> Path:
    return PACKAGE_ASSET_ROOT.joinpath(*parts)


def first_existing(*paths: Path) -> Path:
    for path in paths:
        if path.exists():
            return path
    return paths[0]


def mascot_path(theme: str | None) -> Path:
    key = normalize_theme(theme)
    return first_existing(
        package_asset_path("themes", key, "mascot.webp"),
        package_asset_path("themes", key, "mascot.png"),
        asset_path("images", f"{key}_mascot_logo.webp"),
        asset_path("images", f"{key}_mascot_logo.png"),
        asset_path("images", "stankytools_mascot_logo.webp"),
        asset_path("images", "stankytools_mascot_logo.png"),
    )


def banner_path(theme: str | None, page: str = "dashboard") -> Path:
    key = normalize_theme(theme)
    page_key = (page or "dashboard").strip().lower().replace(" ", "_")
    page_stem = page_key if page_key.endswith("_banner") else f"{page_key}_banner"
    theme_base = package_asset_path("themes", key)
    candidates = [
        theme_base / f"{page_stem}.webp",
        theme_base / f"{page_stem}.png",
        theme_base / "banner.webp",
        theme_base / "banner.png",
        asset_path("backgrounds", f"{key}_{page_stem}.webp"),
        asset_path("backgrounds", f"{key}_{page_stem}.png"),
        asset_path("backgrounds", f"{page_stem}.webp"),
        asset_path("backgrounds", f"{page_stem}.png"),
        asset_path("backgrounds", "dashboard_banner.webp"),
        asset_path("backgrounds", "dashboard_banner.png"),
    ]
    return first_existing(*candidates)


def nav_background_path(theme: str | None) -> Path:
    key = normalize_theme(theme)
    theme_base = package_asset_path("themes", key)
    candidates = [
        asset_path("backgrounds", f"{key}_nav_background.svg"),
        asset_path("backgrounds", f"{key}_nav_background.png"),
        asset_path("backgrounds", f"{key}_nav_background.webp"),
        theme_base / "nav_background.svg",
        theme_base / "nav_background.webp",
        theme_base / "nav_background.png",
        asset_path("backgrounds", f"{key}_sidebar_texture.webp"),
        asset_path("backgrounds", f"{key}_sidebar_texture.png"),
        asset_path("backgrounds", "sidebar_texture.webp"),
        asset_path("backgrounds", "sidebar_texture.png"),
        asset_path("ui", "sidebar_texture.webp"),
    ]
    return first_existing(*candidates)
