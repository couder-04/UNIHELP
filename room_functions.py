"""Room booking service functions for SAC Hall, Guest House, CLH, and Auditorium."""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal

import db
from config import ROOM_DB_NAME

try:
    from psycopg.errors import ExclusionViolation
    from psycopg.rows import dict_row
except ImportError:
    ExclusionViolation = tuple()
    dict_row = None

NOT_IN_AUTHORITY = {"status": "error", "message": "Not in your authority."}

HOURLY_DURATION = {
    "SAC_HALL": 1,
    "CLH": 1,
    "AUDITORIUM": 3,
}

DIRECT_ROLES = {
    "SAC_HALL": {"student"},
    "GUEST_HOUSE": {"student", "faculty", "admin"},
    "CLH": {"faculty", "admin"},
    "AUDITORIUM": {"admin"},
}

REQUEST_ROLES = {
    "CLH": {"student"},
    "AUDITORIUM": {"student", "faculty"},
}

_FACILITY_ALIASES = {
    "sac hall": "SAC_HALL",
    "sac": "SAC_HALL",
    "sac_hall": "SAC_HALL",
    "sac-hall": "SAC_HALL",
    "sachall": "SAC_HALL",
    "guest house": "GUEST_HOUSE",
    "guesthouse": "GUEST_HOUSE",
    "guest_house": "GUEST_HOUSE",
    "guest-house": "GUEST_HOUSE",
    "gh": "GUEST_HOUSE",
    "clh": "CLH",
    "auditorium": "AUDITORIUM",
}


def get_connection():
    return db.get_connection(ROOM_DB_NAME)


@contextmanager
def _cursor(commit=False):
    connection = get_connection()
    cursor = connection.cursor(row_factory=dict_row) if dict_row else connection.cursor()
    try:
        yield connection, cursor
        if commit:
            connection.commit()
        else:
            connection.rollback()
    except Exception:
        try:
            connection.rollback()
        except Exception:
            pass
        raise
    finally:
        cursor.close()
        connection.close()


def _jsonable(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _row_dict(row):
    if row is None:
        return None
    if isinstance(row, dict):
        return {k: _jsonable(v) for k, v in row.items()}
    return row


def _role(user):
    return str((user or {}).get("role") or "").strip().lower()


def _name(user):
    return str((user or {}).get("name") or "").strip()


def _roll(user):
    value = (user or {}).get("roll_number")
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _is_admin(user):
    return _role(user) == "admin"


def _owns(user, owner_name, owner_roll):
    if _is_admin(user):
        return True
    user_roll = _roll(user)
    if user_roll and owner_roll:
        return str(user_roll) == str(owner_roll)
    return _name(user) == str(owner_name or "").strip()


def _mine_filter(user, name_col, roll_col):
    user_roll = _roll(user)
    if user_roll:
        return f"{roll_col} = %s", (user_roll,)
    return f"{name_col} = %s", (_name(user),)


def _normalize_facility(facility):
    if facility is None:
        return None
    key = str(facility).strip().lower().replace("  ", " ")
    if key in _FACILITY_ALIASES:
        return _FACILITY_ALIASES[key]
    compact = key.replace("_", " ").replace("-", " ")
    if compact in _FACILITY_ALIASES:
        return _FACILITY_ALIASES[compact]
    return None


def _as_date(value, field_name):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError:
        raise ValueError(f"{field_name} must be YYYY-MM-DD.")


def _as_int(value, field_name, allow_none=True):
    if value is None or value == "":
        if allow_none:
            return None
        raise ValueError(f"{field_name} is required.")
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be an integer.")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not value.is_integer():
            raise ValueError(f"{field_name} must be an integer.")
        return int(value)
    text = str(value).strip()
    if text.lstrip("-").isdigit():
        return int(text)
    raise ValueError(f"{field_name} must be an integer.")


def _normalize_room_type(room_type):
    if room_type is None or room_type == "":
        return None
    value = str(room_type).strip().upper()
    if value in {"SINGLE", "DOUBLE", "STANDARD"}:
        return value
    raise ValueError("room_type must be SINGLE or DOUBLE.")


def _hourly_window(facility_type, start_hour, duration_hours):
    expected = HOURLY_DURATION[facility_type]
    if duration_hours is None:
        duration_hours = expected
    start_hour = _as_int(start_hour, "start_hour", allow_none=False)
    duration_hours = _as_int(duration_hours, "duration_hours", allow_none=False)
    if start_hour < 0 or start_hour > 23:
        raise ValueError("start_hour must be an integer between 0 and 23.")
    if duration_hours != expected:
        label = {
            "SAC_HALL": "SAC Hall",
            "CLH": "CLH",
            "AUDITORIUM": "Auditorium",
        }[facility_type]
        raise ValueError(f"{label} bookings must be exactly {expected} hour(s).")
    end_hour = start_hour + duration_hours
    if end_hour > 24:
        raise ValueError("end_hour must be <= 24.")
    return start_hour, end_hour, duration_hours


def _error(message, status="error"):
    return {"status": status, "message": message}


def _log_history(cursor, entity_type, entity_id, action, user, old_data=None, new_data=None):
    cursor.execute(
        """
        INSERT INTO booking_history (
            entity_type, entity_id, action,
            actor_name, actor_roll_number, actor_role,
            old_data, new_data
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
        """,
        (
            entity_type,
            entity_id,
            action,
            _name(user) or "unknown",
            _roll(user),
            _role(user) or "unknown",
            json.dumps(_jsonable(old_data)) if old_data is not None else None,
            json.dumps(_jsonable(new_data)) if new_data is not None else None,
        ),
    )


def _facility_row(cursor, facility):
    facility_type = _normalize_facility(facility)
    if not facility_type:
        return None
    cursor.execute(
        """
        SELECT facility_id, name, facility_type, active
        FROM facilities
        WHERE facility_type = %s
        """,
        (facility_type,),
    )
    return cursor.fetchone()


def _available_rooms(
    cursor,
    facility_type,
    *,
    room_code=None,
    room_type=None,
    booking_date=None,
    start_hour=None,
    end_hour=None,
    check_in=None,
    check_out=None,
    exclude_booking_id=None,
):
    params = [facility_type]
    filters = [
        "f.facility_type = %s",
        "r.active = TRUE",
        "f.active = TRUE",
    ]
    if room_code:
        filters.append("r.room_code = %s")
        params.append(room_code)
    if room_type:
        filters.append("r.room_type = %s")
        params.append(room_type)

    if booking_date is not None:
        overlap = """
            NOT EXISTS (
                SELECT 1 FROM bookings b
                WHERE b.room_id = r.room_id
                  AND b.status = 'CONFIRMED'
                  AND b.booking_date = %s
                  AND b.start_hour < %s
                  AND b.end_hour > %s
                  AND (%s::bigint IS NULL OR b.booking_id <> %s::bigint)
            )
        """
        filters.append(overlap)
        params.extend([booking_date, end_hour, start_hour, exclude_booking_id, exclude_booking_id])
    else:
        overlap = """
            NOT EXISTS (
                SELECT 1 FROM bookings b
                WHERE b.room_id = r.room_id
                  AND b.status = 'CONFIRMED'
                  AND b.check_in < %s
                  AND b.check_out > %s
                  AND (%s::bigint IS NULL OR b.booking_id <> %s::bigint)
            )
        """
        filters.append(overlap)
        params.extend([check_out, check_in, exclude_booking_id, exclude_booking_id])

    cursor.execute(
        f"""
        SELECT r.room_id, r.room_code, r.room_type, r.price_per_day,
               f.name AS facility_name, f.facility_type
        FROM rooms r
        JOIN facilities f ON f.facility_id = r.facility_id
        WHERE {" AND ".join(filters)}
        ORDER BY r.room_code
        """,
        params,
    )
    return [_row_dict(row) for row in cursor.fetchall()]


def _lookup_room(cursor, facility_type, room_code):
    cursor.execute(
        """
        SELECT r.room_id, r.room_code, r.room_type, r.price_per_day,
               f.name AS facility_name, f.facility_type
        FROM rooms r
        JOIN facilities f ON f.facility_id = r.facility_id
        WHERE f.facility_type = %s
          AND r.room_code = %s
          AND r.active = TRUE
        """,
        (facility_type, room_code),
    )
    return _row_dict(cursor.fetchone())


def _booking_select():
    return """
        SELECT b.booking_id, b.room_id, b.booker_name, b.booker_roll_number,
               b.booker_role, b.purpose, b.booking_date, b.start_hour, b.end_hour,
               b.check_in, b.check_out, b.status, b.created_at, b.updated_at,
               r.room_code, r.room_type, r.price_per_day,
               f.name AS facility_name, f.facility_type
        FROM bookings b
        JOIN rooms r ON r.room_id = b.room_id
        JOIN facilities f ON f.facility_id = r.facility_id
    """


def _request_select():
    return """
        SELECT req.request_id, req.room_id, req.requester_name, req.requester_roll_number,
               req.requester_role, req.purpose, req.booking_date, req.start_hour, req.end_hour,
               req.check_in, req.check_out, req.status, req.created_at, req.updated_at,
               req.decided_at, req.decided_by_name, req.decided_by_role,
               r.room_code, r.room_type, r.price_per_day,
               f.name AS facility_name, f.facility_type
        FROM requests req
        JOIN rooms r ON r.room_id = req.room_id
        JOIN facilities f ON f.facility_id = r.facility_id
    """


def _pick_room(cursor, facility_type, room_code, room_type, **availability):
    if room_code:
        room = _lookup_room(cursor, facility_type, room_code)
        if not room:
            return None, _error(f"No room found with code {room_code}.", "not_found")
        available = _available_rooms(
            cursor,
            facility_type,
            room_code=room_code,
            room_type=room_type,
            **availability,
        )
        if not available:
            return None, _error("That room is not available for the requested time.")
        return available[0], None

    available = _available_rooms(
        cursor,
        facility_type,
        room_type=room_type,
        **availability,
    )
    if not available:
        return None, _error("No room is available for the requested time.")
    return available[0], None


def _fetch_booking(cursor, booking_id):
    cursor.execute(_booking_select() + " WHERE b.booking_id = %s", (booking_id,))
    return _row_dict(cursor.fetchone())


def _fetch_request(cursor, request_id):
    cursor.execute(_request_select() + " WHERE req.request_id = %s", (request_id,))
    return _row_dict(cursor.fetchone())


def list_facilities():
    with _cursor() as (_conn, cursor):
        cursor.execute(
            """
            SELECT f.facility_id, f.name, f.facility_type, f.active,
                   COUNT(r.room_id) FILTER (WHERE r.active) AS room_count
            FROM facilities f
            LEFT JOIN rooms r ON r.facility_id = f.facility_id
            GROUP BY f.facility_id
            ORDER BY f.facility_id
            """
        )
        facilities = []
        for row in cursor.fetchall():
            item = _row_dict(row)
            cursor.execute(
                """
                SELECT room_type, COUNT(*) AS count, MIN(price_per_day) AS price_per_day
                FROM rooms
                WHERE facility_id = %s AND active = TRUE
                GROUP BY room_type
                ORDER BY room_type
                """,
                (item["facility_id"],),
            )
            item["rooms"] = [_row_dict(r) for r in cursor.fetchall()]
            facilities.append(item)
        return {"status": "success", "facilities": facilities}


def check_availability(
    facility,
    booking_date=None,
    start_hour=None,
    duration_hours=None,
    check_in=None,
    check_out=None,
    room_type=None,
):
    try:
        booking_date = _as_date(booking_date, "booking_date")
        check_in = _as_date(check_in, "check_in")
        check_out = _as_date(check_out, "check_out")
        room_type = _normalize_room_type(room_type)
    except ValueError as exc:
        return _error(str(exc))

    with _cursor() as (_conn, cursor):
        facility_row = _facility_row(cursor, facility)
        if not facility_row:
            return _error("Unknown facility.")
        facility_type = str(facility_row["facility_type"])

        try:
            if facility_type == "GUEST_HOUSE":
                if not check_in or not check_out:
                    return _error("Guest House requires check_in and check_out.")
                if check_in >= check_out:
                    return _error("check_in must be before check_out.")
                rooms = _available_rooms(
                    cursor,
                    facility_type,
                    room_type=room_type,
                    check_in=check_in,
                    check_out=check_out,
                )
            else:
                if not booking_date:
                    return _error("booking_date is required for this facility.")
                start_hour, end_hour, duration_hours = _hourly_window(
                    facility_type, start_hour, duration_hours
                )
                rooms = _available_rooms(
                    cursor,
                    facility_type,
                    booking_date=booking_date,
                    start_hour=start_hour,
                    end_hour=end_hour,
                )
        except ValueError as exc:
            return _error(str(exc))

        return {
            "status": "success",
            "facility": facility_row["name"],
            "facility_type": facility_type,
            "available_count": len(rooms),
            "rooms": rooms,
        }


def create_direct_booking(
    facility,
    user,
    purpose=None,
    room_code=None,
    booking_date=None,
    start_hour=None,
    duration_hours=None,
    check_in=None,
    check_out=None,
    guest_name=None,
    room_type=None,
):
    role = _role(user)
    if not role:
        return NOT_IN_AUTHORITY

    facility_type = _normalize_facility(facility)
    if not facility_type:
        return _error("Unknown facility.")
    if role not in DIRECT_ROLES.get(facility_type, set()):
        return NOT_IN_AUTHORITY

    purpose = (purpose or "").strip() or None
    if facility_type == "SAC_HALL" and not purpose:
        return _error("SAC Hall bookings require a purpose.")

    try:
        booking_date = _as_date(booking_date, "booking_date")
        check_in = _as_date(check_in, "check_in")
        check_out = _as_date(check_out, "check_out")
        room_type = _normalize_room_type(room_type)
        room_code = (room_code or "").strip() or None
        guest_name = (guest_name or "").strip() or None
    except ValueError as exc:
        return _error(str(exc))

    start = end = None
    try:
        if facility_type == "GUEST_HOUSE":
            if not check_in or not check_out:
                return _error("Guest House requires check_in and check_out.")
            if check_in >= check_out:
                return _error("check_in must be before check_out.")
            booking_date = None
        else:
            if not booking_date:
                return _error("booking_date is required for this facility.")
            start, end, duration_hours = _hourly_window(
                facility_type, start_hour, duration_hours
            )
            check_in = check_out = None
    except ValueError as exc:
        return _error(str(exc))

    booker = dict(user or {})
    if guest_name and not _name(booker):
        booker["name"] = guest_name

    try:
        with _cursor(commit=True) as (connection, cursor):
            room, err = _pick_room(
                cursor,
                facility_type,
                room_code,
                room_type,
                booking_date=booking_date,
                start_hour=start,
                end_hour=end,
                check_in=check_in,
                check_out=check_out,
            )
            if err:
                connection.rollback()
                return err

            cursor.execute(
                """
                INSERT INTO bookings (
                    room_id, booker_name, booker_roll_number, booker_role, purpose,
                    booking_date, start_hour, end_hour, check_in, check_out, status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'CONFIRMED')
                RETURNING booking_id
                """,
                (
                    room["room_id"],
                    _name(booker) or guest_name or "unknown",
                    _roll(booker),
                    role,
                    purpose,
                    booking_date,
                    start,
                    end,
                    check_in,
                    check_out,
                ),
            )
            booking_id = cursor.fetchone()["booking_id"]
            booking = _fetch_booking(cursor, booking_id)
            _log_history(cursor, "BOOKING", booking_id, "CREATED", user, None, booking)
            return {"status": "success", "booking": booking}
    except ExclusionViolation:
        return _error("That slot is no longer available.")


def create_request(
    facility,
    user,
    purpose=None,
    room_code=None,
    booking_date=None,
    start_hour=None,
    duration_hours=None,
):
    role = _role(user)
    if not role:
        return NOT_IN_AUTHORITY

    facility_type = _normalize_facility(facility)
    if not facility_type:
        return _error("Unknown facility.")
    if role not in REQUEST_ROLES.get(facility_type, set()):
        return NOT_IN_AUTHORITY

    purpose = (purpose or "").strip() or None
    room_code = (room_code or "").strip() or None

    try:
        booking_date = _as_date(booking_date, "booking_date")
        if not booking_date:
            return _error("booking_date is required for this facility.")
        start, end, duration_hours = _hourly_window(
            facility_type, start_hour, duration_hours
        )
    except ValueError as exc:
        return _error(str(exc))

    with _cursor(commit=True) as (connection, cursor):
        if room_code:
            room = _lookup_room(cursor, facility_type, room_code)
            if not room:
                connection.rollback()
                return _error(f"No room found with code {room_code}.", "not_found")
        else:
            available = _available_rooms(
                cursor,
                facility_type,
                booking_date=booking_date,
                start_hour=start,
                end_hour=end,
            )
            if available:
                room = available[0]
            else:
                cursor.execute(
                    """
                    SELECT r.room_id, r.room_code, r.room_type, r.price_per_day,
                           f.name AS facility_name, f.facility_type
                    FROM rooms r
                    JOIN facilities f ON f.facility_id = r.facility_id
                    WHERE f.facility_type = %s AND r.active = TRUE
                    ORDER BY r.room_code
                    LIMIT 1
                    """,
                    (facility_type,),
                )
                room = _row_dict(cursor.fetchone())
                if not room:
                    connection.rollback()
                    return _error("No room found for this facility.", "not_found")

        cursor.execute(
            """
            INSERT INTO requests (
                room_id, requester_name, requester_roll_number, requester_role,
                purpose, booking_date, start_hour, end_hour, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'PENDING')
            RETURNING request_id
            """,
            (
                room["room_id"],
                _name(user) or "unknown",
                _roll(user),
                role,
                purpose,
                booking_date,
                start,
                end,
            ),
        )
        request_id = cursor.fetchone()["request_id"]
        request = _fetch_request(cursor, request_id)
        _log_history(cursor, "REQUEST", request_id, "CREATED", user, None, request)
        return {"status": "success", "request": request}


def list_my_bookings(u, include_cancelled=False):
    clause, params = _mine_filter(u, "b.booker_name", "b.booker_roll_number")
    sql = _booking_select() + " WHERE " + clause
    if not include_cancelled:
        sql += " AND b.status = 'CONFIRMED'"
    sql += " ORDER BY b.created_at DESC"
    with _cursor() as (_conn, cursor):
        cursor.execute(sql, params)
        return {
            "status": "success",
            "bookings": [_row_dict(row) for row in cursor.fetchall()],
        }


def list_my_requests(u, include_closed=False):
    clause, params = _mine_filter(u, "req.requester_name", "req.requester_roll_number")
    sql = _request_select() + " WHERE " + clause
    if not include_closed:
        sql += " AND req.status = 'PENDING'"
    sql += " ORDER BY req.created_at DESC"
    with _cursor() as (_conn, cursor):
        cursor.execute(sql, params)
        return {
            "status": "success",
            "requests": [_row_dict(row) for row in cursor.fetchall()],
        }


def get_booking(booking_id, u):
    try:
        booking_id = _as_int(booking_id, "booking_id", allow_none=False)
    except ValueError as exc:
        return _error(str(exc))
    with _cursor() as (_conn, cursor):
        booking = _fetch_booking(cursor, booking_id)
        if not booking:
            return _error("Booking not found.", "not_found")
        if not _owns(u, booking["booker_name"], booking["booker_roll_number"]):
            return NOT_IN_AUTHORITY
        return {"status": "success", "booking": booking}


def get_request(request_id, u):
    try:
        request_id = _as_int(request_id, "request_id", allow_none=False)
    except ValueError as exc:
        return _error(str(exc))
    with _cursor() as (_conn, cursor):
        request = _fetch_request(cursor, request_id)
        if not request:
            return _error("Request not found.", "not_found")
        if not _owns(u, request["requester_name"], request["requester_roll_number"]):
            return NOT_IN_AUTHORITY
        return {"status": "success", "request": request}


def cancel_booking(booking_id, u):
    try:
        booking_id = _as_int(booking_id, "booking_id", allow_none=False)
    except ValueError as exc:
        return _error(str(exc))
    with _cursor(commit=True) as (connection, cursor):
        booking = _fetch_booking(cursor, booking_id)
        if not booking:
            connection.rollback()
            return _error("Booking not found.", "not_found")
        if not _owns(u, booking["booker_name"], booking["booker_roll_number"]):
            connection.rollback()
            return NOT_IN_AUTHORITY
        if booking["status"] != "CONFIRMED":
            connection.rollback()
            return _error("Only confirmed bookings can be cancelled.")
        cursor.execute(
            "UPDATE bookings SET status = 'CANCELLED' WHERE booking_id = %s",
            (booking_id,),
        )
        updated = _fetch_booking(cursor, booking_id)
        _log_history(cursor, "BOOKING", booking_id, "CANCELLED", u, booking, updated)
        return {"status": "success", "booking": updated}


def cancel_request(request_id, u):
    try:
        request_id = _as_int(request_id, "request_id", allow_none=False)
    except ValueError as exc:
        return _error(str(exc))
    with _cursor(commit=True) as (connection, cursor):
        request = _fetch_request(cursor, request_id)
        if not request:
            connection.rollback()
            return _error("Request not found.", "not_found")
        if not _owns(u, request["requester_name"], request["requester_roll_number"]):
            connection.rollback()
            return NOT_IN_AUTHORITY
        if request["status"] != "PENDING":
            connection.rollback()
            return _error("Only pending requests can be cancelled.")
        cursor.execute(
            "UPDATE requests SET status = 'CANCELLED' WHERE request_id = %s",
            (request_id,),
        )
        updated = _fetch_request(cursor, request_id)
        _log_history(cursor, "REQUEST", request_id, "CANCELLED", u, request, updated)
        return {"status": "success", "request": updated}


def modify_booking(
    booking_id,
    user,
    booking_date=None,
    start_hour=None,
    check_in=None,
    check_out=None,
    room_code=None,
):
    try:
        booking_id = _as_int(booking_id, "booking_id", allow_none=False)
        booking_date = _as_date(booking_date, "booking_date")
        check_in = _as_date(check_in, "check_in")
        check_out = _as_date(check_out, "check_out")
        room_code = (room_code or "").strip() or None
        start_hour = _as_int(start_hour, "start_hour")
    except ValueError as exc:
        return _error(str(exc))

    try:
        with _cursor(commit=True) as (connection, cursor):
            booking = _fetch_booking(cursor, booking_id)
            if not booking:
                connection.rollback()
                return _error("Booking not found.", "not_found")
            if not _owns(user, booking["booker_name"], booking["booker_roll_number"]):
                connection.rollback()
                return NOT_IN_AUTHORITY
            if booking["status"] != "CONFIRMED":
                connection.rollback()
                return _error("Only confirmed bookings can be modified.")

            facility_type = str(booking["facility_type"])
            new_room_code = room_code or booking["room_code"]

            if facility_type == "GUEST_HOUSE":
                old_in = date.fromisoformat(str(booking["check_in"]))
                old_out = date.fromisoformat(str(booking["check_out"]))
                nights = old_out - old_in
                new_in = check_in or old_in
                if check_in and check_out:
                    if (check_out - check_in) != nights:
                        connection.rollback()
                        return _error("modify_booking cannot change duration.")
                    new_out = check_out
                else:
                    new_out = new_in + nights
                if new_in >= new_out:
                    connection.rollback()
                    return _error("check_in must be before check_out.")
                room, err = _pick_room(
                    cursor,
                    facility_type,
                    new_room_code,
                    booking.get("room_type"),
                    check_in=new_in,
                    check_out=new_out,
                    exclude_booking_id=booking_id,
                )
                if err:
                    connection.rollback()
                    return err
                cursor.execute(
                    """
                    UPDATE bookings
                    SET room_id = %s, check_in = %s, check_out = %s
                    WHERE booking_id = %s
                    """,
                    (room["room_id"], new_in, new_out, booking_id),
                )
            else:
                duration = int(booking["end_hour"]) - int(booking["start_hour"])
                new_date = booking_date or date.fromisoformat(str(booking["booking_date"]))
                new_start = start_hour if start_hour is not None else int(booking["start_hour"])
                if new_start < 0 or new_start > 23:
                    connection.rollback()
                    return _error("start_hour must be an integer between 0 and 23.")
                new_end = new_start + duration
                if new_end > 24:
                    connection.rollback()
                    return _error("end_hour must be <= 24.")
                room, err = _pick_room(
                    cursor,
                    facility_type,
                    new_room_code,
                    None,
                    booking_date=new_date,
                    start_hour=new_start,
                    end_hour=new_end,
                    exclude_booking_id=booking_id,
                )
                if err:
                    connection.rollback()
                    return err
                cursor.execute(
                    """
                    UPDATE bookings
                    SET room_id = %s, booking_date = %s, start_hour = %s, end_hour = %s
                    WHERE booking_id = %s
                    """,
                    (room["room_id"], new_date, new_start, new_end, booking_id),
                )

            updated = _fetch_booking(cursor, booking_id)
            _log_history(cursor, "BOOKING", booking_id, "MODIFIED", user, booking, updated)
            return {"status": "success", "booking": updated}
    except ExclusionViolation:
        return _error("That slot is no longer available.")


def modify_request(
    request_id,
    user,
    booking_date=None,
    start_hour=None,
    room_code=None,
):
    try:
        request_id = _as_int(request_id, "request_id", allow_none=False)
        booking_date = _as_date(booking_date, "booking_date")
        start_hour = _as_int(start_hour, "start_hour")
        room_code = (room_code or "").strip() or None
    except ValueError as exc:
        return _error(str(exc))

    with _cursor(commit=True) as (connection, cursor):
        request = _fetch_request(cursor, request_id)
        if not request:
            connection.rollback()
            return _error("Request not found.", "not_found")
        if not _owns(user, request["requester_name"], request["requester_roll_number"]):
            connection.rollback()
            return NOT_IN_AUTHORITY
        if request["status"] != "PENDING":
            connection.rollback()
            return _error("Only pending requests can be modified.")

        facility_type = str(request["facility_type"])
        duration = int(request["end_hour"]) - int(request["start_hour"])
        new_date = booking_date or date.fromisoformat(str(request["booking_date"]))
        new_start = start_hour if start_hour is not None else int(request["start_hour"])
        if new_start < 0 or new_start > 23:
            connection.rollback()
            return _error("start_hour must be an integer between 0 and 23.")
        new_end = new_start + duration
        if new_end > 24:
            connection.rollback()
            return _error("end_hour must be <= 24.")

        new_room_code = room_code or request["room_code"]
        room = _lookup_room(cursor, facility_type, new_room_code)
        if not room:
            connection.rollback()
            return _error(f"No room found with code {new_room_code}.", "not_found")

        cursor.execute(
            """
            UPDATE requests
            SET room_id = %s, booking_date = %s, start_hour = %s, end_hour = %s
            WHERE request_id = %s
            """,
            (room["room_id"], new_date, new_start, new_end, request_id),
        )
        updated = _fetch_request(cursor, request_id)
        _log_history(cursor, "REQUEST", request_id, "MODIFIED", user, request, updated)
        return {"status": "success", "request": updated}


def list_all_pending_requests(u):
    if not _is_admin(u):
        return NOT_IN_AUTHORITY
    with _cursor() as (_conn, cursor):
        cursor.execute(
            _request_select() + " WHERE req.status = 'PENDING' ORDER BY req.created_at"
        )
        return {
            "status": "success",
            "requests": [_row_dict(row) for row in cursor.fetchall()],
        }


def approve_request(request_id, u):
    if not _is_admin(u):
        return NOT_IN_AUTHORITY
    try:
        request_id = _as_int(request_id, "request_id", allow_none=False)
    except ValueError as exc:
        return _error(str(exc))

    try:
        with _cursor(commit=True) as (connection, cursor):
            cursor.execute(
                _request_select() + " WHERE req.request_id = %s FOR UPDATE OF req",
                (request_id,),
            )
            request = _row_dict(cursor.fetchone())
            if not request:
                connection.rollback()
                return _error("Request not found.", "not_found")
            if request["status"] != "PENDING":
                connection.rollback()
                return _error("Only pending requests can be approved.")

            facility_type = str(request["facility_type"])
            booking_date = date.fromisoformat(str(request["booking_date"]))
            start_hour = int(request["start_hour"])
            end_hour = int(request["end_hour"])

            room, err = _pick_room(
                cursor,
                facility_type,
                request["room_code"],
                None,
                booking_date=booking_date,
                start_hour=start_hour,
                end_hour=end_hour,
            )
            if err:
                # Specified room taken: try any available room in the facility.
                fallback, fallback_err = _pick_room(
                    cursor,
                    facility_type,
                    None,
                    None,
                    booking_date=booking_date,
                    start_hour=start_hour,
                    end_hour=end_hour,
                )
                if fallback_err:
                    connection.rollback()
                    return fallback_err
                room = fallback

            requester = {
                "role": request["requester_role"],
                "name": request["requester_name"],
                "roll_number": request["requester_roll_number"],
            }
            cursor.execute(
                """
                INSERT INTO bookings (
                    room_id, booker_name, booker_roll_number, booker_role, purpose,
                    booking_date, start_hour, end_hour, status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'CONFIRMED')
                RETURNING booking_id
                """,
                (
                    room["room_id"],
                    requester["name"],
                    requester["roll_number"],
                    requester["role"],
                    request.get("purpose"),
                    booking_date,
                    start_hour,
                    end_hour,
                ),
            )
            booking_id = cursor.fetchone()["booking_id"]
            cursor.execute(
                """
                UPDATE requests
                SET status = 'APPROVED',
                    decided_at = NOW(),
                    decided_by_name = %s,
                    decided_by_role = %s,
                    room_id = %s
                WHERE request_id = %s
                """,
                (_name(u), _role(u), room["room_id"], request_id),
            )
            booking = _fetch_booking(cursor, booking_id)
            updated = _fetch_request(cursor, request_id)
            _log_history(cursor, "REQUEST", request_id, "APPROVED", u, request, updated)
            _log_history(cursor, "BOOKING", booking_id, "CREATED", u, None, booking)
            return {"status": "success", "request": updated, "booking": booking}
    except ExclusionViolation:
        return _error("That slot is no longer available.")


def reject_request(request_id, u, reason=None):
    if not _is_admin(u):
        return NOT_IN_AUTHORITY
    try:
        request_id = _as_int(request_id, "request_id", allow_none=False)
    except ValueError as exc:
        return _error(str(exc))
    reason = (reason or "").strip() or None

    with _cursor(commit=True) as (connection, cursor):
        request = _fetch_request(cursor, request_id)
        if not request:
            connection.rollback()
            return _error("Request not found.", "not_found")
        if request["status"] != "PENDING":
            connection.rollback()
            return _error("Only pending requests can be rejected.")
        cursor.execute(
            """
            UPDATE requests
            SET status = 'REJECTED',
                decided_at = NOW(),
                decided_by_name = %s,
                decided_by_role = %s
            WHERE request_id = %s
            """,
            (_name(u), _role(u), request_id),
        )
        updated = _fetch_request(cursor, request_id)
        history_new = dict(updated)
        if reason:
            history_new["reason"] = reason
        _log_history(cursor, "REQUEST", request_id, "REJECTED", u, request, history_new)
        result = {"status": "success", "request": updated}
        if reason:
            result["reason"] = reason
        return result
