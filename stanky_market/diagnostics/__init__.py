from .diagnostics_manager import DiagnosticsManager
from .health_monitor import HealthMonitor
from .telemetry import TelemetryLogger
from .performance import PerformanceTracker
from .queue_monitor import QueueMonitor
from .connection_monitor import ConnectionMonitor
from .sync_stats import SyncStats

diagnostics = DiagnosticsManager.instance()
