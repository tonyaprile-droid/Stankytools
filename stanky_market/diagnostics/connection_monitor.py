\
from __future__ import annotations

import socket
import time


class ConnectionMonitor:
    def __init__(self, host: str = "api.github.com", port: int = 443, timeout: float = 2.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.online = False
        self.latency_ms: float | None = None
        self.last_checked: float | None = None
        self.last_error: str | None = None

    def check(self) -> bool:
        start = time.perf_counter()
        self.last_checked = time.time()

        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout):
                self.latency_ms = round((time.perf_counter() - start) * 1000, 2)
                self.online = True
                self.last_error = None
                return True
        except Exception as exc:
            self.latency_ms = None
            self.online = False
            self.last_error = str(exc)
            return False

    def to_dict(self) -> dict:
        return {
            "online": self.online,
            "latency_ms": self.latency_ms,
            "last_checked": self.last_checked,
            "last_error": self.last_error,
        }
