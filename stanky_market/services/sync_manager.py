from __future__ import annotations

import time
from PySide6.QtCore import QObject, QTimer, Signal


class SyncManager(QObject):
    """Central sync coordinator for v1.0 milestone 4.

    Pages should queue changes here instead of exposing manual sync buttons.
    This keeps sync automatic and leaves Settings as the only manual recovery area.
    """

    statusChanged = Signal(str)

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.pending: set[str] = set()
        self.last_success = "Not yet synced"
        self._running = False
        self._timer = QTimer(self)
        self._timer.setInterval(1250)
        self._timer.timeout.connect(self.flush)

    def queue(self, kind: str, immediate: bool = True) -> None:
        kind = (kind or "all").lower().strip()
        if kind in {"marker", "markers"}:
            kind = "all"
        self.pending.add(kind)
        self.statusChanged.emit(f"Queued {kind}")
        if immediate:
            QTimer.singleShot(0, self.flush)
        elif not self._timer.isActive():
            self._timer.start()

    def flush(self) -> None:
        if self._running or not self.pending:
            return
        self._running = True
        pending = set(self.pending)
        self.pending.clear()
        w = self.window
        try:
            if "all" in pending or "poi" in pending:
                w.sync_guild_pois(show_popup=False)
                if hasattr(w, "poi_sync_status"):
                    w.poi_sync_status.setText("Auto-sync complete for Deep Desert POIs.")
            if "all" in pending or "base" in pending:
                w.sync_guild_bases(show_popup=False)
                if hasattr(w, "base_sync_status"):
                    w.base_sync_status.setText("Auto-sync complete for base markers.")
            if "all" in pending or "news" in pending or "guild" in pending:
                w.sync_guild_dashboard_content(show_errors=False)
            self.last_success = time.strftime("%Y-%m-%d %H:%M:%S")
            self.statusChanged.emit("Auto-sync complete")
            if hasattr(w, "dashboard_sync_status"):
                w.dashboard_sync_status.setText("SYNC STATUS: AUTO-SYNCED")
        except Exception as exc:
            self.pending.update(pending)
            self.statusChanged.emit(f"Sync failed: {exc}")
            if hasattr(w, "dashboard_sync_status"):
                w.dashboard_sync_status.setText("SYNC STATUS: RETRY QUEUED")
            if not self._timer.isActive():
                self._timer.start()
        finally:
            self._running = False
            if not self.pending and self._timer.isActive():
                self._timer.stop()
