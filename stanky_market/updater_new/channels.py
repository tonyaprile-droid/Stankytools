from __future__ import annotations

VALID_CHANNELS = {"stable", "beta", "dev"}


def normalize_channel(value: str | None) -> str:
    channel = (value or "stable").strip().lower()
    return channel if channel in VALID_CHANNELS else "stable"


def channel_allows_file(active_channel: str, file_channel: str) -> bool:
    active = normalize_channel(active_channel)
    file_ch = normalize_channel(file_channel)
    if active == "dev":
        return True
    if active == "beta":
        return file_ch in {"stable", "beta"}
    return file_ch == "stable"
