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

COMMIT;
