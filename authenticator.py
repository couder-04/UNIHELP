import time
import threading

import db
from config import AUTH_DB_NAME

# Every A2A request calls authenticate() before doing anything else, so it
# sits on the critical path of every single request. Auth keys change rarely
# (manual user management), so we cache successful lookups for a short TTL
# instead of hitting Postgres on every message.
_CACHE_TTL_SECONDS = 300
_NEGATIVE_CACHE_TTL_SECONDS = 30
_cache_lock = threading.Lock()
_cache: dict = {}  # key -> (expires_at, user_dict_or_None)


def _get_connection():
    return db.get_connection(AUTH_DB_NAME)


def _cache_get(key):
    with _cache_lock:
        entry = _cache.get(key)
        if entry is None:
            return None, False
        expires_at, value = entry
        if time.time() >= expires_at:
            del _cache[key]
            return None, False
        return value, True


def _cache_set(key, value, ttl=_CACHE_TTL_SECONDS):
    with _cache_lock:
        _cache[key] = (time.time() + ttl, value)


def invalidate_auth_cache(key: str = None):
    """Call this if/when user records are edited while the app is running.
    With no argument it clears the whole cache."""
    with _cache_lock:
        if key is None:
            _cache.clear()
        else:
            _cache.pop(key, None)


def list_users():
    """Return every campus_agent.users row for the GUI directory."""
    connection = _get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT authentication_key, role, names, roll_number
            FROM users
            ORDER BY
              CASE LOWER(role)
                WHEN 'admin' THEN 0
                WHEN 'faculty' THEN 1
                ELSE 2
              END,
              names,
              roll_number
            """
        )
        rows = cursor.fetchall()
        cursor.close()
        return [
            {
                "authentication_key": row[0],
                "role": row[1],
                "names": row[2],
                "roll_number": str(row[3]) if row[3] is not None else "",
            }
            for row in rows
        ]
    finally:
        connection.close()


def authenticate(key):
    if not key:
        return None

    cached_value, hit = _cache_get(key)
    if hit:
        return cached_value

    connection = _get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT authentication_key, role, names, roll_number
            FROM users
            WHERE authentication_key = %s
            """,
            (key,)
        )

        row = cursor.fetchone()
        cursor.close()

        if row is None:
            # Cache misses too, but for a much shorter window, so a typo'd
            # key doesn't repeatedly hit the DB while still allowing a
            # just-added user to authenticate quickly.
            _cache_set(key, None, ttl=_NEGATIVE_CACHE_TTL_SECONDS)
            return None

        user = {
            "role": row[1],
            "name": row[2],
            "roll_number": str(row[3]) if row[3] is not None else None,
        }

        _cache_set(key, user)
        return user

    finally:
        connection.close()


# print("Testing key: key")
# print(authenticate("key"))

# print("\nTesting faculty key:")
# print(authenticate("efgh1"))
