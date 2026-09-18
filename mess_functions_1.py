import db
from config import MESS_DB_NAME
from ttl_cache import TtlCache


def get_connection():
    # Pooled connection when psycopg_pool is installed; falls back to a
    # plain per-call connection (pg8000 first, then psycopg) otherwise.
    # PGHOST/PGPORT/PGUSER/PGPASSWORD env overrides are handled inside db.py.
    return db.get_connection(MESS_DB_NAME)


_menu_cache = TtlCache("mess_menu", ttl_seconds=60)
_timing_cache = TtlCache("mess_menu", ttl_seconds=None)


def _invalidate_menu_cache(hostel: str | None = None, menu_date: str | None = None):
    if hostel and menu_date:
        host = hostel.strip().lower()
        _menu_cache.pop(f"menu:{host}:{menu_date}")
        _menu_cache.invalidate_prefix(f"weekly:{host}:")
        return
    _menu_cache.clear()


def _get_menu_uncached(hostel: str, target_date):
    conn = get_connection()
    try:
        cur = conn.cursor()
        day_name = target_date.strftime("%A")
        cur.execute(
            """
            SELECT breakfast, lunch, snacks, dinner
            FROM temporary
            WHERE LOWER(hostel) = LOWER(%s)
              AND LOWER(day) = LOWER(%s)
            """,
            (hostel, day_name)
        )
        row = cur.fetchone()
        cur.close()
        conn.commit()

        if not row:
            return {
                "status": "not_found",
                "message": f"No menu found for {hostel} on {target_date.isoformat()} ({day_name})."
            }

        menu = {"breakfast": row[0], "lunch": row[1], "snacks": row[2], "dinner": row[3], "dessert": None}

        return {
            "status": "success",
            "hostel": hostel,
            "date": target_date.isoformat(),
            "day": day_name,
            "menu": menu
        }
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def get_menu(hostel: str, menu_date: str):
    """Get menu for a specific hostel and date.
    menu_date: 'today', 'tomorrow', or 'YYYY-MM-DD'."""
    from datetime import date, timedelta
    raw = menu_date.strip().lower()
    if raw == "today":
        target_date = date.today()
    elif raw == "tomorrow":
        target_date = date.today() + timedelta(days=1)
    else:
        try:
            target_date = date.fromisoformat(raw)
        except ValueError:
            return {
                "status": "error",
                "message": f"Invalid date '{menu_date}'. Use 'today', 'tomorrow', or YYYY-MM-DD."
            }
    key = f"menu:{hostel.strip().lower()}:{target_date.isoformat()}"
    return _menu_cache.get(key, lambda: _get_menu_uncached(hostel, target_date))


def get_weekly_menu(hostel: str, start_date: str = None):
    """Get weekly menu for a hostel starting from start_date (default: today)."""
    from datetime import date, timedelta
    if start_date:
        start_date = start_date.strip().lower()
        if start_date == "today":
            start = date.today()
        elif start_date == "tomorrow":
            start = date.today() + timedelta(days=1)
        else:
            try:
                start = date.fromisoformat(start_date)
            except ValueError:
                return {"status": "error", "message": f"Invalid start_date '{start_date}'."}
    else:
        start = date.today()

    key = f"weekly:{hostel.strip().lower()}:{start.isoformat()}"

    def _compute():
        day_names = [(start + timedelta(days=i)).strftime("%A") for i in range(7)]
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT day, breakfast, lunch, snacks, dinner
            FROM temporary
            WHERE LOWER(hostel) = LOWER(%s)
              AND LOWER(day) = ANY(%s)
            """,
            (hostel, [d.lower() for d in day_names])
        )
        rows_by_day = {row[0].strip().lower(): row for row in cur.fetchall()}
        cur.close()
        conn.close()

        week = []
        for i, day_name in enumerate(day_names):
            d = start + timedelta(days=i)
            row = rows_by_day.get(day_name.lower())
            if row:
                day_menu = {"day": day_name, "date": d.isoformat(),
                            "breakfast": row[1], "lunch": row[2], "snacks": row[3], "dinner": row[4], "dessert": None}
            else:
                day_menu = {"day": day_name, "date": d.isoformat(),
                            "breakfast": "—", "lunch": "—", "snacks": "—", "dinner": "—", "dessert": None}
            week.append(day_menu)

        if all(m["breakfast"] == "—" for m in week):
            return {"status": "not_found", "message": f"No weekly menu found for {hostel}."}

        return {"status": "success", "hostel": hostel, "week_menu": week}

    return _menu_cache.get(key, _compute)


def get_meal_timing(meal: str):
    """Get fixed meal timings (static, not in DB)."""
    meal_key = meal.strip().lower()
    return _timing_cache.get(f"timing:{meal_key}", lambda: _get_meal_timing_uncached(meal_key))


def _get_meal_timing_uncached(meal: str):
    timings = {
        "breakfast": "07:30 - 09:30",
        "lunch": "12:30 - 14:30",
        "snacks": "17:00 - 18:00",
        "dinner": "20:00 - 22:00"
    }
    if meal not in timings:
        return {"status": "error", "message": f"Unknown meal: {meal}."}
    return {"status": "success", "meal": meal, "timing": timings[meal]}


def modify_menu(hostel: str, menu_date: str, meal: str, new_items: str, change_type: str, user_role: str):
    """Modify menu for a hostel/date/meal. Only Admin can do permanent; Faculty temporary."""
    from datetime import date, timedelta
    if user_role.lower() == "student":
        return {"status": "forbidden", "message": "Not in your authority."}
    if user_role.lower() == "faculty" and change_type.lower() == "permanent":
        return {"status": "forbidden", "message": "Not in your authority."}

    meal = meal.strip().lower()
    # Explicit allow-list mapping (not just a membership check) so the value
    # interpolated into the SQL below can only ever be one of these four
    # literal column names, never anything derived from user input.
    valid_meal_columns = {
        "breakfast": "breakfast",
        "lunch": "lunch",
        "snacks": "snacks",
        "dinner": "dinner",
    }
    if meal not in valid_meal_columns:
        return {"status": "error", "message": f"Invalid meal: {meal}."}
    meal_column = valid_meal_columns[meal]

    if change_type.lower() not in ("temporary", "permanent"):
        return {"status": "error", "message": "change_type must be 'temporary' or 'permanent'."}

    menu_date = menu_date.strip().lower()
    if menu_date == "today":
        d = date.today()
    elif menu_date == "tomorrow":
        d = date.today() + timedelta(days=1)
    else:
        try:
            d = date.fromisoformat(menu_date)
        except ValueError:
            return {"status": "error", "message": f"Invalid date '{menu_date}'."}

    conn = get_connection()
    cur = conn.cursor()
    # sync to actual tables: temporary and permanent (hostel/day schema, column per meal)
    table = "temporary" if change_type.lower() == "temporary" else "permanent"
    day_name = d.strftime("%A")
    # validated meal is a column name, safe to interpolate after validation
    try:
        cur.execute(
            f"""
            UPDATE {table}
            SET {meal_column} = %s
            WHERE LOWER(hostel) = LOWER(%s)
              AND LOWER(day) = LOWER(%s)
            """,
            (new_items, hostel, day_name)
        )
        if cur.rowcount == 0:
            return {"status": "not_found", "message": f"No menu row for {hostel} on {d.isoformat()} ({day_name}) {meal}."}
        conn.commit()
        _invalidate_menu_cache(hostel, d.isoformat())
        return {
            "status": "success",
            "message": f"{change_type.capitalize()} menu updated for {hostel} {d.isoformat()} ({day_name}) {meal}.",
            "hostel": hostel,
            "date": d.isoformat(),
            "day": day_name,
            "meal": meal,
            "new_items": new_items,
            "change_type": change_type
        }
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": f"Update failed: {e}"}
    finally:
        cur.close()
        conn.close()


# print("\n==============================")
# print("TEST 1: GET TODAY'S MENU")
# print("==============================")

# result = get_menu("CV Raman", "today")
# print(result)


# print("\n==============================")
# print("TEST 2: GET TOMORROW'S MENU")
# print("==============================")

# result = get_menu("Aryabhatta", "tomorrow")
# print(result)


# print("\n==============================")
# print("TEST 3: GET MENU USING DATE")
# print("==============================")

# result = get_menu("Kalam", "2026-09-14")
# print(result)


# print("\n==============================")
# print("TEST 4: INVALID DATE")
# print("==============================")

# result = get_menu("Kalam", "wrong-date")
# print(result)


# print("\n==============================")
# print("TEST 5: WEEKLY MENU")
# print("==============================")

# result = get_weekly_menu("Kalam")
# print(result)


# print("\n==============================")
# print("TEST 6: BREAKFAST TIMING")
# print("==============================")

# result = get_meal_timing("breakfast")
# print(result)


# print("\n==============================")
# print("TEST 7: DINNER TIMING")
# print("==============================")

# result = get_meal_timing("dinner")
# print(result)


# print("\n==============================")
# print("TEST 8: INVALID MEAL")
# print("==============================")

# result = get_meal_timing("brunch")
# print(result)


# print("\n==============================")
# print("TEST 9: STUDENT MODIFY")
# print("==============================")

# result = modify_menu(
#     "Kalam",
#     "today",
#     "dinner",
#     "Roti, Dal, Paneer Curry",
#     "temporary",
#     "student"
# )
# print(result)


# print("\n==============================")
# print("TEST 10: FACULTY TEMPORARY MODIFY")
# print("==============================")

# result = modify_menu(
#     "Kalam",
#     "today",
#     "dinner",
#     "Roti, Dal, Paneer Curry",
#     "temporary",
#     "faculty"
# )
# print(result)


# print("\n==============================")
# print("TEST 11: FACULTY PERMANENT MODIFY")
# print("==============================")

# result = modify_menu(
#     "Kalam",
#     "today",
#     "dinner",
#     "Roti, Dal, Paneer Curry",
#     "permanent",
#     "faculty"
# )
# print(result)


# print("\n==============================")
# print("TEST 12: ADMIN PERMANENT MODIFY")
# print("==============================")

# result = modify_menu(
#     "Kalam",
#     "today",
#     "dinner",
#     "Roti, Dal, Paneer Curry",
#     "permanent",
#     "admin"
# )
# print(result)


# print("\n==============================")
# print("TEST 13: VERIFY TEMPORARY MENU")
# print("==============================")

# result = get_menu("Kalam", "today")
# print(result)