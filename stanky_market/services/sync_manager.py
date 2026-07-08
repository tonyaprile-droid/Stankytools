from __future__ import annotations

import time
from PySide6.QtCore import QObject, QTimer, Signal


class SyncManager(QObject):
    """Central, non-intrusive sync coordinator.

    User actions save locally first and queue sync work. The queue is debounced so
    rapid marker/news edits don't repeatedly block the interface. Network work is
    delayed slightly and status is reported with toasts.
    """

    statusChanged = Signal(str)

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.pending: set[str] = set()
        self.last_success = "Not yet synced"
        self._running = False
        self._timer = QTimer(self)
        self._timer.setInterval(2200)
        self._timer.timeout.connect(self.flush)

    def queue(self, kind: str, immediate: bool = False) -> None:
        kind = (kind or "all").lower().strip()
        if kind in {"marker", "markers"}:
            kind = "all"
        self.pending.add(kind)
        self.statusChanged.emit(f"Queued {kind}")
        if not self._timer.isActive():
            self._timer.start()
        if immediate:
            # Still debounce by one event loop tick so the UI can repaint first.
            QTimer.singleShot(350, self.flush)

    def flush(self) -> None:
        if self._running or not self.pending:
            return
        self._running = True
        pending = set(self.pending)
        self.pending.clear()
        w = self.window
        if hasattr(w, "notify"):
            w.notify("Syncing", "Sending saved changes in the background.", "info", 1800)
        try:
            if "all" in pending or "poi" in pending or "base" in pending:
                if hasattr(w, "sync_deep_desert_markers"):
                    w.sync_deep_desert_markers(show_popup=False, refresh_ui=True)
                else:
                    if "all" in pending or "poi" in pending:
                        w.sync_guild_pois(show_popup=False)
                    if "all" in pending or "base" in pending:
                        w.sync_guild_bases(show_popup=False)
                if hasattr(w, "poi_sync_status"):
                    w.poi_sync_status.setText("Deep Desert POIs synced.")
                if hasattr(w, "base_sync_status"):
                    w.base_sync_status.setText("Base markers synced.")
            if "all" in pending or "news" in pending or "guild" in pending or "events" in pending or "specializations" in pending:
                w.sync_guild_dashboard_content(show_errors=False)
            self.last_success = time.strftime("%Y-%m-%d %H:%M:%S")
            self.statusChanged.emit("Auto-sync complete")
            if hasattr(w, "dashboard_sync_status"):
                w.dashboard_sync_status.setText("SYNC STATUS: AUTO-SYNCED")
            if hasattr(w, "notify"):
                w.notify("Synced Successfully", "Guild data is up to date.", "success", 2200)
        except Exception as exc:
            self.pending.update(pending)
            self.statusChanged.emit(f"Sync failed: {exc}")
            if hasattr(w, "dashboard_sync_status"):
                w.dashboard_sync_status.setText("SYNC STATUS: RETRY QUEUED")
            if hasattr(w, "notify"):
                w.notify("Sync Queued", "Network sync failed; changes remain saved locally and will retry.", "warning", 4200)
            if not self._timer.isActive():
                self._timer.start()
        finally:
            self._running = False
            if not self.pending and self._timer.isActive():
                self._timer.stop()
