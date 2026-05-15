from __future__ import annotations

from dataclasses import asdict, dataclass
from threading import Lock


@dataclass
class Item:
    id: int
    name: str
    price: float

    def to_dict(self) -> dict:
        return asdict(self)


class ItemStore:
    """In-memory thread-safe store. Stand-in for a real database."""

    def __init__(self) -> None:
        self._items: dict[int, Item] = {}
        self._next_id: int = 1
        self._lock = Lock()

    def list(self) -> list[Item]:
        with self._lock:
            return list(self._items.values())

    def get(self, item_id: int) -> Item | None:
        with self._lock:
            return self._items.get(item_id)

    def add(self, name: str, price: float) -> Item:
        if not name or not name.strip():
            raise ValueError("name is required")
        if price < 0:
            raise ValueError("price must be non-negative")
        with self._lock:
            item = Item(id=self._next_id, name=name.strip(), price=float(price))
            self._items[item.id] = item
            self._next_id += 1
            return item

    def delete(self, item_id: int) -> bool:
        with self._lock:
            return self._items.pop(item_id, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            self._next_id = 1
