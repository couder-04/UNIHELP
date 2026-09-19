#!/usr/bin/env bash
# Start UniHelp against the isolated IIT Mandi demo databases.
# Creates the mandi_* databases if they are missing.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

export ORG_PROFILE_PATH="${ORG_PROFILE_PATH:-orgs/iit_mandi.yaml}"
export UNIHELP_PORT="${UNIHELP_PORT:-8002}"
export PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-http://127.0.0.1:${UNIHELP_PORT}}"
export AUTH_DB_NAME=mandi_campus_agent
export MESS_DB_NAME=mandi_mess_menu
export ROOM_DB_NAME=mandi_room_booking
export BUS_DB_NAME=mandi_bus_schedule
export COMPLAINTS_DB_NAME=mandi_complaints
export ATTENDANCE_DB_NAME=mandi_organization_agent
export NOTICE_DB_NAME=mandi_notice_board
export TIMETABLE_DB_NAME=mandi_timetable

if ! PGPASSWORD="${PGPASSWORD:-}" psql -h "${PGHOST:-localhost}" -p "${PGPORT:-5432}" -U "${PGUSER:-postgres}" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='mandi_campus_agent'" | grep -q 1; then
  echo "mandi_* databases missing; creating them..."
  "$ROOT/.venv/bin/python" "$ROOT/scripts/create_iit_mandi_demo_db.py"
fi

echo "IIT Mandi on ${PUBLIC_BASE_URL}  profile=${ORG_PROFILE_PATH}"
echo "DBs: ${AUTH_DB_NAME} ${MESS_DB_NAME} ${BUS_DB_NAME} ${NOTICE_DB_NAME} ..."
exec "$ROOT/.venv/bin/python" "$ROOT/main.py"
