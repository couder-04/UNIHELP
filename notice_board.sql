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
