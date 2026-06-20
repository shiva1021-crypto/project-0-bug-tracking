from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from flask import current_app


_events = defaultdict(deque)
_lock = Lock()


def rate_limit_exceeded(scope, identity, limit, window_seconds):
    if current_app.config.get("TESTING"):
        return False

    key = (scope, identity or "unknown")
    cutoff = monotonic() - window_seconds
    with _lock:
        events = _events[key]
        while events and events[0] < cutoff:
            events.popleft()
        if len(events) >= limit:
            return True
        events.append(monotonic())
        return False
