from __future__ import annotations


def _theme(name: str, accent: str, glow: str, accent_soft: str) -> dict[str, str]:
    return {
        "name": name,
        "accent": accent,
        "glow": glow,
        "accent_soft": accent_soft,
        "accent_faint": glow,
        "border": accent_soft,
        "hover": glow,
        "panel": "#17191C",
        "panel_hover": "#1F2327",
        "bg": "#0D0E10",
        "text": "#ECECEC",
        "muted": "#A7A09A",
    }


THEMES = {
    "dune": _theme("Dune Gold", "#D9B45D", "rgba(217,180,93,0.18)", "rgba(217,180,93,0.58)"),
    "atreides": _theme("Atreides Green", "#59D37A", "rgba(89,211,122,0.20)", "rgba(89,211,122,0.58)"),
    "spice": _theme("Spice Purple", "#A06BFF", "rgba(160,107,255,0.20)", "rgba(160,107,255,0.58)"),
    "harkonnen": _theme("Harkonnen Red", "#E25555", "rgba(226,85,85,0.20)", "rgba(226,85,85,0.58)"),
}


def theme_colors(theme_key: str | None) -> dict[str, str]:
    return THEMES.get((theme_key or "dune").strip().lower(), THEMES["dune"])
