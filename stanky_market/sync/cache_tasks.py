from __future__ import annotations

from .cache_cleanup import CacheCleanup, CleanupResult


def run_startup_cache_cleanup() -> CleanupResult:
    """Call once during app startup after QApplication is created."""
    return CacheCleanup().run_startup_cleanup()
