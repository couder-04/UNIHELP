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
