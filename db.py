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
import time

from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD

import metrics

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

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _sslmode(host: str) -> str:
    explicit = os.getenv("PGSSLMODE")
    if explicit:
        return explicit
    # Hosted Postgres (Neon, etc.) requires TLS. Local clusters usually do not.
    return "disable" if host in _LOCAL_HOSTS else "require"


def _on_vercel() -> bool:
    return bool(os.getenv("VERCEL"))


def _conninfo(dbname: str) -> str:
    host = os.getenv("PGHOST", DB_HOST)
    port = int(os.getenv("PGPORT", DB_PORT))
    user = os.getenv("PGUSER", DB_USER)
    password = os.getenv("PGPASSWORD", DB_PASSWORD)
    # dbname is always one of our own constants (AUTH_DB_NAME, MESS_DB_NAME,
    # ...), never user input, so plain interpolation here is safe.
    # TCP keepalives catch idle drops from hosted Postgres (Neon, etc.).
    return (
        f"host={host} port={port} dbname={dbname} "
        f"user={user} password={password} sslmode={_sslmode(host)} "
        f"client_encoding=UTF8 "
        f"keepalives=1 keepalives_idle=30 keepalives_interval=10 keepalives_count=3"
    )


def _new_pool(dbname: str) -> "ConnectionPool":
    # Vercel freezes the process between requests, so sockets in the pool
    # are often already closed by the time the next invocation starts.
    # min_size=0 avoids holding idle fds; check discards dead ones on
    # checkout instead of handing them to callers (which 500s Ask/Users).
    vercel = _on_vercel()
    return ConnectionPool(
        conninfo=_conninfo(dbname),
        min_size=0 if vercel else POOL_MIN_SIZE,
        max_size=POOL_MAX_SIZE,
        open=True,
        check=ConnectionPool.check_connection,
        max_idle=30.0 if vercel else 600.0,
        max_lifetime=300.0 if vercel else 3600.0,
        timeout=10.0,
        reconnect_timeout=10.0,
    )


def _get_pool(dbname: str) -> "ConnectionPool":
    if dbname not in _pools:
        with _pools_lock:
            if dbname not in _pools:  # re-check inside the lock
                _pools[dbname] = _new_pool(dbname)
    return _pools[dbname]


def _drop_pool(dbname: str) -> None:
    with _pools_lock:
        pool = _pools.pop(dbname, None)
    if pool is None:
        return
    try:
        pool.close()
    except Exception:
        pass


class _PooledConnection:
    """Proxies a real psycopg connection. `.close()` returns it to the pool
    instead of dropping the socket, so existing call sites don't change."""

    __slots__ = ("_pool", "_conn", "_returned", "_dbname", "_started")

    def __init__(self, pool, conn, dbname):
        self._pool = pool
        self._conn = conn
        self._returned = False
        self._dbname = dbname
        self._started = time.perf_counter()

    def close(self):
        if not self._returned:
            self._returned = True
            try:
                metrics.record_db(
                    self._dbname,
                    (time.perf_counter() - self._started) * 1000,
                )
            except Exception:
                pass
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
    sslmode = _sslmode(host)
    try:
        import pg8000
        return pg8000.connect(
            host=host, port=port, database=dbname,
            user=user, password=password, timeout=5,
            ssl_context=sslmode not in ("disable", "allow"),
        )
    except ImportError:
        import psycopg
        return psycopg.connect(
            host=host, port=port, dbname=dbname,
            user=user, password=password, connect_timeout=5,
            sslmode=sslmode,
            client_encoding="UTF8",
        )


class _TrackedConnection:
    """Times a fallback (unpooled) connection from checkout to close."""

    def __init__(self, conn, dbname):
        self._conn = conn
        self._dbname = dbname
        self._started = time.perf_counter()
        self._closed = False

    def close(self):
        if not self._closed:
            self._closed = True
            try:
                metrics.record_db(
                    self._dbname,
                    (time.perf_counter() - self._started) * 1000,
                )
            except Exception:
                pass
            self._conn.close()

    def __getattr__(self, name):
        return getattr(self._conn, name)


def get_connection(dbname: str):
    """Return a connection for `dbname`. Pooled when psycopg_pool is
    installed, otherwise a plain unpooled connection.

    Each checkout is counted in metrics.db_calls / db_latency_ms (time
    from get_connection until close), rather than instrumenting every
    *_functions.py query path.
    """
    if not _POOLING_AVAILABLE:
        return _TrackedConnection(_fallback_connection(dbname), dbname)

    last_exc: Exception | None = None
    for attempt in range(3):
        pool = _get_pool(dbname)
        try:
            conn = pool.getconn()
        except Exception as exc:
            last_exc = exc
            _drop_pool(dbname)
            continue
        if getattr(conn, "closed", 0):
            try:
                pool.putconn(conn)
            except Exception:
                pass
            if attempt == 2:
                break
            continue
        return _PooledConnection(pool, conn, dbname)
    if last_exc is not None:
        raise last_exc
    raise RuntimeError(f"could not get a live connection to {dbname}")


def close_all_pools():
    """Call on app shutdown to close every pool cleanly."""
    with _pools_lock:
        for pool in _pools.values():
            pool.close()
        _pools.clear()
