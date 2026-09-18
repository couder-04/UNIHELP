"""Canonical campus_agent.people table and live-data backfill.

campus_agent.users, complaints.users, organization_agent.people, and
timetable.people all stored overlapping identity. This module creates one
people table in campus_agent (the auth DB), backfills it from users, and
adds person_id columns on the duplicate/domain tables so FKs can move
over without a cross-database REFERENCES (Postgres cannot FK across DBs).

Old identity columns stay in place unused-for-resolution for one release.
"""

from __future__ import annotations

import hashlib
import logging
import uuid

import db
import org_profile
from config import (
    ATTENDANCE_DB_NAME,
    AUTH_DB_NAME,
    COMPLAINTS_DB_NAME,
    TIMETABLE_DB_NAME,
)

logger = logging.getLogger(__name__)

# SUPERSEDED: campus_agent.users is kept for rollback. Scheduled for
# removal once people FKs are confirmed in production for a full cycle.
_USERS_SUPERSEDED_COMMENT = (
    "SUPERSEDED by people. Kept for one release for rollback. "
    "Scheduled for removal once domain person_id columns are confirmed "
    "correct in production for a full cycle."
)

_PEOPLE_DDL = """
CREATE TABLE IF NOT EXISTS people (
    id UUID PRIMARY KEY,
    org_id TEXT NOT NULL,
    external_id TEXT NOT NULL,
    role TEXT NOT NULL,
    display_name TEXT NOT NULL,
    auth_key_hash TEXT NOT NULL,
    authentication_key TEXT NOT NULL,
    CONSTRAINT people_role_check
        CHECK (LOWER(role) IN ('student', 'faculty', 'admin')),
    CONSTRAINT people_org_external_key UNIQUE (org_id, external_id),
    CONSTRAINT people_auth_key_hash_key UNIQUE (auth_key_hash),
    CONSTRAINT people_authentication_key_key UNIQUE (authentication_key)
)
"""


def hash_auth_key(key: str) -> str:
    return hashlib.sha256((key or "").encode("utf-8")).hexdigest()


def _conn(dbname: str):
    return db.get_connection(dbname)


def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
          AND column_name = %s
        """,
        (table, column),
    )
    return cursor.fetchone() is not None


def _table_exists(cursor, table: str) -> bool:
    cursor.execute(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = %s
        """,
        (table,),
    )
    return cursor.fetchone() is not None


def _comment_on_table(cursor, table: str, comment: str) -> None:
    # COMMENT ON TABLE does not accept bind parameters.
    escaped = comment.replace("'", "''")
    cursor.execute(f"COMMENT ON TABLE {table} IS '{escaped}'")


def _ensure_campus_people(cursor) -> None:
    cursor.execute(_PEOPLE_DDL)
    if _table_exists(cursor, "users"):
        _comment_on_table(cursor, "users", _USERS_SUPERSEDED_COMMENT)

    cursor.execute("SELECT authentication_key FROM people")
    existing_keys = {row[0] for row in cursor.fetchall()}

    if not _table_exists(cursor, "users"):
        return

    cursor.execute(
        "SELECT authentication_key, role, names, roll_number FROM users"
    )
    rows = cursor.fetchall()
    org_id = org_profile.ORG.org_id
    identity = org_profile.ORG.identity
    inserted = 0
    for auth_key, role, names, roll in rows:
        if auth_key in existing_keys:
            continue
        role_n = (role or "").strip().lower()
        external_id = "" if roll is None else str(roll).strip()
        if role_n == "student":
            try:
                identity.validate_student_external_id(external_id)
            except org_profile.OrgProfileError:
                logger.warning(
                    "Skipping people backfill for student %r: id does not match %s",
                    external_id,
                    identity.student_id_pattern,
                )
                continue
        person_id = uuid.uuid4()
        cursor.execute(
            """
            INSERT INTO people (
                id, org_id, external_id, role, display_name,
                auth_key_hash, authentication_key
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (authentication_key) DO NOTHING
            """,
            (
                str(person_id),
                org_id,
                external_id,
                role_n,
                names,
                hash_auth_key(str(auth_key)),
                auth_key,
            ),
        )
        inserted += 1
    if inserted:
        logger.info("Backfilled %s campus_agent.people rows from users", inserted)


def _people_by_external_id(cursor) -> dict[str, str]:
    cursor.execute("SELECT LOWER(external_id), id::text FROM people")
    return {row[0]: row[1] for row in cursor.fetchall() if row[0]}


def _add_person_id_column(cursor, table: str) -> None:
    if _column_exists(cursor, table, "person_id"):
        return
    cursor.execute(f"ALTER TABLE {table} ADD COLUMN person_id UUID")
    logger.info("Added %s.person_id (logical FK to campus_agent.people.id)", table)


def _backfill_by_roll(cursor, table: str, roll_column: str, mapping: dict[str, str]) -> int:
    if not _column_exists(cursor, table, "person_id"):
        return 0
    cursor.execute(
        f"SELECT {roll_column} FROM {table} WHERE person_id IS NULL"
    )
    updated = 0
    for (roll,) in cursor.fetchall():
        if roll is None:
            continue
        person_id = mapping.get(str(roll).strip().lower())
        if not person_id:
            continue
        cursor.execute(
            f"UPDATE {table} SET person_id = %s WHERE {roll_column} = %s AND person_id IS NULL",
            (person_id, roll),
        )
        updated += cursor.rowcount or 0
    return updated


def _backfill_complaints_domain(cursor, mapping: dict[str, str]) -> None:
    if _table_exists(cursor, "users"):
        _add_person_id_column(cursor, "users")
        n = _backfill_by_roll(cursor, "users", "roll_number", mapping)
        if n:
            logger.info("Backfilled complaints.users.person_id on %s rows", n)
        _comment_on_table(
            cursor,
            "users",
            "SUPERSEDED by campus_agent.people. person_id links to "
            "the canonical row. Identity columns kept for one release.",
        )

    if _table_exists(cursor, "complaints"):
        _add_person_id_column(cursor, "complaints")
        if _column_exists(cursor, "users", "person_id"):
            cursor.execute(
                """
                UPDATE complaints c
                SET person_id = u.person_id
                FROM users u
                WHERE c.user_id = u.id
                  AND c.person_id IS NULL
                  AND u.person_id IS NOT NULL
                """
            )
            if cursor.rowcount:
                logger.info(
                    "Backfilled complaints.complaints.person_id on %s rows",
                    cursor.rowcount,
                )


def _backfill_roster(dbname: str, table: str, roll_column: str, mapping: dict[str, str]) -> None:
    connection = _conn(dbname)
    try:
        cursor = connection.cursor()
        if not _table_exists(cursor, table):
            cursor.close()
            return
        _add_person_id_column(cursor, table)
        n = _backfill_by_roll(cursor, table, roll_column, mapping)
        _comment_on_table(
            cursor,
            table,
            "Roster copy of identity. person_id links to "
            "campus_agent.people; roll/name/role columns kept for "
            "one release until domain FKs are confirmed.",
        )
        connection.commit()
        cursor.close()
        if n:
            logger.info("Backfilled %s.%s.person_id on %s rows", dbname, table, n)
    finally:
        connection.close()


_ready = False


def ensure_canonical_people() -> None:
    """Idempotent startup migration. Safe to call more than once."""
    global _ready
    if _ready:
        return

    connection = _conn(AUTH_DB_NAME)
    try:
        cursor = connection.cursor()
        _ensure_campus_people(cursor)
        mapping = _people_by_external_id(cursor)
        connection.commit()
        cursor.close()
    finally:
        connection.close()

    complaints = _conn(COMPLAINTS_DB_NAME)
    try:
        cursor = complaints.cursor()
        _backfill_complaints_domain(cursor, mapping)
        complaints.commit()
        cursor.close()
    finally:
        complaints.close()

    _backfill_roster(ATTENDANCE_DB_NAME, "people", "roll_num", mapping)
    _backfill_roster(TIMETABLE_DB_NAME, "people", "roll_num", mapping)

    _ready = True
    logger.info("Canonical people table is ready (org_id=%s)", org_profile.ORG.org_id)
