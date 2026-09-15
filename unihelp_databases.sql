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
-- roll_number is a UUID. The same UUID must exist as:
--   complaints.users.id
--   organization_agent.people.roll_num  (as text)
--
-- Run inside the dedicated `campus_agent` database.

BEGIN;

CREATE TABLE IF NOT EXISTS users (
    authentication_key VARCHAR PRIMARY KEY,
    role VARCHAR NOT NULL,
    names TEXT NOT NULL,
    roll_number UUID UNIQUE NOT NULL,
    CONSTRAINT users_role_check
        CHECK (LOWER(role) IN ('student', 'faculty', 'admin'))
);

INSERT INTO users (authentication_key, role, names, roll_number) VALUES
    (
        'student-demo',
        'student',
        'Aarav Sharma',
        '3a63c6fe-18be-4110-8bfc-02f8538eaaab'
    ),
    (
        'faculty-demo',
        'faculty',
        'Priya Patel',
        '271875d6-51ca-4236-9d13-3d43c25d0320'
    ),
    (
        'admin-demo',
        'admin',
        'Rohan Verma',
        '3af87d28-f359-4494-9dbe-f6d765b40d8b'
    )
ON CONFLICT (authentication_key) DO NOTHING;

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
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    authentication_key VARCHAR,
    role VARCHAR,
    names TEXT,
    roll_number UUID UNIQUE,
    email VARCHAR,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    hierarchy_level VARCHAR,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

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
            user_id UUID NOT NULL REFERENCES users(id),
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category VARCHAR(20) NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'PENDING_VERIFICATION',
            verified_by UUID REFERENCES users(id),
            verified_at TIMESTAMPTZ,
            completed_by UUID REFERENCES users(id),
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
    user_id UUID NOT NULL REFERENCES users(id),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(20) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING_VERIFICATION',
    verified_by UUID REFERENCES users(id),
    verified_at TIMESTAMPTZ,
    completed_by UUID REFERENCES users(id),
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

-- ------------------------------------------------------------------
-- Audit history. ON DELETE CASCADE so pruning completed complaints
-- also removes their history rows.
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS complaint_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    complaint_id UUID NOT NULL REFERENCES complaints(id) ON DELETE CASCADE,
    actor_id UUID REFERENCES users(id),
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

-- Demo identities. `id` must match campus_agent.users.roll_number because
-- the executor passes that UUID as the complaint user identifier.
INSERT INTO users (id, authentication_key, role, names, roll_number, email, hierarchy_level, is_active)
VALUES
    (
        '3a63c6fe-18be-4110-8bfc-02f8538eaaab',
        'student-demo',
        'student',
        'Aarav Sharma',
        '3a63c6fe-18be-4110-8bfc-02f8538eaaab',
        'aarav.sharma@example.edu',
        'student',
        TRUE
    ),
    (
        '271875d6-51ca-4236-9d13-3d43c25d0320',
        'faculty-demo',
        'faculty',
        'Priya Patel',
        '271875d6-51ca-4236-9d13-3d43c25d0320',
        'priya.patel@example.edu',
        'faculty',
        TRUE
    ),
    (
        '3af87d28-f359-4494-9dbe-f6d765b40d8b',
        'admin-demo',
        'admin',
        'Rohan Verma',
        '3af87d28-f359-4494-9dbe-f6d765b40d8b',
        'rohan.verma@example.edu',
        'admin',
        TRUE
    )
ON CONFLICT (id) DO NOTHING;

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
-- Identity: campus_agent.users.roll_number is stored here as people.roll_num
-- (text). Sample S-100 / E-100 / A-100 rows are kept for local tool tests.
--
-- Run inside the dedicated `organization_agent` database (ATTENDANCE_DB_NAME).
-- Safe to re-run: drops and recreates the four tables.

BEGIN;

DROP TABLE IF EXISTS attendance CASCADE;
DROP TABLE IF EXISTS enrollments CASCADE;
DROP TABLE IF EXISTS courses CASCADE;
DROP TABLE IF EXISTS people CASCADE;

CREATE TABLE people (
    roll_num VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL,
    CONSTRAINT people_role_check
        CHECK (role IN ('student', 'faculty', 'admin'))
);

CREATE TABLE courses (
    code VARCHAR(32) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    professor_name VARCHAR(255) NOT NULL,
    professor_roll VARCHAR(64) NOT NULL REFERENCES people(roll_num),
    department VARCHAR(128) NOT NULL DEFAULT 'CSE',
    min_attendance_percent INTEGER NOT NULL DEFAULT 75,
    planned_sessions INTEGER NOT NULL DEFAULT 40
);

CREATE TABLE enrollments (
    student_roll VARCHAR(64) NOT NULL REFERENCES people(roll_num),
    course_code VARCHAR(32) NOT NULL REFERENCES courses(code),
    PRIMARY KEY (student_roll, course_code)
);

CREATE TABLE attendance (
    student_roll VARCHAR(64) NOT NULL REFERENCES people(roll_num),
    course_code VARCHAR(32) NOT NULL REFERENCES courses(code),
    session_date DATE NOT NULL,
    attendance_status VARCHAR(32) NOT NULL,
    marked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    marked_by_roll VARCHAR(64) NOT NULL REFERENCES people(roll_num),
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

-- Demo people used by standalone tool tests.
INSERT INTO people (roll_num, name, role) VALUES
    ('S-100', 'Local Student', 'student'),
    ('E-100', 'Local Faculty', 'faculty'),
    ('A-100', 'Local Admin', 'admin');

-- Campus-agent identities (users.roll_number as text).
INSERT INTO people (roll_num, name, role) VALUES
    ('3a63c6fe-18be-4110-8bfc-02f8538eaaab', 'Aarav Sharma', 'student'),
    ('271875d6-51ca-4236-9d13-3d43c25d0320', 'Priya Patel', 'faculty'),
    ('3af87d28-f359-4494-9dbe-f6d765b40d8b', 'Rohan Verma', 'admin');

INSERT INTO courses (
    code, name, professor_name, professor_roll,
    department, min_attendance_percent, planned_sessions
) VALUES
    ('CS101', 'Algorithms', 'Priya Patel',
     '271875d6-51ca-4236-9d13-3d43c25d0320', 'CSE', 75, 40),
    ('CS102', 'Data Structures', 'Priya Patel',
     '271875d6-51ca-4236-9d13-3d43c25d0320', 'CSE', 75, 40),
    ('MA201', 'Linear Algebra', 'Priya Patel',
     '271875d6-51ca-4236-9d13-3d43c25d0320', 'CSE', 75, 40),
    ('PHY101', 'Physics', 'Priya Patel',
     '271875d6-51ca-4236-9d13-3d43c25d0320', 'CSE', 75, 40),
    ('HS101', 'Communication', 'Priya Patel',
     '271875d6-51ca-4236-9d13-3d43c25d0320', 'CSE', 75, 40);

INSERT INTO enrollments (student_roll, course_code)
SELECT student_roll, course_code
FROM (
    VALUES
        ('S-100'),
        ('3a63c6fe-18be-4110-8bfc-02f8538eaaab')
) AS students(student_roll)
CROSS JOIN (
    VALUES ('CS101'), ('CS102'), ('MA201'), ('PHY101'), ('HS101')
) AS course_list(course_code);

INSERT INTO attendance (
    student_roll, course_code, session_date,
    attendance_status, marked_at, marked_by_roll
)
SELECT
    student_roll,
    'CS101',
    session_date,
    status,
    marked_at,
    CASE
        WHEN student_roll = 'S-100' AND session_date = DATE '2026-09-20'
            THEN 'A-100'
        WHEN student_roll = 'S-100'
            THEN 'E-100'
        ELSE '271875d6-51ca-4236-9d13-3d43c25d0320'
    END
FROM (
    VALUES
        ('S-100'),
        ('3a63c6fe-18be-4110-8bfc-02f8538eaaab')
) AS students(student_roll)
CROSS JOIN (
    VALUES
        (DATE '2026-09-08', 'present', TIMESTAMPTZ '2026-09-13 14:32:02.665742+00'),
        (DATE '2026-09-10', 'present', TIMESTAMPTZ '2026-09-13 14:32:02.665742+00'),
        (DATE '2026-09-12', 'absent',  TIMESTAMPTZ '2026-09-13 14:32:02.665742+00'),
        (DATE '2026-09-15', 'present', TIMESTAMPTZ '2026-09-13 14:32:02.665742+00'),
        (DATE '2026-09-20', 'present', TIMESTAMPTZ '2026-09-13 14:36:33.624238+00'),
        (DATE '2026-09-21', 'absent',  TIMESTAMPTZ '2026-09-13 14:36:33.638692+00')
) AS sessions(session_date, status, marked_at);

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
    roll_num VARCHAR(32) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    role VARCHAR(32) NOT NULL,            -- 'student', 'faculty', 'admin', 'guest'
    student_group VARCHAR(64)             -- e.g., 'G1', 'G21' (NULL for faculty/2nd years)
);

CREATE TABLE courses (
    code VARCHAR(32) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    professor_name VARCHAR(128),
    professor_roll VARCHAR(32),           -- Links to people.roll_num
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
    ('A-001', 'Super Admin', 'admin'),
    ('F-CS01', 'Dr. CS Head', 'faculty'),
    ('F-CB01', 'Dr. CBE Head', 'faculty'),
    ('F-CE01', 'Dr. Civil Head', 'faculty'),
    ('F-MA01', 'Dr. Maths Head', 'faculty'),
    ('F-PH01', 'Dr. Physics Head', 'faculty');

INSERT INTO courses (code, name, professor_name, professor_roll, department) VALUES
    ('MA1101', 'Calculus and Linear Algebra', 'Dr. Maths Head', 'F-MA01', 'MA'),
    ('CS1101', 'Foundations of Programming', 'Dr. CS Head', 'F-CS01', 'CS'),
    ('PH1101', 'Physics', 'Dr. Physics Head', 'F-PH01', 'PH'),
    ('CE1101', 'Engineering Graphics', 'Dr. Civil Head', 'F-CE01', 'CE'),
    ('CS2101', 'Algorithms', 'Dr. CS Head', 'F-CS01', 'CS'),
    ('CS2102', 'Digital Logic', 'Dr. CS Head', 'F-CS01', 'CS'),
    ('CS2103', 'AI Concepts', 'Dr. CS Head', 'F-CS01', 'CS'),
    ('CB2101', 'Process Calculations', 'Dr. CBE Head', 'F-CB01', 'CB'),
    ('CB2102', 'Fluid Mechanics', 'Dr. CBE Head', 'F-CB01', 'CB'),
    ('CB2103', 'Chemical Engineering Thermodynamics', 'Dr. CBE Head', 'F-CB01', 'CB'),
    ('CB2105', 'Mechanical Operations', 'Dr. CBE Head', 'F-CB01', 'CB');

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
