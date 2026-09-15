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
