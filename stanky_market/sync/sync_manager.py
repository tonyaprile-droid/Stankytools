from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from .diagnostics import SyncDiagnostics
from .dispatcher import dispatcher
from .delta import DeltaState
from .realtime import RealtimeManager
from .retry import RetryPolicy
from .scheduler import TaskScheduler
from .status import SyncState
from .sync_queue import SyncQueue
from .worker import SyncWorker

DEFAULT_SYNC_TABLES = [
    "guild_events",
    "guild_event_responses",
    "guild_pois",
    "guild_bases",
    "guild_announcements",
    "guild_links",
    "guild_ideas",
    "guild_members",
    "member_specializations",
]


class SyncManager(QObject):
    statusChanged = Signal(str)
    pendingChanged = Signal(int)
    guildChanged = Signal(str)
    realtimeChanged = Signal(dict)
    diagnosticsChanged = Signal(dict)

    _instance: "SyncManager | None" = None

    @classmethod
    def instance(cls) -> "SyncManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        super().__init__()
        self.guild_id: str | None = None
        self.status = SyncState.SYNCED
        self.queue = SyncQueue()
        self.delta = DeltaState()
        self.realtime = RealtimeManager()
        self.scheduler = TaskScheduler()
        self.diagnostics = SyncDiagnostics()
        self.worker = SyncWorker(self.process_queue, interval_seconds=1.0)
        self._supabase = None

    def set_supabase_client(self, client) -> None:
        self._supabase = client

    def start(self) -> None:
        self.worker.start()
        self.scheduler.start()
        self.scheduler.add("diagnostics", 5, self._emit_diagnostics, run_immediately=True)

    def stop(self) -> None:
        self.worker.stop()
        self.scheduler.stop()
        self.realtime.unsubscribe_all()

    def subscribe_guild(self, guild_id: str, tables: list[str] | None = None) -> None:
        self.unsubscribe_guild(clear=False)
        self.guild_id = guild_id
        self.diagnostics.guild_id = guild_id
        self.realtime.subscribe_guild(guild_id, tables or DEFAULT_SYNC_TABLES, self._handle_realtime_payload)
        self.guildChanged.emit(guild_id)
        dispatcher.emit("guild_changed", guild_id)
        self._set_status(SyncState.SYNCED)

    def unsubscribe_guild(self, *, clear: bool = True) -> None:
        old = self.guild_id
        self.realtime.unsubscribe_all()
        self.guild_id = None
        self.diagnostics.guild_id = None
        if clear and old:
            dispatcher.emit("guild_unsubscribed", old)

    def queue_change(self, table: str, action: str, payload: dict) -> None:
        item = self.queue.add(table, action, payload)
        dispatcher.emit("sync_queued", item)
        self.pendingChanged.emit(self.queue.pending)
        self._set_status(SyncState.PENDING)

    def process_queue(self) -> None:
        if not self.queue.pending:
            if self.status == SyncState.PENDING:
                self._set_status(SyncState.SYNCED)
            return
        item = self.queue.next()
        if item is None:
            return
        try:
            self._set_status(SyncState.SYNCING)
            self._upload_item(item)
            self.queue.remove(item.id)
            self.pendingChanged.emit(self.queue.pending)
            self.diagnostics.mark_sync()
            dispatcher.emit("sync_uploaded", item)
            self._set_status(SyncState.SYNCED if not self.queue.pending else SyncState.PENDING)
        except Exception as exc:
            item.retries += 1
            self.diagnostics.mark_error(str(exc))
            dispatcher.emit("sync_failed", item, exc)
            self._set_status(SyncState.ERROR)

    def pull_delta(self, table: str) -> list[dict]:
        if not self.guild_id or self._supabase is None:
            return []
        last = self.delta.get(self.guild_id, table)
        query = self._supabase.table(table).select("*").eq("guild_id", self.guild_id)
        if last:
            query = query.gt("updated_at", last)
        result = query.execute()
        rows = getattr(result, "data", None) or []
        self.delta.set_now(self.guild_id, table)
        dispatcher.emit("sync_delta", table, rows)
        return rows

    def _upload_item(self, item) -> None:
        if self._supabase is None:
            # Infrastructure mode: app can hook sync_upload and perform the actual save.
            dispatcher.emit("sync_upload", item)
            return
        table = self._supabase.table(item.table)
        if item.action in {"insert", "upsert", "update"}:
            table.upsert(item.payload).execute()
        elif item.action == "delete":
            table.delete().eq("id", item.payload["id"]).execute()
        elif item.action == "soft_delete":
            table.update({"deleted_at": item.payload.get("deleted_at")}).eq("id", item.payload["id"]).execute()
        else:
            raise ValueError(f"Unknown sync action: {item.action}")

    def _handle_realtime_payload(self, payload: dict) -> None:
        self.realtimeChanged.emit(payload)
        dispatcher.emit("realtime_payload", payload)

    def _set_status(self, status: SyncState) -> None:
        self.status = status
        self.diagnostics.status = status.value
        self.diagnostics.pending_queue = self.queue.pending
        self.diagnostics.realtime_tables = self.realtime.active_tables
        self.statusChanged.emit(status.value)
        dispatcher.emit("sync_status", status.value)

    def _emit_diagnostics(self) -> None:
        self.diagnostics.pending_queue = self.queue.pending
        self.diagnostics.realtime_tables = self.realtime.active_tables
        data = self.diagnostics.to_dict()
        self.diagnosticsChanged.emit(data)
        dispatcher.emit("sync_diagnostics", data)


sync_manager = SyncManager.instance()
