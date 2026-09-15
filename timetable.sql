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
