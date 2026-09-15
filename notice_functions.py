import os
import json
from datetime import datetime
from typing import List, Dict, Any
import psycopg
from psycopg.rows import dict_row

from config import DB_HOST, DB_PORT, NOTICE_DB_NAME, DB_USER, DB_PASSWORD

def get_connection():
    host = os.getenv("PGHOST", DB_HOST)
    port = int(os.getenv("PGPORT", DB_PORT))
    dbname = os.getenv("PGDATABASE", NOTICE_DB_NAME)
    user = os.getenv("PGUSER", DB_USER)
    password = os.getenv("PGPASSWORD", DB_PASSWORD)
    return psycopg.connect(
        host=host, port=port, dbname=dbname, user=user, password=password, connect_timeout=5
    )

def _check_write_authorization(role: str):
    if not isinstance(role, str) or role.lower() not in ("faculty", "admin"):
        return {"status": "error", "message": "Not authorised."}
    return None

def publish_notice(content: str, notice_type: str, author_id: str, author_authority: str, target_audience: List[str], expires_at: str, user: str = None) -> Dict[str, Any]:
    # RBAC check
    role = user or author_authority
    auth_err = _check_write_authorization(role)
    if auth_err:
        return auth_err

    conn = get_connection()
    try:
        with conn.cursor(row_factory=dict_row) as cur:
            query = """
                INSERT INTO notices (content, notice_type, author_id, author_authority, target_audience, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, publish_timestamp;
            """
            cur.execute(query, (content, notice_type, author_id, role, target_audience, expires_at))
            res = cur.fetchone()
            conn.commit()
            return {"status": "success", "id": str(res["id"]), "publish_timestamp": str(res["publish_timestamp"])}
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()

def view_notices(caller_audience: str, caller_authority: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor(row_factory=dict_row) as cur:
            if caller_authority.lower() == "admin":
                query = "SELECT * FROM notices WHERE status = 'Active' ORDER BY publish_timestamp DESC;"
                cur.execute(query)
            else:
                query = """
                    SELECT * FROM notices 
                    WHERE status = 'Active' 
                      AND ('All' = ANY(target_audience) OR %s = ANY(target_audience))
                    ORDER BY publish_timestamp DESC;
                """
                cur.execute(query, (caller_audience,))
            rows = cur.fetchall()
            for r in rows:
                r["id"] = str(r["id"])
                r["publish_timestamp"] = str(r["publish_timestamp"])
                r["expires_at"] = str(r["expires_at"]) if r["expires_at"] else None
            return rows
    except Exception as e:
        return [{"error": str(e)}]
    finally:
        conn.close()

def archive_expired_notices(user: str = None) -> Dict[str, Any]:
    auth_err = _check_write_authorization(user or "")
    if auth_err:
        return auth_err

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE notices SET status = 'Archived' WHERE status = 'Active' AND expires_at < CURRENT_TIMESTAMP;")
            count = cur.rowcount
            conn.commit()
            return {"status": "success", "archived_count": count}
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()

TOOLS = {
    "publish_notice": publish_notice,
    "view_notices": view_notices,
    "archive_expired_notices": archive_expired_notices,
}

def call_tool(name: str, **kwargs) -> str:
    fn = TOOLS.get(name)
    if not fn:
        return json.dumps({"error": f"Unknown tool '{name}'."})
    try:
        return json.dumps(fn(**kwargs), indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": f"Tool execution failed: {exc}"})