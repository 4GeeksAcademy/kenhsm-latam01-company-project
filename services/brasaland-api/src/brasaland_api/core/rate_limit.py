from __future__ import annotations

from math import ceil
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request

from brasaland_api.core.config import get_settings


class FixedWindowRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int = 60, max_keys: int = 10000):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.max_keys = max_keys
        self._buckets: dict[str, tuple[int, int]] = {}
        self._last_cleanup = monotonic()
        self._lock = Lock()

    def check(self, key: str) -> int | None:
        now = monotonic()
        window = int(now // self.window_seconds)
        with self._lock:
            if now - self._last_cleanup >= self.window_seconds or (
                len(self._buckets) >= self.max_keys and key not in self._buckets
            ):
                self._buckets = {
                    stored_key: bucket
                    for stored_key, bucket in self._buckets.items()
                    if bucket[0] == window
                }
                self._last_cleanup = now

            bucket = self._buckets.get(key)
            if bucket and bucket[0] == window:
                if bucket[1] >= self.max_requests:
                    return max(1, ceil((window + 1) * self.window_seconds - now))
                self._buckets[key] = (window, bucket[1] + 1)
                return None

            if len(self._buckets) >= self.max_keys:
                return self.window_seconds
            self._buckets[key] = (window, 1)
            return None

    def __call__(self, request: Request) -> None:
        client_host = request.client.host if request.client else "unknown"
        retry_after = self.check(f"ip:{client_host}")
        if retry_after is not None:
            raise HTTPException(
                status_code=429,
                detail="Límite de consultas al agente alcanzado. Inténtalo de nuevo más tarde.",
                headers={"Retry-After": str(retry_after)},
            )


agent_query_rate_limiter = FixedWindowRateLimiter(get_settings().agent_query_limit_per_minute)