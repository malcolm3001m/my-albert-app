from __future__ import annotations

from threading import Lock
from time import monotonic
from typing import Any, Dict, Optional, Tuple


class TTLCache:
    def __init__(self) -> None:
        self._items: Dict[str, Tuple[float, Any]] = {}
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            item = self._items.get(key)
            if item is None:
                return None

            expires_at, value = item
            if expires_at <= monotonic():
                self._items.pop(key, None)
                return None

            return value

    def set(self, key: str, value: Any, ttl_seconds: int) -> Any:
        with self._lock:
            self._items[key] = (monotonic() + ttl_seconds, value)
        return value

    def delete(self, key: str) -> None:
        with self._lock:
            self._items.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
