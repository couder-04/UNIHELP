import json
import random
import re
import string
from datetime import datetime, timezone

import db
from config import COMPLAINTS_DB_NAME

try:
    from psycopg.errors import UniqueViolation
except ImportError:
    UniqueViolation = tuple()


# ============================================================
# DATABASE
# ============================================================

def get_connection():
    """Pooled connection when psycopg_pool is installed (see db.py)."""
    return db.get_connection(COMPLAINTS_DB_NAME)


# ============================================================
# CONSTANTS / HELPERS
# ============================================================

VALID_CATEGORIES = {"academic", "hostel", "mess"}
VALID_STATUSES = {"PENDING_VERIFICATION", "PROGRESS", "COMPLETED"}
MAX_COMPLETED_PER_CATEGORY = 50

STAFF_ROLES = {"Faculty", "Admin", "Warden", "HOD"}


def _clean(value):
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    return value.strip()


def _normalize_text(value):
    cleaned = _clean(value)
    if not cleaned:
        return ""
    return re.sub(r"\s+", " ", cleaned).lower()


def _gen_complaint_number():
    return "C-" + "".join(random.choices(string.digits, k=6))


def _normalize_role(role):
    if not role:
        return None
    mapping = {
        "student": "Student",
        "faculty": "Faculty",
        "warden": "Warden",
        "technician": "Technician",
        "hod": "HOD",
        "admin": "Admin",
        "guest": "Guest",
    }
    return mapping.get(role.strip().lower(), role.strip())


def _resolve_user(user_identifier: str):
    """
    Resolve a user identifier to internal DB user data.

    Public API accepts:
      - student/staff roll number (stored as UUID, equal to users.id)
      - staff/faculty email

    Returns:
      (internal_user_id, role, roll_number, email)
    """
    identifier = _clean(user_identifier)
    if not identifier:
        return None, None, None, None

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, COALESCE(hierarchy_level, role), roll_number, email
            FROM users
            WHERE (
                roll_number::text = LOWER(%s)
                OR id::text = LOWER(%s)
            )
              AND is_active = TRUE
            LIMIT 1
            """,
            (identifier, identifier),
        )
        row = cur.fetchone()
        if row:
            return row[0], row[1], row[2], row[3]

        cur.execute(
            """
            SELECT id, COALESCE(hierarchy_level, role), roll_number, email
            FROM users
            WHERE LOWER(email) = LOWER(%s)
              AND is_active = TRUE
            LIMIT 1
            """,
            (identifier,),
        )
        row = cur.fetchone()
        if row:
            return row[0], row[1], row[2], row[3]

        return None, None, None, None
    finally:
        cur.close()
        conn.close()


def _history(cur, complaint_db_id, actor_db_id, actor_role, action,
             from_status=None, to_status=None, extra=None, now=None):
    now = now or datetime.now(timezone.utc)
    cur.execute(
        """
        INSERT INTO complaint_history
            (complaint_id, actor_id, actor_role, action, from_status,
             to_status, extra, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            complaint_db_id,
            actor_db_id,
            actor_role,
            action,
            from_status,
            to_status,
            json.dumps(extra) if extra is not None else None,
            now,
        ),
    )


def _find_open_duplicate(cur, category, title, description):
    """Return an open complaint with the same category + title + description."""
    cur.execute(
        """
        SELECT complaint_number, status
        FROM complaints
        WHERE LOWER(category) = LOWER(%s)
          AND status IN ('PENDING_VERIFICATION', 'PROGRESS')
          AND LOWER(btrim(title)) = LOWER(btrim(%s))
          AND LOWER(btrim(description)) = LOWER(btrim(%s))
        LIMIT 1
        """,
        (category, title, description),
    )
    row = cur.fetchone()
    if not row:
        return None
    return {"complaint_number": row[0], "complaint_status": row[1]}


def _duplicate_response(existing):
    return {
        "status": "duplicate",
        "message": (
            f"This complaint is already logged as {existing['complaint_number']} "
            f"and is currently {existing['complaint_status']}. "
            "It will not be created again until that complaint is completed."
        ),
        "complaint_number": existing["complaint_number"],
        "complaint_status": existing["complaint_status"],
    }


def _prune_completed(cur, category):
    """Keep only the latest 50 COMPLETED complaints in this category."""
    cur.execute(
        """
        DELETE FROM complaints
        WHERE LOWER(category) = LOWER(%s)
          AND status = 'COMPLETED'
          AND id NOT IN (
              SELECT id
              FROM complaints
              WHERE LOWER(category) = LOWER(%s)
                AND status = 'COMPLETED'
              ORDER BY completed_at DESC NULLS LAST, created_at DESC
              LIMIT %s
          )
        """,
        (category, category, MAX_COMPLETED_PER_CATEGORY),
    )


# ============================================================
# PUBLIC COMPLAINT FUNCTIONS
# ============================================================

def create_complaint(
    user_identifier: str,
    title: str,
    description: str,
    category: str,
    visibility: str = None,
    subcategory: str = None,
    hostel_id: str = None,
    block: str = None,
    floor: str = None,
    location: str = None,
    asset_name: str = None,
):
    """Create a complaint tagged academic, hostel, or mess."""
    # Extra kwargs are accepted so older agent tool calls still parse,
    # but they are ignored by the simplified workflow.
    _ = (visibility, subcategory, hostel_id, block, floor, location, asset_name)

    category = _normalize_text(category)
    title = _clean(title)
    description = _clean(description)

    if category not in VALID_CATEGORIES:
        return {
            "status": "error",
            "message": "category must be academic, hostel, or mess",
        }
    if not title or not description:
        return {"status": "error", "message": "title and description are required"}

    user_db_id, role, _, _ = _resolve_user(user_identifier)
    if not user_db_id:
        return {"status": "error", "message": "User not found. Use student roll number or staff email."}

    role = _normalize_role(role)
    if role == "Guest":
        return {"status": "forbidden", "message": "Guest users cannot create complaints"}

    conn = get_connection()
    cur = conn.cursor()
    try:
        existing = _find_open_duplicate(cur, category, title, description)
        if existing:
            return _duplicate_response(existing)

        now = datetime.now(timezone.utc)
        complaint_number = None
        for _ in range(5):
            candidate = _gen_complaint_number()
            cur.execute(
                "SELECT 1 FROM complaints WHERE complaint_number = %s",
                (candidate,),
            )
            if not cur.fetchone():
                complaint_number = candidate
                break

        if not complaint_number:
            return {"status": "error", "message": "Could not generate a unique complaint number"}

        cur.execute(
            """
            INSERT INTO complaints (
                complaint_number, user_id, title, description,
                category, status, created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s,
                %s, 'PENDING_VERIFICATION', %s, %s
            )
            RETURNING id
            """,
            (complaint_number, user_db_id, title, description, category, now, now),
        )
        complaint_db_id = cur.fetchone()[0]

        _history(
            cur,
            complaint_db_id,
            user_db_id,
            role,
            "complaint_created",
            to_status="PENDING_VERIFICATION",
            extra={"category": category},
            now=now,
        )

        conn.commit()
        return {
            "status": "success",
            "complaint_number": complaint_number,
            "complaint_status": "PENDING_VERIFICATION",
            "category": category,
            "message": (
                f"Complaint {complaint_number} logged under {category} "
                "and is waiting for admin/faculty verification."
            ),
        }
    except UniqueViolation:
        conn.rollback()
        existing = _find_open_duplicate(cur, category, title, description)
        if existing:
            return _duplicate_response(existing)
        return {"status": "error", "message": "This complaint is already logged and still open."}
    except Exception as exc:
        conn.rollback()
        message = str(exc).lower()
        if "uniq_open_complaints" in message or "duplicate" in message:
            existing = _find_open_duplicate(cur, category, title, description)
            if existing:
                return _duplicate_response(existing)
            return {"status": "error", "message": "This complaint is already logged and still open."}
        return {"status": "error", "message": f"Failed to create complaint: {exc}"}
    finally:
        cur.close()
        conn.close()


def get_complaint(complaint_number: str, user_identifier: str = None):
    """Get a complaint using its human complaint number, e.g. C-123456."""
    if not complaint_number:
        return {"status": "error", "message": "complaint_number is required"}
    if not user_identifier:
        return {"status": "forbidden", "message": "Authenticated user identifier is required"}

    user_db_id, role, _, _ = _resolve_user(user_identifier)
    if not user_db_id:
        return {"status": "error", "message": "User not found. Use roll number or email."}
    role = _normalize_role(role)

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT c.complaint_number, c.title, c.description, c.category, c.status,
                   c.created_at, c.verified_at, c.completed_at, c.user_id,
                   COALESCE(u.email, u.roll_number::text) AS reporter
            FROM complaints c
            JOIN users u ON u.id = c.user_id
            WHERE c.complaint_number = %s
            """,
            (_clean(complaint_number).upper(),),
        )
        row = cur.fetchone()
        if not row:
            return {"status": "not_found", "message": "Complaint not found"}

        columns = [d[0] for d in cur.description]
        complaint = dict(zip(columns, row))
        owner_id = complaint.pop("user_id", None)

        if role not in STAFF_ROLES and owner_id != user_db_id:
            return {"status": "forbidden", "message": "Not authorized to view this complaint"}

        return {"status": "success", "complaint": complaint}
    finally:
        cur.close()
        conn.close()


def list_complaints(
    user_identifier: str = None,
    status: str = None,
    category: str = None,
    visibility: str = None,
    limit: int = 50,
):
    """List complaints visible to the authenticated user."""
    _ = visibility
    if not user_identifier:
        return {"status": "forbidden", "message": "Authenticated user identifier is required"}

    user_db_id, role, _, _ = _resolve_user(user_identifier)
    if not user_db_id:
        return {"status": "error", "message": "User not found. Use roll number or email."}
    role = _normalize_role(role)

    try:
        limit = max(1, min(int(limit), 100))
    except (TypeError, ValueError):
        limit = 50

    status = _clean(status).upper() if status else None
    category = _normalize_text(category) if category else None
    if status and status not in VALID_STATUSES:
        return {"status": "error", "message": f"Invalid status: {status}"}
    if category and category not in VALID_CATEGORIES:
        return {"status": "error", "message": "category must be academic, hostel, or mess"}

    conn = get_connection()
    cur = conn.cursor()
    try:
        where = []
        params = []

        if role not in STAFF_ROLES:
            where.append("c.user_id = %s")
            params.append(user_db_id)

        if status:
            where.append("c.status = %s")
            params.append(status)
        if category:
            where.append("LOWER(c.category) = LOWER(%s)")
            params.append(category)

        where_sql = "WHERE " + " AND ".join(where) if where else ""
        cur.execute(
            f"""
            SELECT c.complaint_number, c.title, c.description, c.category, c.status,
                   c.created_at, c.verified_at, c.completed_at,
                   COALESCE(u.email, u.roll_number::text) AS reporter
            FROM complaints c
            JOIN users u ON u.id = c.user_id
            {where_sql}
            ORDER BY c.created_at DESC
            LIMIT %s
            """,
            params + [limit],
        )
        rows = cur.fetchall()
        columns = [d[0] for d in cur.description]
        return {"status": "success", "complaints": [dict(zip(columns, r)) for r in rows]}
    finally:
        cur.close()
        conn.close()


def verify_complaint(complaint_number: str, verifier_identifier: str):
    """Admin/faculty verify a pending complaint and move it to PROGRESS."""
    verifier_db_id, verifier_role, _, _ = _resolve_user(verifier_identifier)
    if not verifier_db_id:
        return {"status": "error", "message": "Verifier not found. Use staff email or roll number."}
    verifier_role = _normalize_role(verifier_role)
    if verifier_role not in STAFF_ROLES:
        return {"status": "forbidden", "message": "Only faculty or admin can verify complaints"}

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id, status FROM complaints WHERE complaint_number = %s",
            (_clean(complaint_number).upper(),),
        )
        row = cur.fetchone()
        if not row:
            return {"status": "not_found", "message": "Complaint not found"}

        complaint_db_id, old_status = row
        if old_status == "PROGRESS":
            return {"status": "error", "message": "Complaint is already under PROGRESS"}
        if old_status == "COMPLETED":
            return {"status": "error", "message": "Completed complaints cannot be verified again"}
        if old_status != "PENDING_VERIFICATION":
            return {"status": "error", "message": f"Cannot verify from status {old_status}"}

        now = datetime.now(timezone.utc)
        cur.execute(
            """
            UPDATE complaints
            SET status = 'PROGRESS',
                verified_by = %s,
                verified_at = %s,
                updated_at = %s
            WHERE id = %s
            """,
            (verifier_db_id, now, now, complaint_db_id),
        )
        _history(
            cur, complaint_db_id, verifier_db_id, verifier_role,
            "complaint_verified", from_status=old_status, to_status="PROGRESS", now=now
        )
        conn.commit()
        return {
            "status": "success",
            "complaint_number": _clean(complaint_number).upper(),
            "complaint_status": "PROGRESS",
            "message": "Complaint verified and moved to PROGRESS",
        }
    except Exception as exc:
        conn.rollback()
        return {"status": "error", "message": f"Verify failed: {exc}"}
    finally:
        cur.close()
        conn.close()


def complete_complaint(complaint_number: str, actor_identifier: str):
    """Admin/faculty mark a complaint in PROGRESS as COMPLETED."""
    actor_db_id, actor_role, _, _ = _resolve_user(actor_identifier)
    if not actor_db_id:
        return {"status": "error", "message": "Actor not found. Use staff email or roll number."}
    actor_role = _normalize_role(actor_role)
    if actor_role not in STAFF_ROLES:
        return {"status": "forbidden", "message": "Only faculty or admin can complete complaints"}

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id, status, category FROM complaints WHERE complaint_number = %s",
            (_clean(complaint_number).upper(),),
        )
        row = cur.fetchone()
        if not row:
            return {"status": "not_found", "message": "Complaint not found"}

        complaint_db_id, old_status, category = row
        if old_status == "COMPLETED":
            return {"status": "error", "message": "Complaint is already COMPLETED"}
        if old_status != "PROGRESS":
            return {
                "status": "error",
                "message": "Complaint must be verified and under PROGRESS before it can be completed",
            }

        now = datetime.now(timezone.utc)
        cur.execute(
            """
            UPDATE complaints
            SET status = 'COMPLETED',
                completed_by = %s,
                completed_at = %s,
                updated_at = %s
            WHERE id = %s
            """,
            (actor_db_id, now, now, complaint_db_id),
        )
        _history(
            cur, complaint_db_id, actor_db_id, actor_role,
            "complaint_completed", from_status=old_status, to_status="COMPLETED", now=now
        )
        # Trigger also prunes; this keeps the cap even if the trigger is missing.
        _prune_completed(cur, category)
        conn.commit()
        return {
            "status": "success",
            "complaint_number": _clean(complaint_number).upper(),
            "complaint_status": "COMPLETED",
            "message": "Complaint marked COMPLETED",
        }
    except Exception as exc:
        conn.rollback()
        return {"status": "error", "message": f"Complete failed: {exc}"}
    finally:
        cur.close()
        conn.close()


def update_status(complaint_number: str, new_status: str, actor_identifier: str):
    """Map the simplified status words onto verify / complete."""
    new_status = _clean(new_status).upper() if new_status else ""
    aliases = {
        "IN_PROGRESS": "PROGRESS",
        "RESOLVED": "COMPLETED",
        "CLOSED": "COMPLETED",
        "VERIFIED": "PROGRESS",
    }
    new_status = aliases.get(new_status, new_status)

    if new_status == "PROGRESS":
        return verify_complaint(complaint_number, actor_identifier)
    if new_status == "COMPLETED":
        return complete_complaint(complaint_number, actor_identifier)
    return {
        "status": "error",
        "message": "Valid statuses are PROGRESS (after verify) and COMPLETED",
    }


def search_duplicates(
    category: str,
    query: str = None,
    title: str = None,
    description: str = None,
    hostel_id: str = None,
    block: str = None,
    floor: str = None,
    location: str = None,
):
    """Find an open duplicate before creating a complaint."""
    _ = (hostel_id, block, floor, location)
    category = _normalize_text(category) if category else None
    title = _clean(title)
    description = _clean(description)
    query = _clean(query)

    if not category:
        return {"status": "error", "message": "category must be academic, hostel, or mess"}
    if category not in VALID_CATEGORIES:
        return {"status": "error", "message": "category must be academic, hostel, or mess"}

    conn = get_connection()
    cur = conn.cursor()
    try:
        if title and description:
            existing = _find_open_duplicate(cur, category, title, description)
            duplicates = [existing] if existing else []
            return {"status": "success", "duplicates": duplicates}

        where = [
            "LOWER(category) = LOWER(%s)",
            "status IN ('PENDING_VERIFICATION', 'PROGRESS')",
        ]
        params = [category]
        if query:
            where.append("(LOWER(title) LIKE %s OR LOWER(description) LIKE %s)")
            like = f"%{query.lower()}%"
            params.extend([like, like])

        cur.execute(
            f"""
            SELECT complaint_number, title, description, category, status, created_at
            FROM complaints
            WHERE {' AND '.join(where)}
            ORDER BY created_at DESC
            LIMIT 10
            """,
            params,
        )
        rows = cur.fetchall()
        columns = [d[0] for d in cur.description]
        return {"status": "success", "duplicates": [dict(zip(columns, r)) for r in rows]}
    finally:
        cur.close()
        conn.close()


# ============================================================
# SIMPLE DIRECT TEST
# ============================================================

def run_complaint_lifecycle_tests():
    print("--- Starting simplified complaint lifecycle tests ---\n")

    print("1. Creating complaint...")
    res_create = create_complaint(
        user_identifier="3a63c6fe-18be-4110-8bfc-02f8538eaaab",
        title="Cold lunch in CV Raman mess",
        description="Lunch was served cold today in CV Raman hostel.",
        category="mess",
    )
    print(json.dumps(res_create, indent=2, default=str))
    comp_num = res_create.get("complaint_number")
    if not comp_num:
        print("Failed to create complaint. Aborting tests.")
        return

    print("\n2. Duplicate create should be rejected...")
    res_dup = create_complaint(
        user_identifier="3a63c6fe-18be-4110-8bfc-02f8538eaaab",
        title="Cold lunch in CV Raman mess",
        description="Lunch was served cold today in CV Raman hostel.",
        category="mess",
    )
    print(json.dumps(res_dup, indent=2, default=str))

    print(f"\n3. Verifying {comp_num} as faculty...")
    res_verify = verify_complaint(comp_num, "271875d6-51ca-4236-9d13-3d43c25d0320")
    print(json.dumps(res_verify, indent=2, default=str))

    print("\n4. Duplicate while in PROGRESS should still be rejected...")
    res_dup2 = create_complaint(
        user_identifier="3a63c6fe-18be-4110-8bfc-02f8538eaaab",
        title="Cold lunch in CV Raman mess",
        description="Lunch was served cold today in CV Raman hostel.",
        category="mess",
    )
    print(json.dumps(res_dup2, indent=2, default=str))

    print(f"\n5. Completing {comp_num} as admin...")
    res_complete = complete_complaint(comp_num, "3af87d28-f359-4494-9dbe-f6d765b40d8b")
    print(json.dumps(res_complete, indent=2, default=str))


if __name__ == "__main__":
    print("Complaint functions loaded successfully.")
    print("Public user identifiers: student roll number / staff email")
    print("Public complaint identifier: complaint number (C-XXXXXX)")
    print("Statuses: PENDING_VERIFICATION -> PROGRESS -> COMPLETED")
    run_complaint_lifecycle_tests()
