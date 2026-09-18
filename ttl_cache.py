"""Process-local TTL caches with application cache-hit metrics.

cached_tokens on the request record is LLM/provider prompt caching.
record_cache() here is the application/data cache (mess menu, bus schedule,
notices, timetable, rooms). Do not treat one as the other.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Optional

import metrics


class TtlCache:
    def __init__(self, source: str, ttl_seconds: Optional[float] = 60):
        self.source = source
        self.ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self._store: dict[Any, tuple[Optional[float], Any]] = {}

    def get(self, key: Any, compute_fn: Callable[[], Any]) -> Any:
        now = time.time()
        with self._lock:
            entry = self._store.get(key)
            if entry is not None and (entry[0] is None or now < entry[0]):
                metrics.record_cache(self.source, True)
                return entry[1]
        value = compute_fn()
        expires = None if self.ttl_seconds is None else time.time() + self.ttl_seconds
        with self._lock:
            self._store[key] = (expires, value)
        metrics.record_cache(self.source, False)
        return value

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def pop(self, key: Any) -> None:
        with self._lock:
            self._store.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> None:
        with self._lock:
            for key in [k for k in self._store if str(k).startswith(prefix)]:
                self._store.pop(key, None)
