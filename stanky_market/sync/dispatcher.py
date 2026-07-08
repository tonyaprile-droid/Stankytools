from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Callable, DefaultDict

log = logging.getLogger(__name__)


class Dispatcher:
    def __init__(self) -> None:
        self._listeners: DefaultDict[str, list[Callable[..., None]]] = defaultdict(list)

    def subscribe(self, event: str, callback: Callable[..., None]) -> None:
        if callback not in self._listeners[event]:
            self._listeners[event].append(callback)

    def unsubscribe(self, event: str, callback: Callable[..., None]) -> None:
        if callback in self._listeners[event]:
            self._listeners[event].remove(callback)

    def emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        for callback in list(self._listeners[event]):
            try:
                callback(*args, **kwargs)
            except Exception:
                log.exception("Dispatcher listener failed for event %s", event)


dispatcher = Dispatcher()
