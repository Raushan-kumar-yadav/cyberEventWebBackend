import time
from collections import deque

from fastapi import HTTPException, status

from app.core.config import settings


# sliding window, per process
class RateLimiter:
    def __init__(self, limit: int, window_seconds: float) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = {}

    def hit(self, key: str) -> None:
        now = time.monotonic()
        if len(self._hits) > 10_000:
            self._prune(now)
        hits = self._hits.setdefault(key, deque())
        while hits and now - hits[0] > self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts, slow down")
        hits.append(now)

    def _prune(self, now: float) -> None:
        stale = [k for k, v in self._hits.items() if not v or now - v[-1] > self.window]
        for key in stale:
            del self._hits[key]


login_limiter = RateLimiter(settings.login_attempts_per_minute, 60)
