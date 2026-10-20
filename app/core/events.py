"""Minimális eseménybusz: a modulok egymás ismerete nélkül reagálhatnak egymás változásaira."""
from collections import defaultdict
from collections.abc import Callable
from typing import Any


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[..., Any]]] = defaultdict(list)

    def subscribe(self, event: str, handler: Callable[..., Any]) -> None:
        if handler not in self._handlers[event]:  # többszöri setup() ne duplázzon
            self._handlers[event].append(handler)

    def publish(self, event: str, **payload: Any) -> None:
        for handler in self._handlers[event]:
            handler(**payload)


bus = EventBus()
