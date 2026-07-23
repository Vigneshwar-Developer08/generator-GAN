"""
Minimal in-memory rate limiter.

Deliberately dependency-free (no slowapi/redis) to keep the stack
exactly as specified. Good enough for a single-process deployment;
for multi-instance/horizontally-scaled deployments, swap the internal
store for Redis (INCR + EXPIRE) without changing the public interface.
"""

import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict


class RateLimiter:
    """Fixed-window-per-client sliding counter, keyed by client identifier (e.g. IP)."""

    def __init__(self, max_requests: int, window_seconds: int = 60) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, client_key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[client_key]
            while hits and now - hits[0] > self._window_seconds:
                hits.popleft()

            if len(hits) >= self._max_requests:
                return False

            hits.append(now)
            return True
