"""Általános bővítési pont: névvel regisztrált elemek (kategóriák, kinyerők, később ellenőrző eszközök)."""
from typing import Generic, TypeVar

T = TypeVar("T")


class Registry(Generic[T]):
    def __init__(self, name: str) -> None:
        self.name = name
        self._items: dict[str, T] = {}

    def register(self, key: str, item: T) -> None:
        self._items[key] = item

    def get(self, key: str) -> T:
        if key not in self._items:
            raise KeyError(f"{self.name}: ismeretlen kulcs '{key}'")
        return self._items[key]

    def keys(self) -> list[str]:
        return list(self._items)

    def items(self) -> dict[str, T]:
        return dict(self._items)
