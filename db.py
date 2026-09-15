"""
Shared PostgreSQL connection pooling.

Every domain module (mess, bus, room booking, complaints, attendance, auth) used to open
a brand-new socket connection per query and close it immediately after. Under
concurrent users that meant constant connect/auth handshake overhead and a
real risk of exhausting Postgres' max_connections.

This module keeps one psycopg_pool.ConnectionPool per database name (auth,
mess, bus, room, complaints, attendance) and hands out connections from it. Call sites
elsewhere in the codebase are unchanged: they still do

    conn = get_connection()
    ...
    conn.close()

`close()` on the object we return puts the connection back in the pool
instead of actually closing the socket, so no other file needs to change.

If psycopg_pool (or psycopg) isn't installed — e.g. on native Windows where
the C extension sometimes fails to build — this transparently falls back to
the old behavior (one connection per call, via pg8000 if available) so
nothing breaks; you just don't get pooling.

Install with:  pip install "psycopg[binary,pool]"
"""

import os
import threading

from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD

try:
    from psycopg_pool import ConnectionPool
    _POOLING_AVAILABLE = True
except ImportError:
    _POOLING_AVAILABLE = False

_pools = {}
_pools_lock = threading.Lock()

# Tune via env if needed; sane defaults for a small campus app.
POOL_MIN_SIZE = int(os.getenv("DB_POOL_MIN_SIZE", "1"))
POOL_MAX_SIZE = int(os.getenv("DB_POOL_MAX_SIZE", "10"))


def _conninfo(dbname: str) -> str:
    host = os.getenv("PGHOST", DB_HOST)
    port = int(os.getenv("PGPORT", DB_PORT))
    user = os.getenv("PGUSER", DB_USER)
    password = os.getenv("PGPASSWORD", DB_PASSWORD)
    # dbname is always one of our own constants (AUTH_DB_NAME, MESS_DB_NAME,
    # ...), never user input, so plain interpolation here is safe.
    return (
        f"host={host} port={port} dbname={dbname} "
        f"user={user} password={password}"
    )


def _get_pool(dbname: str) -> "ConnectionPool":
    if dbname not in _pools:
        with _pools_lock:
            if dbname not in _pools:  # re-check inside the lock
                _pools[dbname] = ConnectionPool(
                    conninfo=_conninfo(dbname),
                    min_size=POOL_MIN_SIZE,
                    max_size=POOL_MAX_SIZE,
                    open=True,
                )
    return _pools[dbname]


class _PooledConnection:
    """Proxies a real psycopg connection. `.close()` returns it to the pool
    instead of dropping the socket, so existing call sites don't change."""

    __slots__ = ("_pool", "_conn", "_returned")

    def __init__(self, pool, conn):
        self._pool = pool
        self._conn = conn
        self._returned = False

    def close(self):
        if not self._returned:
            self._returned = True
            try:
                self._pool.putconn(self._conn)
            except Exception:
                # Connection was broken; let the pool discard it rather
                # than raise out of a finally block in caller code.
                pass

    def __enter__(self):
        self._conn.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        return self._conn.__exit__(exc_type, exc, tb)

    def __getattr__(self, name):
        return getattr(self._conn, name)


def _fallback_connection(dbname: str):
    """Old, non-pooled behavior — used only when psycopg_pool isn't
    installed. One fresh connection per call, pg8000 first (pure Python,
    works on Windows without a C toolchain), psycopg as a fallback."""
    host = os.getenv("PGHOST", DB_HOST)
    port = int(os.getenv("PGPORT", DB_PORT))
    user = os.getenv("PGUSER", DB_USER)
    password = os.getenv("PGPASSWORD", DB_PASSWORD)
    try:
        import pg8000
        return pg8000.connect(
            host=host, port=port, database=dbname,
            user=user, password=password, timeout=5,
        )
    except ImportError:
        import psycopg
        return psycopg.connect(
            host=host, port=port, dbname=dbname,
            user=user, password=password, connect_timeout=5,
        )


def get_connection(dbname: str):
    """Return a connection for `dbname`. Pooled when psycopg_pool is
    installed, otherwise a plain unpooled connection."""
    if not _POOLING_AVAILABLE:
        return _fallback_connection(dbname)

    pool = _get_pool(dbname)
    conn = pool.getconn()
    return _PooledConnection(pool, conn)


def close_all_pools():
    """Call on app shutdown to close every pool cleanly."""
    with _pools_lock:
        for pool in _pools.values():
            pool.close()
        _pools.clear()
