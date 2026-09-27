"""Small in-process TTL cache for response projections.

Keys are supplied by callers so protected endpoints can include the user id
and never share private responses between sessions.
"""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from threading import RLock
from time import monotonic
from typing import Any


class TTLCache:
    def __init__(self) -> None:
        self._entries: dict[str, tuple[float, Any]] = {}
        self._lock = RLock()

    def get_or_set(self, key: str, loader: Callable[[], Any], ttl_seconds: float) -> Any:
        now = monotonic()
        with self._lock:
            entry = self._entries.get(key)
            if entry is not None and entry[0] > now:
                return deepcopy(entry[1])

        value = loader()
        with self._lock:
            self._entries[key] = (now + ttl_seconds, deepcopy(value))
        return deepcopy(value)

    def invalidate_prefix(self, prefix: str) -> None:
        with self._lock:
            for key in [key for key in self._entries if key.startswith(prefix)]:
                del self._entries[key]


response_cache = TTLCache()