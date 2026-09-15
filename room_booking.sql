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
