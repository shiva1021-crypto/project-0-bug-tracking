from collections import defaultdict, deque
import hashlib
from threading import Lock
from time import monotonic

from flask import current_app

from config import db_cursor


_events = defaultdict(deque)
_lock = Lock()


def rate_limit_exceeded(scope, identity, limit, window_seconds):
    if current_app.config.get("TESTING"):
        return False

    if current_app.config.get("RATELIMIT_STORAGE", "database") == "memory":
        return _memory_rate_limit_exceeded(scope, identity, limit, window_seconds)

    identity_hash = hashlib.sha256((identity or "unknown").encode()).hexdigest()
    with db_cursor(dictionary=True, commit=True) as cursor:
        cursor.execute(
            """
            INSERT INTO auth_rate_limits
                (scope, identity_hash, window_started_at, attempts)
            VALUES (%s, %s, NOW(), 1)
            ON DUPLICATE KEY UPDATE
                attempts = IF(
                    window_started_at < DATE_SUB(NOW(), INTERVAL %s SECOND),
                    1,
                    attempts + 1
                ),
                window_started_at = IF(
                    window_started_at < DATE_SUB(NOW(), INTERVAL %s SECOND),
                    NOW(),
                    window_started_at
                )
            """,
            (scope, identity_hash, window_seconds, window_seconds),
        )
        cursor.execute(
            "SELECT attempts FROM auth_rate_limits WHERE scope = %s AND identity_hash = %s",
            (scope, identity_hash),
        )
        attempts = cursor.fetchone()["attempts"]
        cursor.execute(
            "DELETE FROM auth_rate_limits WHERE updated_at < DATE_SUB(NOW(), INTERVAL 2 DAY) LIMIT 100"
        )
    return attempts > limit


def _memory_rate_limit_exceeded(scope, identity, limit, window_seconds):

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
