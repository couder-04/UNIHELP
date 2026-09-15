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
