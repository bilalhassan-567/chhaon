"""In-memory sliding-window rate limiter, keyed by an arbitrary string (here, the
sender's phone number). Deliberately not a distributed/Redis-backed limiter — this is
a single-instance hackathon deployment (Render free tier, one Web Service), so
in-process state is sufficient and doesn't add an infra dependency. Resets on restart,
which is an accepted limitation, same as the WhatsApp conversation state.
"""

import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, max_events: int, window_seconds: float):
        self.max_events = max_events
        self.window_seconds = window_seconds
        self._events: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] < cutoff:
                events.popleft()
            if len(events) >= self.max_events:
                return False
            events.append(now)
            return True
