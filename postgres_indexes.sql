-- ------------------------------------------------------------------
-- Indexes identified during the architecture review (2026-09-15).
-- bus_schedule and the mess menu tables currently only have a primary
-- key, so every lookup by bus name / day / hostel / stop is a full
-- table scan. Run this once against each database after restoring
-- postgres_setup.sql.
-- ------------------------------------------------------------------

-- bus_schedule DB --------------------------------------------------
\connect bus_schedule

CREATE INDEX IF NOT EXISTS idx_bus_schedule_bus_name
    ON public.bus_schedule (bus_name);

CREATE INDEX IF NOT EXISTS idx_bus_schedule_day
    ON public.bus_schedule (day);

CREATE INDEX IF NOT EXISTS idx_bus_schedule_start_dest
    ON public.bus_schedule (start_point, destination);

-- Case-insensitive matching is used throughout bus_function.py
-- (bus name / stop resolution); a lower() functional index lets the
-- planner use an index scan instead of a sequential scan + filter.
CREATE INDEX IF NOT EXISTS idx_bus_schedule_bus_name_lower
    ON public.bus_schedule (LOWER(bus_name));

-- mess_menu DB -------------------------------------------------------
\connect mess_menu

CREATE INDEX IF NOT EXISTS idx_temporary_hostel_day
    ON public.temporary (LOWER(hostel), LOWER(day));

CREATE INDEX IF NOT EXISTS idx_permanent_hostel_day
    ON public.permanent (LOWER(hostel), LOWER(day));

-- room_booking DB ------------------------------------------------------
-- Indexes live in room_booking.sql (facilities / rooms / bookings /
-- requests). Do not recreate them here.

-- attendance DB (organization_agent) -----------------------------------
-- Indexes live in attendance.sql.
