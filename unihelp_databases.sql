-- unihelp_databases.sql
-- Combined schema + seed data for every UniHelp database and table.
-- Built from the per-database SQL files that already lived in this repo.
--
-- Databases / tables:
--   campus_agent.users
--   mess_menu.mess_feedback
--   mess_menu.permanent
--   mess_menu.temporary
--   bus_schedule.bus_schedule
--   room_booking.booking_history
--   room_booking.bookings
--   room_booking.facilities
--   room_booking.requests
--   room_booking.rooms
--   complaints.complaint_history
--   complaints.complaints
--   complaints.users
--   organization_agent.attendance
--   organization_agent.courses
--   organization_agent.enrollments
--   organization_agent.people
--   notice_board.notices
--   timetable.courses
--   timetable.people
--   timetable.rooms
--   timetable.timetable
--
-- Restore:
--   export PGHOST=localhost PGPORT=5434 PGUSER=postgres
--   psql -d postgres -f unihelp_databases.sql
--
-- Student roster (optional, after this file):
--   psql -d timetable -c "\\copy people(roll_num, name, role, student_group) FROM 'timetable_users.csv' DELIMITER ',' CSV HEADER"
--
-- Run with psql. Other clients will not honor \connect / \gexec.

\connect postgres

SELECT 'CREATE DATABASE campus_agent'         WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'campus_agent')\gexec
SELECT 'CREATE DATABASE mess_menu'            WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'mess_menu')\gexec
SELECT 'CREATE DATABASE bus_schedule'         WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'bus_schedule')\gexec
SELECT 'CREATE DATABASE room_booking'         WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'room_booking')\gexec
SELECT 'CREATE DATABASE complaints'           WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'complaints')\gexec
SELECT 'CREATE DATABASE organization_agent'   WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'organization_agent')\gexec
SELECT 'CREATE DATABASE notice_board'         WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'notice_board')\gexec
SELECT 'CREATE DATABASE timetable'            WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'timetable')\gexec


-- ============================================================
-- Database: campus_agent  (from campus_agent.sql)
-- ============================================================
\connect campus_agent

-- campus_agent.sql
-- Authentication database (AUTH_DB_NAME). The A2A entry point looks up
-- authentication_key here before any planning or tool calls.
--
-- roll_number is TEXT (IIT Patna-style, e.g. 2501CS09). It must match:
--   complaints.users.id / complaints.users.roll_number
--   organization_agent.people.roll_num
--
-- Run inside the dedicated `campus_agent` database.

BEGIN;

CREATE TABLE IF NOT EXISTS users (
    authentication_key VARCHAR PRIMARY KEY,
    role VARCHAR NOT NULL,
    names TEXT NOT NULL,
    roll_number TEXT UNIQUE NOT NULL,
    CONSTRAINT users_role_check
        CHECK (LOWER(role) IN ('student', 'faculty', 'admin'))
);

INSERT INTO users (authentication_key, role, names, roll_number) VALUES
    ('student-demo', 'student', 'Aarav Sharma', '2501CS09'),
    ('student-neha', 'student', 'Neha Gupta', '2501CS90'),
    ('student-kabir', 'student', 'Kabir Mehta', '2501CS91'),
    ('student-ananya', 'student', 'Ananya Iyer', '2501AI51'),
    ('student-vikram', 'student', 'Vikram Singh', '2501CS92'),
    ('faculty-demo', 'faculty', 'Priya Patel', 'PF001'),
    ('faculty-arjun', 'faculty', 'Arjun Nair', 'PF002'),
    ('faculty-meera', 'faculty', 'Meera Joshi', 'PF003'),
    ('faculty-sameer', 'faculty', 'Sameer Khan', 'PF004'),
    ('faculty-kavita', 'faculty', 'Kavita Desai', 'PF005'),
    ('faculty-aditi', 'faculty', 'Aditi Rao', 'PF006'),
    ('faculty-harsh', 'faculty', 'Harsh Vardhan', 'PF007'),
    ('faculty-leela', 'faculty', 'Leela Menon', 'PF008'),
    ('faculty-omar', 'faculty', 'Omar Qureshi', 'PF009'),
    ('faculty-tanvi', 'faculty', 'Tanvi Shah', 'PF010'),
    ('faculty-nikhil', 'faculty', 'Nikhil Rao', 'PF011'),
    ('faculty-pooja', 'faculty', 'Pooja Bhatt', 'PF012'),
    ('faculty-farhan', 'faculty', 'Farhan Ali', 'PF013'),
    ('faculty-diya', 'faculty', 'Diya Kulkarni', 'PF014'),
    ('faculty-yash', 'faculty', 'Yash Agarwal', 'PF015'),
    ('faculty-sana', 'faculty', 'Sana Iqbal', 'PF016'),
    ('admin-demo', 'admin', 'Rohan Verma', 'AD001'),
    ('admin-nisha', 'admin', 'Nisha Kapoor', 'AD002')
ON CONFLICT (authentication_key) DO UPDATE
SET role = EXCLUDED.role,
    names = EXCLUDED.names,
    roll_number = EXCLUDED.roll_number;

COMMIT;


-- ============================================================
-- Database: mess_menu  (from mess_menu.sql)
-- ============================================================
\connect mess_menu

-- mess_menu.sql
-- Hostel mess menus. Reads always hit `temporary`. Writes go to
-- `temporary` (faculty/admin) or `permanent` (admin only).
--
-- Run inside the dedicated `mess_menu` database.

BEGIN;

CREATE TABLE IF NOT EXISTS temporary (
    hostel TEXT NOT NULL,
    day TEXT NOT NULL,
    breakfast TEXT,
    lunch TEXT,
    snacks TEXT,
    dinner TEXT,
    PRIMARY KEY (hostel, day)
);

CREATE TABLE IF NOT EXISTS permanent (
    hostel TEXT NOT NULL,
    day TEXT NOT NULL,
    breakfast TEXT,
    lunch TEXT,
    snacks TEXT,
    dinner TEXT,
    PRIMARY KEY (hostel, day)
);

CREATE INDEX IF NOT EXISTS idx_temporary_hostel_day
    ON temporary (LOWER(hostel), LOWER(day));

CREATE INDEX IF NOT EXISTS idx_permanent_hostel_day
    ON permanent (LOWER(hostel), LOWER(day));

-- Sample weekly menus for the hostels the agent examples use.
INSERT INTO temporary (hostel, day, breakfast, lunch, snacks, dinner)
SELECT hostel, day, breakfast, lunch, snacks, dinner
FROM (
    VALUES
        ('Kalam', 'Monday',    'Poha, banana, tea',           'Rice, dal, mixed veg, roti',     'Samosa, tea',     'Roti, dal, paneer, rice'),
        ('Kalam', 'Tuesday',   'Idli, sambar, coffee',        'Jeera rice, chole, salad',       'Bhel, lemonade',  'Roti, palak paneer, rice'),
        ('Kalam', 'Wednesday', 'Paratha, curd, tea',          'Rice, sambar, cabbage, roti',    'Pakora, tea',     'Roti, egg curry, rice'),
        ('Kalam', 'Thursday',  'Upma, fruit, tea',            'Rice, rajma, beans, roti',       'Sandwich, juice', 'Roti, chicken curry, rice'),
        ('Kalam', 'Friday',    'Bread omelette, tea',         'Fried rice, dal tadka, roti',    'Vada, coffee',    'Roti, fish curry, rice'),
        ('Kalam', 'Saturday',  'Aloo paratha, pickle, tea',   'Rice, kadhi, aloo gobi, roti',   'Noodles, tea',    'Roti, mix veg, rice'),
        ('Kalam', 'Sunday',    'Chole bhature, tea',          'Veg biryani, raita, papad',      'Cake, coffee',    'Roti, malai kofta, rice'),

        ('Aryabhatta', 'Monday',    'Poha, banana, tea',           'Rice, dal, mixed veg, roti',     'Samosa, tea',     'Roti, dal, paneer, rice'),
        ('Aryabhatta', 'Tuesday',   'Idli, sambar, coffee',        'Jeera rice, chole, salad',       'Bhel, lemonade',  'Roti, palak paneer, rice'),
        ('Aryabhatta', 'Wednesday', 'Paratha, curd, tea',          'Rice, sambar, cabbage, roti',    'Pakora, tea',     'Roti, egg curry, rice'),
        ('Aryabhatta', 'Thursday',  'Upma, fruit, tea',            'Rice, rajma, beans, roti',       'Sandwich, juice', 'Roti, chicken curry, rice'),
        ('Aryabhatta', 'Friday',    'Bread omelette, tea',         'Fried rice, dal tadka, roti',    'Vada, coffee',    'Roti, fish curry, rice'),
        ('Aryabhatta', 'Saturday',  'Aloo paratha, pickle, tea',   'Rice, kadhi, aloo gobi, roti',   'Noodles, tea',    'Roti, mix veg, rice'),
        ('Aryabhatta', 'Sunday',    'Chole bhature, tea',          'Veg biryani, raita, papad',      'Cake, coffee',    'Roti, malai kofta, rice'),

        ('CV Raman', 'Monday',    'Poha, banana, tea',           'Rice, dal, mixed veg, roti',     'Samosa, tea',     'Roti, dal, paneer, rice'),
        ('CV Raman', 'Tuesday',   'Idli, sambar, coffee',        'Jeera rice, chole, salad',       'Bhel, lemonade',  'Roti, palak paneer, rice'),
        ('CV Raman', 'Wednesday', 'Paratha, curd, tea',          'Rice, sambar, cabbage, roti',    'Pakora, tea',     'Roti, egg curry, rice'),
        ('CV Raman', 'Thursday',  'Upma, fruit, tea',            'Rice, rajma, beans, roti',       'Sandwich, juice', 'Roti, chicken curry, rice'),
        ('CV Raman', 'Friday',    'Bread omelette, tea',         'Fried rice, dal tadka, roti',    'Vada, coffee',    'Roti, fish curry, rice'),
        ('CV Raman', 'Saturday',  'Aloo paratha, pickle, tea',   'Rice, kadhi, aloo gobi, roti',   'Noodles, tea',    'Roti, mix veg, rice'),
        ('CV Raman', 'Sunday',    'Chole bhature, tea',          'Veg biryani, raita, papad',      'Cake, coffee',    'Roti, malai kofta, rice'),

        ('Asima', 'Monday',    'Poha, banana, tea',           'Rice, dal, mixed veg, roti',     'Samosa, tea',     'Roti, dal, paneer, rice'),
        ('Asima', 'Tuesday',   'Idli, sambar, coffee',        'Jeera rice, chole, salad',       'Bhel, lemonade',  'Roti, palak paneer, rice'),
        ('Asima', 'Wednesday', 'Paratha, curd, tea',          'Rice, sambar, cabbage, roti',    'Pakora, tea',     'Roti, egg curry, rice'),
        ('Asima', 'Thursday',  'Upma, fruit, tea',            'Rice, rajma, beans, roti',       'Sandwich, juice', 'Roti, chicken curry, rice'),
        ('Asima', 'Friday',    'Bread omelette, tea',         'Fried rice, dal tadka, roti',    'Vada, coffee',    'Roti, fish curry, rice'),
        ('Asima', 'Saturday',  'Aloo paratha, pickle, tea',   'Rice, kadhi, aloo gobi, roti',   'Noodles, tea',    'Roti, mix veg, rice'),
        ('Asima', 'Sunday',    'Chole bhature, tea',          'Veg biryani, raita, papad',      'Cake, coffee',    'Roti, malai kofta, rice')
) AS seed(hostel, day, breakfast, lunch, snacks, dinner)
ON CONFLICT (hostel, day) DO NOTHING;

INSERT INTO permanent (hostel, day, breakfast, lunch, snacks, dinner)
SELECT hostel, day, breakfast, lunch, snacks, dinner
FROM temporary
ON CONFLICT (hostel, day) DO NOTHING;

COMMIT;


-- ============================================================
-- Database: bus_schedule  (from bus_schedule.sql)
-- ============================================================
\connect bus_schedule

-- bus_schedule.sql
-- Campus shuttle timetable used by bus_function.py.
--
-- Run inside the dedicated `bus_schedule` database.

BEGIN;

CREATE TABLE IF NOT EXISTS bus_schedule (
    id SERIAL PRIMARY KEY,
    day TEXT NOT NULL,
    time TIME NOT NULL,
    bus_name TEXT NOT NULL,
    start_point TEXT NOT NULL,
    destination TEXT NOT NULL,
    driver_name TEXT,
    driver_no TEXT
);

CREATE INDEX IF NOT EXISTS idx_bus_schedule_bus_name
    ON bus_schedule (bus_name);
CREATE INDEX IF NOT EXISTS idx_bus_schedule_day
    ON bus_schedule (day);
CREATE INDEX IF NOT EXISTS idx_bus_schedule_start_dest
    ON bus_schedule (start_point, destination);
CREATE INDEX IF NOT EXISTS idx_bus_schedule_bus_name_lower
    ON bus_schedule (LOWER(bus_name));

INSERT INTO bus_schedule
    (day, time, bus_name, start_point, destination, driver_name, driver_no)
VALUES
    ('Monday',    '08:00', 'Bus 02', 'Aryabhatta', 'Tut Block',  'Ramesh Kumar', '9876500002'),
    ('Monday',    '08:15', 'Bus 02', 'Kalam',      'Tut Block',  'Ramesh Kumar', '9876500002'),
    ('Monday',    '17:30', 'Bus 02', 'Tut Block',  'Kalam',      'Ramesh Kumar', '9876500002'),
    ('Monday',    '17:45', 'Bus 02', 'Tut Block',  'Aryabhatta', 'Ramesh Kumar', '9876500002'),
    ('Tuesday',   '08:00', 'Bus 02', 'Aryabhatta', 'Tut Block',  'Ramesh Kumar', '9876500002'),
    ('Tuesday',   '08:15', 'Bus 02', 'Kalam',      'Tut Block',  'Ramesh Kumar', '9876500002'),
    ('Tuesday',   '17:30', 'Bus 02', 'Tut Block',  'Kalam',      'Ramesh Kumar', '9876500002'),
    ('Wednesday', '08:00', 'Bus 02', 'Aryabhatta', 'Tut Block',  'Ramesh Kumar', '9876500002'),
    ('Wednesday', '08:15', 'Bus 02', 'Kalam',      'Tut Block',  'Ramesh Kumar', '9876500002'),
    ('Wednesday', '17:30', 'Bus 02', 'Tut Block',  'Kalam',      'Ramesh Kumar', '9876500002'),
    ('Thursday',  '08:00', 'Bus 02', 'Aryabhatta', 'Tut Block',  'Ramesh Kumar', '9876500002'),
    ('Thursday',  '17:30', 'Bus 02', 'Tut Block',  'Kalam',      'Ramesh Kumar', '9876500002'),
    ('Friday',    '08:00', 'Bus 02', 'Aryabhatta', 'Tut Block',  'Ramesh Kumar', '9876500002'),
    ('Friday',    '17:30', 'Bus 02', 'Tut Block',  'Kalam',      'Ramesh Kumar', '9876500002'),
    ('Saturday',  '09:00', 'Bus 02', 'Aryabhatta', 'Tut Block',  'Suresh Singh', '9876500003'),
    ('Saturday',  '18:00', 'Bus 02', 'Tut Block',  'Aryabhatta', 'Suresh Singh', '9876500003'),
    ('Sunday',    '10:00', 'Bus 02', 'Kalam',      'Tut Block',  'Suresh Singh', '9876500003'),
    ('Sunday',    '18:00', 'Bus 02', 'Tut Block',  'Kalam',      'Suresh Singh', '9876500003'),
    ('Monday',    '08:30', 'Bus 05', 'CV Raman',   'Tut Block',  'Anil Yadav',   '9876500005'),
    ('Monday',    '17:15', 'Bus 05', 'Tut Block',  'CV Raman',   'Anil Yadav',   '9876500005');

COMMIT;


-- ============================================================
-- Database: room_booking  (from room_booking.sql)
-- ============================================================
\connect room_booking

-- room_booking.sql
-- PostgreSQL schema for the IIT Patna Room Booking service.
-- Facilities:
--   SAC Hall       : students only, fixed 1-hour integer slots
--   Guest House    : 20 rooms (10 single, 10 double), day-based
--   CLH            : 6 rooms, fixed 1-hour integer slots
--                    faculty/admin direct; students request
--   Auditorium     : one facility, exactly 3 hours, integer-hour boundaries
--                    admin direct; student/faculty request
--
-- Run inside a dedicated database, e.g. room_booking.

CREATE EXTENSION IF NOT EXISTS btree_gist;

DROP TABLE IF EXISTS booking_history CASCADE;
DROP TABLE IF EXISTS requests CASCADE;
DROP TABLE IF EXISTS bookings CASCADE;
DROP TABLE IF EXISTS rooms CASCADE;
DROP TABLE IF EXISTS facilities CASCADE;

DROP FUNCTION IF EXISTS set_updated_at() CASCADE;
DROP TYPE IF EXISTS request_status;
DROP TYPE IF EXISTS booking_status;
DROP TYPE IF EXISTS room_type;
DROP TYPE IF EXISTS facility_type;

CREATE TYPE facility_type AS ENUM ('SAC_HALL', 'GUEST_HOUSE', 'CLH', 'AUDITORIUM');
CREATE TYPE room_type AS ENUM ('SINGLE', 'DOUBLE', 'STANDARD');
CREATE TYPE booking_status AS ENUM ('CONFIRMED', 'CANCELLED');
CREATE TYPE request_status AS ENUM ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED');

CREATE TABLE facilities (
    facility_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    facility_type facility_type NOT NULL UNIQUE,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE rooms (
    room_id SERIAL PRIMARY KEY,
    facility_id INTEGER NOT NULL REFERENCES facilities(facility_id) ON DELETE CASCADE,
    room_code TEXT NOT NULL UNIQUE,
    room_type room_type NOT NULL DEFAULT 'STANDARD',
    price_per_day NUMERIC(10,2),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (facility_id, room_code)
);

CREATE TABLE bookings (
    booking_id BIGSERIAL PRIMARY KEY,
    room_id INTEGER NOT NULL REFERENCES rooms(room_id) ON DELETE RESTRICT,

    booker_name TEXT NOT NULL,
    booker_roll_number TEXT,
    booker_role TEXT NOT NULL,

    -- Optional because the exact required fields differ by facility.
    purpose TEXT,

    -- Hourly facilities use booking_date/start_hour/end_hour.
    -- Guest House uses check_in/check_out.
    booking_date DATE,
    start_hour INTEGER,
    end_hour INTEGER,

    check_in DATE,
    check_out DATE,

    status booking_status NOT NULL DEFAULT 'CONFIRMED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (
        (
            booking_date IS NOT NULL
            AND start_hour IS NOT NULL
            AND end_hour IS NOT NULL
            AND check_in IS NULL
            AND check_out IS NULL
            AND start_hour >= 0
            AND start_hour <= 23
            AND end_hour > start_hour
            AND end_hour <= 24
        )
        OR
        (
            booking_date IS NULL
            AND start_hour IS NULL
            AND end_hour IS NULL
            AND check_in IS NOT NULL
            AND check_out IS NOT NULL
            AND check_in < check_out
        )
    )
);

CREATE TABLE requests (
    request_id BIGSERIAL PRIMARY KEY,
    room_id INTEGER NOT NULL REFERENCES rooms(room_id) ON DELETE RESTRICT,

    requester_name TEXT NOT NULL,
    requester_roll_number TEXT,
    requester_role TEXT NOT NULL,

    purpose TEXT,

    booking_date DATE,
    start_hour INTEGER,
    end_hour INTEGER,

    check_in DATE,
    check_out DATE,

    status request_status NOT NULL DEFAULT 'PENDING',

    -- Only the person who created the request or an authorized admin
    -- should normally act on it at the application layer.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decided_at TIMESTAMPTZ,
    decided_by_name TEXT,
    decided_by_role TEXT,

    CHECK (
        (
            booking_date IS NOT NULL
            AND start_hour IS NOT NULL
            AND end_hour IS NOT NULL
            AND check_in IS NULL
            AND check_out IS NULL
            AND start_hour >= 0
            AND start_hour <= 23
            AND end_hour > start_hour
            AND end_hour <= 24
        )
        OR
        (
            booking_date IS NULL
            AND start_hour IS NULL
            AND end_hour IS NULL
            AND check_in IS NOT NULL
            AND check_out IS NOT NULL
            AND check_in < check_out
        )
    )
);

CREATE TABLE booking_history (
    history_id BIGSERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('BOOKING', 'REQUEST')),
    entity_id BIGINT NOT NULL,
    action TEXT NOT NULL,
    actor_name TEXT NOT NULL,
    actor_roll_number TEXT,
    actor_role TEXT NOT NULL,
    old_data JSONB,
    new_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Prevent overlapping hourly bookings on the same room.
ALTER TABLE bookings
ADD CONSTRAINT no_overlapping_hourly_bookings
EXCLUDE USING gist (
    room_id WITH =,
    int8range(
        (booking_date - DATE '2000-01-01')::BIGINT * 24 + start_hour,
        (booking_date - DATE '2000-01-01')::BIGINT * 24 + end_hour,
        '[)'
    ) WITH &&
)
WHERE (
    status = 'CONFIRMED'
    AND booking_date IS NOT NULL
);

-- Prevent overlapping guest-house stays on the same room.
ALTER TABLE bookings
ADD CONSTRAINT no_overlapping_daily_bookings
EXCLUDE USING gist (
    room_id WITH =,
    daterange(check_in, check_out, '[)') WITH &&
)
WHERE (
    status = 'CONFIRMED'
    AND check_in IS NOT NULL
);

INSERT INTO facilities (name, facility_type)
VALUES
    ('SAC Hall', 'SAC_HALL'),
    ('Guest House', 'GUEST_HOUSE'),
    ('CLH', 'CLH'),
    ('Auditorium', 'AUDITORIUM');

-- SAC Hall is a single bookable resource.
INSERT INTO rooms (facility_id, room_code, room_type)
SELECT facility_id, 'SAC-HALL', 'STANDARD'
FROM facilities WHERE facility_type = 'SAC_HALL';

-- Guest House: 10 single + 10 double rooms.
INSERT INTO rooms (facility_id, room_code, room_type, price_per_day)
SELECT facility_id, 'GH-S-' || LPAD(i::TEXT, 2, '0'), 'SINGLE', 1200.00
FROM facilities, generate_series(1,10) AS i
WHERE facility_type = 'GUEST_HOUSE';

INSERT INTO rooms (facility_id, room_code, room_type, price_per_day)
SELECT facility_id, 'GH-D-' || LPAD(i::TEXT, 2, '0'), 'DOUBLE', 1800.00
FROM facilities, generate_series(1,10) AS i
WHERE facility_type = 'GUEST_HOUSE';

-- CLH: 6 rooms.
INSERT INTO rooms (facility_id, room_code, room_type)
SELECT facility_id, 'CLH-' || LPAD(i::TEXT, 2, '0'), 'STANDARD'
FROM facilities, generate_series(1,6) AS i
WHERE facility_type = 'CLH';

-- Auditorium is a single resource.
INSERT INTO rooms (facility_id, room_code, room_type)
SELECT facility_id, 'AUDITORIUM', 'STANDARD'
FROM facilities WHERE facility_type = 'AUDITORIUM';

CREATE INDEX idx_bookings_room_date ON bookings(room_id, booking_date);
CREATE INDEX idx_bookings_guest_dates ON bookings(room_id, check_in, check_out);
CREATE INDEX idx_bookings_booker ON bookings(booker_roll_number, booker_name);
CREATE INDEX idx_requests_requester ON requests(requester_roll_number, requester_name);
CREATE INDEX idx_requests_status ON requests(status);
CREATE INDEX idx_requests_room_date ON requests(room_id, booking_date);
CREATE INDEX idx_history_entity ON booking_history(entity_type, entity_id);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_bookings_updated_at
BEFORE UPDATE ON bookings
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_requests_updated_at
BEFORE UPDATE ON requests
FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- ============================================================
-- Database: complaints  (from complaints.sql)
-- ============================================================
\connect complaints

-- complaints.sql
-- PostgreSQL schema for the simplified IIT Patna Complaint service.
--
-- Flow:
--   1. User files a complaint tagged academic / hostel / mess
--      -> status PENDING_VERIFICATION
--   2. Admin or faculty verifies it
--      -> status PROGRESS
--   3. Admin or faculty marks it solved
--      -> status COMPLETED
--
-- Rules:
--   - An open complaint (PENDING_VERIFICATION or PROGRESS) cannot be
--     logged again with the same category, title, and description.
--   - Only the latest 50 COMPLETED complaints per category are kept.
--     Older completed rows are deleted; open complaints are never pruned.
--
-- Run inside the dedicated `complaints` database. Safe to re-run.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ------------------------------------------------------------------
-- Users (identity lookup for students by roll number, staff by email)
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    authentication_key VARCHAR,
    role VARCHAR,
    names TEXT,
    roll_number TEXT UNIQUE,
    email VARCHAR,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    hierarchy_level VARCHAR,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- Keep complaints.users.id aligned with roll_number (campus roll, not UUID).
CREATE OR REPLACE FUNCTION users_set_roll_number_to_id()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.id IS NULL OR btrim(NEW.id) = '' THEN
        NEW.id := NEW.roll_number;
    END IF;
    IF NEW.roll_number IS NULL OR btrim(NEW.roll_number) = '' THEN
        NEW.roll_number := NEW.id;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_users_roll_number_to_id ON users;
CREATE TRIGGER trg_users_roll_number_to_id
BEFORE INSERT OR UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION users_set_roll_number_to_id();

ALTER TABLE users DROP CONSTRAINT IF EXISTS users_roll_number_eq_id;
ALTER TABLE users ADD CONSTRAINT users_roll_number_eq_id CHECK (roll_number = id);

-- ------------------------------------------------------------------
-- Drop workflow tables that the simplified agent no longer uses.
-- ------------------------------------------------------------------
DROP TABLE IF EXISTS complaint_votes CASCADE;
DROP TABLE IF EXISTS complaint_notifications CASCADE;
DROP TABLE IF EXISTS complaint_routing_rules CASCADE;
DROP TABLE IF EXISTS complaint_escalation_policies CASCADE;
DROP TABLE IF EXISTS guest_permissions CASCADE;

-- ------------------------------------------------------------------
-- Rebuild complaints with the simplified columns when the live table
-- still has the old schema. Skip if already simplified.
-- ------------------------------------------------------------------
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'complaints'
          AND column_name = 'visibility'
    ) THEN
        DROP TABLE IF EXISTS complaints_simplified CASCADE;

        CREATE TABLE complaints_simplified (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            complaint_number VARCHAR(32) NOT NULL UNIQUE,
            user_id TEXT NOT NULL REFERENCES users(id),
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category VARCHAR(20) NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'PENDING_VERIFICATION',
            verified_by TEXT REFERENCES users(id),
            verified_at TIMESTAMPTZ,
            completed_by TEXT REFERENCES users(id),
            completed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ,
            CONSTRAINT complaints_category_check
                CHECK (LOWER(category) IN ('academic', 'hostel', 'mess')),
            CONSTRAINT complaints_status_check
                CHECK (status IN ('PENDING_VERIFICATION', 'PROGRESS', 'COMPLETED')),
            CONSTRAINT complaints_title_check
                CHECK (btrim(title) <> ''),
            CONSTRAINT complaints_description_check
                CHECK (btrim(description) <> '')
        );

        INSERT INTO complaints_simplified (
            id, complaint_number, user_id, title, description,
            category, status, verified_at, completed_at, created_at, updated_at
        )
        SELECT
            c.id,
            c.complaint_number,
            COALESCE(c.user_id, c.roll_number),
            c.title,
            c.description,
            CASE
                WHEN LOWER(c.category) IN ('academic', 'hostel', 'mess')
                    THEN LOWER(c.category)
                ELSE 'hostel'
            END,
            CASE
                WHEN c.status IN (
                    'VERIFIED', 'ASSIGNED', 'IN_PROGRESS',
                    'WAITING_FOR_USER', 'ESCALATED', 'PROGRESS'
                ) THEN 'PROGRESS'
                WHEN c.status IN ('RESOLVED', 'CLOSED', 'COMPLETED')
                    THEN 'COMPLETED'
                ELSE 'PENDING_VERIFICATION'
            END,
            c.verified_at,
            COALESCE(c.closed_at, c.resolved_at),
            c.created_at,
            c.updated_at
        FROM complaints c
        WHERE COALESCE(c.user_id, c.roll_number) IS NOT NULL
        ON CONFLICT (complaint_number) DO NOTHING;

        DROP TABLE IF EXISTS complaint_history CASCADE;
        DROP TABLE complaints;
        ALTER TABLE complaints_simplified RENAME TO complaints;
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS complaints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    complaint_number VARCHAR(32) NOT NULL UNIQUE,
    user_id TEXT NOT NULL REFERENCES users(id),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(20) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING_VERIFICATION',
    verified_by TEXT REFERENCES users(id),
    verified_at TIMESTAMPTZ,
    completed_by TEXT REFERENCES users(id),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    CONSTRAINT complaints_category_check
        CHECK (LOWER(category) IN ('academic', 'hostel', 'mess')),
    CONSTRAINT complaints_status_check
        CHECK (status IN ('PENDING_VERIFICATION', 'PROGRESS', 'COMPLETED')),
    CONSTRAINT complaints_title_check
        CHECK (btrim(title) <> ''),
    CONSTRAINT complaints_description_check
        CHECK (btrim(description) <> '')
);

ALTER TABLE complaints ADD COLUMN IF NOT EXISTS name TEXT;
ALTER TABLE complaints ADD COLUMN IF NOT EXISTS roll_number TEXT;

-- ------------------------------------------------------------------
-- Audit history. ON DELETE CASCADE so pruning completed complaints
-- also removes their history rows.
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS complaint_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    complaint_id UUID NOT NULL REFERENCES complaints(id) ON DELETE CASCADE,
    actor_id TEXT REFERENCES users(id),
    actor_role VARCHAR NOT NULL,
    action VARCHAR NOT NULL,
    from_status VARCHAR,
    to_status VARCHAR,
    extra JSON,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------------
-- Indexes
-- ------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_complaints_category
    ON complaints (LOWER(category));

CREATE INDEX IF NOT EXISTS idx_complaints_status
    ON complaints (status);

CREATE INDEX IF NOT EXISTS idx_complaints_user_id
    ON complaints (user_id);

CREATE INDEX IF NOT EXISTS idx_complaints_created_at
    ON complaints (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_complaints_category_completed
    ON complaints (LOWER(category), completed_at DESC)
    WHERE status = 'COMPLETED';

CREATE INDEX IF NOT EXISTS idx_complaint_history_complaint_id
    ON complaint_history (complaint_id, created_at);

-- Same open complaint (category + title + description) cannot be filed twice.
CREATE UNIQUE INDEX IF NOT EXISTS uniq_open_complaints
    ON complaints (
        LOWER(category),
        LOWER(btrim(title)),
        md5(LOWER(btrim(description)))
    )
    WHERE status IN ('PENDING_VERIFICATION', 'PROGRESS');

-- ------------------------------------------------------------------
-- Keep only the latest 50 COMPLETED complaints per category.
-- Open (pending / progress) rows are never deleted by this trigger.
-- ------------------------------------------------------------------
CREATE OR REPLACE FUNCTION prune_old_completed_complaints()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    DELETE FROM complaints
    WHERE LOWER(category) = LOWER(NEW.category)
      AND status = 'COMPLETED'
      AND id NOT IN (
          SELECT id
          FROM complaints
          WHERE LOWER(category) = LOWER(NEW.category)
            AND status = 'COMPLETED'
          ORDER BY completed_at DESC NULLS LAST, created_at DESC
          LIMIT 50
      );
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_prune_completed_complaints ON complaints;

CREATE TRIGGER trg_prune_completed_complaints
AFTER INSERT OR UPDATE OF status ON complaints
FOR EACH ROW
WHEN (NEW.status = 'COMPLETED')
EXECUTE FUNCTION prune_old_completed_complaints();

-- If an older restore stored user identity as UUID, convert it to TEXT so
-- campus roll numbers like 2501CS09 can be the user id.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'users'
          AND column_name = 'id'
          AND data_type = 'uuid'
    ) THEN
        ALTER TABLE users DROP CONSTRAINT IF EXISTS users_roll_number_eq_id;
        ALTER TABLE complaint_history DROP CONSTRAINT IF EXISTS complaint_history_actor_id_fkey;
        ALTER TABLE complaints DROP CONSTRAINT IF EXISTS complaints_completed_by_fkey;
        ALTER TABLE complaints DROP CONSTRAINT IF EXISTS complaints_user_id_fkey;
        ALTER TABLE complaints DROP CONSTRAINT IF EXISTS complaints_verified_by_fkey;

        ALTER TABLE users ALTER COLUMN id DROP DEFAULT;
        ALTER TABLE users ALTER COLUMN id TYPE TEXT USING id::text;

        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'complaints' AND column_name = 'user_id'
        ) THEN
            ALTER TABLE complaints ALTER COLUMN user_id TYPE TEXT USING user_id::text;
            ALTER TABLE complaints ALTER COLUMN verified_by TYPE TEXT USING verified_by::text;
            ALTER TABLE complaints ALTER COLUMN completed_by TYPE TEXT USING completed_by::text;
        END IF;

        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'complaint_history' AND column_name = 'actor_id'
        ) THEN
            ALTER TABLE complaint_history ALTER COLUMN actor_id TYPE TEXT USING actor_id::text;
        END IF;

        ALTER TABLE complaints
            ADD CONSTRAINT complaints_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);
        ALTER TABLE complaints
            ADD CONSTRAINT complaints_verified_by_fkey FOREIGN KEY (verified_by) REFERENCES users(id);
        ALTER TABLE complaints
            ADD CONSTRAINT complaints_completed_by_fkey FOREIGN KEY (completed_by) REFERENCES users(id);
        ALTER TABLE complaint_history
            ADD CONSTRAINT complaint_history_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES users(id);

        ALTER TABLE users ADD CONSTRAINT users_roll_number_eq_id CHECK (roll_number = id);
    END IF;
END
$$;

-- Demo identities. `id` must match campus_agent.users.roll_number.
-- Students use IIT-style rolls; faculty PF001+; admins AD001+.
UPDATE users SET id = 'PF001', roll_number = 'PF001', names = 'Priya Patel', role = 'faculty'
WHERE authentication_key = 'faculty-demo';
UPDATE users SET id = 'AD001', roll_number = 'AD001', names = 'Rohan Verma', role = 'admin'
WHERE authentication_key = 'admin-demo';
UPDATE users SET id = '2501CS09', roll_number = '2501CS09', names = 'Aarav Sharma', role = 'student'
WHERE authentication_key = 'student-demo';

INSERT INTO users (id, authentication_key, role, names, roll_number, email, hierarchy_level, is_active)
VALUES
    ('2501CS09', 'student-demo', 'student', 'Aarav Sharma', '2501CS09', 'aarav.sharma@example.edu', 'student', TRUE),
    ('2501CS90', 'student-neha', 'student', 'Neha Gupta', '2501CS90', 'neha.gupta@example.edu', 'student', TRUE),
    ('2501CS91', 'student-kabir', 'student', 'Kabir Mehta', '2501CS91', 'kabir.mehta@example.edu', 'student', TRUE),
    ('2501AI51', 'student-ananya', 'student', 'Ananya Iyer', '2501AI51', 'ananya.iyer@example.edu', 'student', TRUE),
    ('2501CS92', 'student-vikram', 'student', 'Vikram Singh', '2501CS92', 'vikram.singh@example.edu', 'student', TRUE),
    ('PF001', 'faculty-demo', 'faculty', 'Priya Patel', 'PF001', 'priya.patel@example.edu', 'faculty', TRUE),
    ('PF002', 'faculty-arjun', 'faculty', 'Arjun Nair', 'PF002', 'arjun.nair@example.edu', 'faculty', TRUE),
    ('PF003', 'faculty-meera', 'faculty', 'Meera Joshi', 'PF003', 'meera.joshi@example.edu', 'faculty', TRUE),
    ('PF004', 'faculty-sameer', 'faculty', 'Sameer Khan', 'PF004', 'sameer.khan@example.edu', 'faculty', TRUE),
    ('PF005', 'faculty-kavita', 'faculty', 'Kavita Desai', 'PF005', 'kavita.desai@example.edu', 'faculty', TRUE),
    ('PF006', 'faculty-aditi', 'faculty', 'Aditi Rao', 'PF006', 'aditi.rao@example.edu', 'faculty', TRUE),
    ('PF007', 'faculty-harsh', 'faculty', 'Harsh Vardhan', 'PF007', 'harsh.vardhan@example.edu', 'faculty', TRUE),
    ('PF008', 'faculty-leela', 'faculty', 'Leela Menon', 'PF008', 'leela.menon@example.edu', 'faculty', TRUE),
    ('PF009', 'faculty-omar', 'faculty', 'Omar Qureshi', 'PF009', 'omar.qureshi@example.edu', 'faculty', TRUE),
    ('PF010', 'faculty-tanvi', 'faculty', 'Tanvi Shah', 'PF010', 'tanvi.shah@example.edu', 'faculty', TRUE),
    ('PF011', 'faculty-nikhil', 'faculty', 'Nikhil Rao', 'PF011', 'nikhil.rao@example.edu', 'faculty', TRUE),
    ('PF012', 'faculty-pooja', 'faculty', 'Pooja Bhatt', 'PF012', 'pooja.bhatt@example.edu', 'faculty', TRUE),
    ('PF013', 'faculty-farhan', 'faculty', 'Farhan Ali', 'PF013', 'farhan.ali@example.edu', 'faculty', TRUE),
    ('PF014', 'faculty-diya', 'faculty', 'Diya Kulkarni', 'PF014', 'diya.kulkarni@example.edu', 'faculty', TRUE),
    ('PF015', 'faculty-yash', 'faculty', 'Yash Agarwal', 'PF015', 'yash.agarwal@example.edu', 'faculty', TRUE),
    ('PF016', 'faculty-sana', 'faculty', 'Sana Iqbal', 'PF016', 'sana.iqbal@example.edu', 'faculty', TRUE),
    ('AD001', 'admin-demo', 'admin', 'Rohan Verma', 'AD001', 'rohan.verma@example.edu', 'admin', TRUE),
    ('AD002', 'admin-nisha', 'admin', 'Nisha Kapoor', 'AD002', 'nisha.kapoor@example.edu', 'admin', TRUE)
ON CONFLICT (id) DO UPDATE
SET authentication_key = EXCLUDED.authentication_key,
    role = EXCLUDED.role,
    names = EXCLUDED.names,
    roll_number = EXCLUDED.roll_number,
    email = EXCLUDED.email,
    hierarchy_level = EXCLUDED.hierarchy_level,
    is_active = EXCLUDED.is_active;

COMMIT;


-- ============================================================
-- Database: organization_agent  (from attendance.sql)
-- ============================================================
\connect organization_agent

-- attendance.sql
-- PostgreSQL schema for the IIT Patna Attendance service.
--
-- Tables:
--   people       student | faculty | admin, keyed by roll_num
--   courses      taught by a faculty roll_num
--   enrollments  student <-> course
--   attendance   one mark per student/course/session_date
--
-- Identity: campus_agent.users.roll_number is stored here as people.roll_num.
-- Students: 2501CS09-style. Faculty: PF001+. Admins: AD001+.
--
-- Run inside the dedicated `organization_agent` database (ATTENDANCE_DB_NAME).
-- Safe to re-run: drops and recreates the four tables.

BEGIN;

DROP TABLE IF EXISTS attendance CASCADE;
DROP TABLE IF EXISTS enrollments CASCADE;
DROP TABLE IF EXISTS courses CASCADE;
DROP TABLE IF EXISTS people CASCADE;

CREATE TABLE people (
    roll_num TEXT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL,
    CONSTRAINT people_role_check
        CHECK (role IN ('student', 'faculty', 'admin'))
);

CREATE TABLE courses (
    code VARCHAR(32) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    professor_name VARCHAR(255) NOT NULL,
    professor_roll TEXT NOT NULL REFERENCES people(roll_num),
    department VARCHAR(128) NOT NULL DEFAULT 'CSE',
    min_attendance_percent INTEGER NOT NULL DEFAULT 75,
    planned_sessions INTEGER NOT NULL DEFAULT 40
);

CREATE TABLE enrollments (
    student_roll TEXT NOT NULL REFERENCES people(roll_num),
    student_name VARCHAR(255) NOT NULL,
    course_code VARCHAR(32) NOT NULL REFERENCES courses(code),
    PRIMARY KEY (student_roll, course_code)
);

CREATE TABLE attendance (
    student_roll TEXT NOT NULL REFERENCES people(roll_num),
    student_name VARCHAR(255) NOT NULL,
    course_code VARCHAR(32) NOT NULL REFERENCES courses(code),
    session_date DATE NOT NULL,
    attendance_status VARCHAR(32) NOT NULL,
    marked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    marked_by_roll TEXT NOT NULL REFERENCES people(roll_num),
    marked_by_name VARCHAR(255) NOT NULL,
    PRIMARY KEY (student_roll, course_code, session_date),
    CONSTRAINT attendance_status_check
        CHECK (LOWER(attendance_status) IN ('present', 'absent', 'late', 'excused'))
);

CREATE INDEX idx_attendance_course_date
    ON attendance (course_code, session_date);
CREATE INDEX idx_attendance_student_date
    ON attendance (student_roll, session_date);
CREATE INDEX idx_enrollments_course
    ON enrollments (course_code);
CREATE INDEX idx_people_role
    ON people (role);
CREATE INDEX idx_courses_professor
    ON courses (professor_roll);

CREATE OR REPLACE FUNCTION fill_enrollment_student_name()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.student_name IS NULL OR btrim(NEW.student_name) = '' THEN
        SELECT name INTO NEW.student_name
        FROM people WHERE LOWER(roll_num) = LOWER(NEW.student_roll);
    END IF;
    RETURN NEW;
END;
$$;
DROP TRIGGER IF EXISTS trg_enrollments_student_name ON enrollments;
CREATE TRIGGER trg_enrollments_student_name
BEFORE INSERT OR UPDATE ON enrollments
FOR EACH ROW EXECUTE FUNCTION fill_enrollment_student_name();

CREATE OR REPLACE FUNCTION fill_attendance_names()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.student_name IS NULL OR btrim(NEW.student_name) = '' THEN
        SELECT name INTO NEW.student_name
        FROM people WHERE LOWER(roll_num) = LOWER(NEW.student_roll);
    END IF;
    IF NEW.marked_by_name IS NULL OR btrim(NEW.marked_by_name) = '' THEN
        SELECT name INTO NEW.marked_by_name
        FROM people WHERE LOWER(roll_num) = LOWER(NEW.marked_by_roll);
    END IF;
    RETURN NEW;
END;
$$;
DROP TRIGGER IF EXISTS trg_attendance_names ON attendance;
CREATE TRIGGER trg_attendance_names
BEFORE INSERT OR UPDATE ON attendance
FOR EACH ROW EXECUTE FUNCTION fill_attendance_names();

-- Demo people. Students use IIT-style rolls (2501CS09). Faculty use PF001+.
-- Admins use AD001+. Every name and roll_num is unique.
INSERT INTO people (roll_num, name, role) VALUES
    ('2501CS09', 'Aarav Sharma', 'student'),
    ('2501CS90', 'Neha Gupta', 'student'),
    ('2501CS91', 'Kabir Mehta', 'student'),
    ('2501AI51', 'Ananya Iyer', 'student'),
    ('2501CS92', 'Vikram Singh', 'student'),
    ('PF001', 'Priya Patel', 'faculty'),
    ('PF002', 'Arjun Nair', 'faculty'),
    ('PF003', 'Meera Joshi', 'faculty'),
    ('PF004', 'Sameer Khan', 'faculty'),
    ('PF005', 'Kavita Desai', 'faculty'),
    ('PF006', 'Aditi Rao', 'faculty'),
    ('PF007', 'Harsh Vardhan', 'faculty'),
    ('PF008', 'Leela Menon', 'faculty'),
    ('PF009', 'Omar Qureshi', 'faculty'),
    ('PF010', 'Tanvi Shah', 'faculty'),
    ('PF011', 'Nikhil Rao', 'faculty'),
    ('PF012', 'Pooja Bhatt', 'faculty'),
    ('PF013', 'Farhan Ali', 'faculty'),
    ('PF014', 'Diya Kulkarni', 'faculty'),
    ('PF015', 'Yash Agarwal', 'faculty'),
    ('PF016', 'Sana Iqbal', 'faculty'),
    ('AD001', 'Rohan Verma', 'admin'),
    ('AD002', 'Nisha Kapoor', 'admin');

INSERT INTO courses (
    code, name, professor_name, professor_roll,
    department, min_attendance_percent, planned_sessions
) VALUES
    ('CS101', 'Algorithms', 'Priya Patel', 'PF001', 'CSE', 75, 40),
    ('CS102', 'Data Structures', 'Arjun Nair', 'PF002', 'CSE', 75, 40),
    ('MA201', 'Linear Algebra', 'Meera Joshi', 'PF003', 'MA', 75, 40),
    ('PHY101', 'Physics', 'Sameer Khan', 'PF004', 'PHY', 75, 40),
    ('HS101', 'Communication', 'Kavita Desai', 'PF005', 'HS', 75, 40);

INSERT INTO enrollments (student_roll, student_name, course_code) VALUES
    ('2501CS09', 'Aarav Sharma', 'CS101'),
    ('2501CS90', 'Neha Gupta', 'CS102'),
    ('2501CS91', 'Kabir Mehta', 'MA201'),
    ('2501AI51', 'Ananya Iyer', 'PHY101'),
    ('2501CS92', 'Vikram Singh', 'HS101');

INSERT INTO attendance (
    student_roll, student_name, course_code, session_date,
    attendance_status, marked_at, marked_by_roll, marked_by_name
) VALUES
    ('2501CS09', 'Aarav Sharma', 'CS101', DATE '2026-09-08', 'present',
     TIMESTAMPTZ '2026-09-13 14:32:02+00', 'PF001', 'Priya Patel'),
    ('2501CS09', 'Aarav Sharma', 'CS101', DATE '2026-09-10', 'present',
     TIMESTAMPTZ '2026-09-13 14:32:02+00', 'PF001', 'Priya Patel'),
    ('2501CS09', 'Aarav Sharma', 'CS101', DATE '2026-09-12', 'absent',
     TIMESTAMPTZ '2026-09-13 14:32:02+00', 'PF001', 'Priya Patel'),
    ('2501CS90', 'Neha Gupta', 'CS102', DATE '2026-09-08', 'present',
     TIMESTAMPTZ '2026-09-13 14:32:02+00', 'PF002', 'Arjun Nair'),
    ('2501CS90', 'Neha Gupta', 'CS102', DATE '2026-09-10', 'late',
     TIMESTAMPTZ '2026-09-13 14:32:02+00', 'PF002', 'Arjun Nair'),
    ('2501CS91', 'Kabir Mehta', 'MA201', DATE '2026-09-08', 'present',
     TIMESTAMPTZ '2026-09-13 14:32:02+00', 'PF003', 'Meera Joshi'),
    ('2501AI51', 'Ananya Iyer', 'PHY101', DATE '2026-09-08', 'absent',
     TIMESTAMPTZ '2026-09-13 14:32:02+00', 'PF004', 'Sameer Khan'),
    ('2501CS92', 'Vikram Singh', 'HS101', DATE '2026-09-08', 'present',
     TIMESTAMPTZ '2026-09-13 14:32:02+00', 'PF005', 'Kavita Desai');

COMMIT;


-- ============================================================
-- Database: notice_board  (from notice_board.sql)
-- ============================================================
\connect notice_board

-- notice_board.sql
-- PostgreSQL schema for the IIT Patna Notice Board service.
--
-- Run inside the dedicated `notice_board` database. Safe to re-run.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS notices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    publish_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    content TEXT NOT NULL,
    notice_type VARCHAR(100) NOT NULL,
    author_id VARCHAR(255) NOT NULL,
    author_authority VARCHAR(100) NOT NULL,
    target_audience TEXT[] NOT NULL,
    status VARCHAR(50) DEFAULT 'Active',
    expires_at TIMESTAMPTZ
);

COMMIT;


-- ============================================================
-- Database: timetable  (from timetable.sql)
-- ============================================================
\connect timetable

-- timetable.sql
-- PostgreSQL schema for the IIT Patna Timetable service.
--
-- Tables:
--   people     student | faculty | admin | guest, keyed by roll_num
--   courses    taught by a faculty roll_num
--   rooms      lecture halls and labs
--   timetable  one row per class slot
--
-- Run inside the dedicated `timetable` database (TIMETABLE_DB_NAME).
-- Safe to re-run: drops and recreates the four tables.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

DROP TABLE IF EXISTS timetable CASCADE;
DROP TABLE IF EXISTS enrollments CASCADE;
DROP TABLE IF EXISTS courses CASCADE;
DROP TABLE IF EXISTS rooms CASCADE;
DROP TABLE IF EXISTS people CASCADE;

CREATE TABLE people (
    roll_num TEXT PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    role VARCHAR(32) NOT NULL,            -- 'student', 'faculty', 'admin', 'guest'
    student_group VARCHAR(64)             -- e.g., 'G1', 'G21' (NULL for faculty/2nd years)
);

CREATE TABLE courses (
    code VARCHAR(32) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    professor_name VARCHAR(128),
    professor_roll TEXT,                  -- Links to people.roll_num
    department VARCHAR(32) NOT NULL,
    min_attendance_percent INT DEFAULT 75,
    planned_sessions INT DEFAULT 40
);

CREATE TABLE rooms (
    room_id VARCHAR(32) PRIMARY KEY,
    capacity INTEGER NOT NULL DEFAULT 60,
    building VARCHAR(128) NOT NULL DEFAULT 'Main'
);

CREATE TABLE timetable (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_code VARCHAR(32) NOT NULL REFERENCES courses(code) ON DELETE CASCADE,
    timetable_day VARCHAR(16) NOT NULL,
    slot_start TIME NOT NULL,
    slot_end TIME NOT NULL,
    room_id VARCHAR(32) NOT NULL REFERENCES rooms(room_id) ON DELETE CASCADE,
    class_type VARCHAR(32),               -- 'lecture', 'lab', 'tutorial'
    student_group VARCHAR(64),            -- e.g., 'G1-G24', 'G19-21'
    department VARCHAR(32)                -- e.g., 'CSE', 'CBE'
);

CREATE INDEX idx_timetable_day ON timetable (timetable_day);
CREATE INDEX idx_timetable_course ON timetable (course_code);
CREATE INDEX idx_timetable_room ON timetable (room_id);
CREATE INDEX idx_people_role ON people (role);
CREATE UNIQUE INDEX uq_timetable_course_day_start
    ON timetable (course_code, timetable_day, slot_start);

INSERT INTO people (roll_num, name, role) VALUES
    ('AD001', 'Rohan Verma', 'admin'),
    ('AD002', 'Nisha Kapoor', 'admin'),
    ('PF001', 'Priya Patel', 'faculty'),
    ('PF006', 'Aditi Rao', 'faculty'),
    ('PF007', 'Harsh Vardhan', 'faculty'),
    ('PF008', 'Leela Menon', 'faculty'),
    ('PF009', 'Omar Qureshi', 'faculty'),
    ('PF010', 'Tanvi Shah', 'faculty'),
    ('PF011', 'Nikhil Rao', 'faculty'),
    ('PF012', 'Pooja Bhatt', 'faculty'),
    ('PF013', 'Farhan Ali', 'faculty'),
    ('PF014', 'Diya Kulkarni', 'faculty'),
    ('PF015', 'Yash Agarwal', 'faculty'),
    ('PF016', 'Sana Iqbal', 'faculty'),
    ('2501CS90', 'Neha Gupta', 'student'),
    ('2501CS91', 'Kabir Mehta', 'student'),
    ('2501AI51', 'Ananya Iyer', 'student'),
    ('2501CS92', 'Vikram Singh', 'student');

INSERT INTO courses (code, name, professor_name, professor_roll, department) VALUES
    ('MA1101', 'Calculus and Linear Algebra', 'Aditi Rao', 'PF006', 'MA'),
    ('CS1101', 'Foundations of Programming', 'Harsh Vardhan', 'PF007', 'CS'),
    ('PH1101', 'Physics', 'Leela Menon', 'PF008', 'PH'),
    ('CE1101', 'Engineering Graphics', 'Omar Qureshi', 'PF009', 'CE'),
    ('CS2101', 'Algorithms', 'Tanvi Shah', 'PF010', 'CS'),
    ('CS2102', 'Digital Logic', 'Nikhil Rao', 'PF011', 'CS'),
    ('CS2103', 'AI Concepts', 'Pooja Bhatt', 'PF012', 'CS'),
    ('CB2101', 'Process Calculations', 'Farhan Ali', 'PF013', 'CB'),
    ('CB2102', 'Fluid Mechanics', 'Diya Kulkarni', 'PF014', 'CB'),
    ('CB2103', 'Chemical Engineering Thermodynamics', 'Yash Agarwal', 'PF015', 'CB'),
    ('CB2105', 'Mechanical Operations', 'Sana Iqbal', 'PF016', 'CB');

INSERT INTO rooms (room_id, capacity) VALUES
    ('Auditorium', 500), ('LT001', 120), ('LT002', 120),
    ('R-102', 60), ('R-104', 60), ('R-307', 60),
    ('CC-LAB', 100), ('CBE-LAB', 40);

INSERT INTO timetable (course_code, timetable_day, slot_start, slot_end, room_id, class_type, student_group, department) VALUES
    ('MA1101', 'Wednesday', '13:00:00', '13:55:00', 'Auditorium', 'lecture', 'G1-G24', 'MA'),
    ('MA1101', 'Thursday', '13:00:00', '13:55:00', 'Auditorium', 'lecture', 'G1-G24', 'MA'),
    ('MA1101', 'Friday', '13:00:00', '13:55:00', 'Auditorium', 'lecture', 'G1-G24', 'MA'),
    ('CS1101', 'Wednesday', '14:00:00', '14:55:00', 'Auditorium', 'lecture', 'G1-G24', 'CS'),
    ('CS1101', 'Wednesday', '15:00:00', '18:00:00', 'CC-LAB', 'lab', 'G1-G6', 'CS'),
    ('CS1101', 'Wednesday', '08:00:00', '11:00:00', 'CC-LAB', 'lab', 'G7-G12', 'CS'),
    ('CS2103', 'Monday', '10:00:00', '10:55:00', 'LT001', 'lecture', NULL, 'CS'),
    ('CS2102', 'Monday', '11:00:00', '11:55:00', 'LT001', 'lecture', NULL, 'CS'),
    ('CS2101', 'Monday', '12:00:00', '12:55:00', 'LT001', 'lecture', NULL, 'CS'),
    ('CB2102', 'Monday', '16:00:00', '16:55:00', 'R-102', 'lecture', NULL, 'CB'),
    ('CB2102', 'Tuesday', '11:00:00', '11:55:00', 'R-307', 'lecture', NULL, 'CB'),
    ('CB2105', 'Tuesday', '09:00:00', '09:55:00', 'R-307', 'lecture', NULL, 'CB');

COMMIT;


-- ============================================================
-- Extra indexes (from postgres_indexes.sql)
-- ============================================================

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
