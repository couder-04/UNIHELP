#!/usr/bin/env bash
# Restore the full UniHelp databases into a local PostgreSQL cluster.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
export PGHOST="${PGHOST:-localhost}"
export PGPORT="${PGPORT:-5432}"
export PGUSER="${PGUSER:-postgres}"
psql -d postgres -v ON_ERROR_STOP=1 -f "$DIR/unihelp_full.sql"
echo "Restore complete."
