#!/bin/sh
set -e

# --- Parse DATABASE_URL without overwriting "$@" ---
if [ -n "$DATABASE_URL" ]; then
  DB_HOST=$(python - <<'PY'
import os
from urllib.parse import urlparse
p = urlparse(os.environ["DATABASE_URL"])
print(p.hostname or "db")
PY
)
  DB_PORT=$(python - <<'PY'
import os
from urllib.parse import urlparse
p = urlparse(os.environ["DATABASE_URL"])
print(p.port or 5432)
PY
)
  DB_USER=$(python - <<'PY'
import os
from urllib.parse import urlparse
p = urlparse(os.environ["DATABASE_URL"])
print(p.username or "loyalty")
PY
)
else
  DB_HOST="${DB_HOST:-db}"
  DB_PORT="${DB_PORT:-5432}"
  DB_USER="${DB_USER:-loyalty}"
fi

echo "DB target: ${DB_HOST}:${DB_PORT} (user=${DB_USER})"

# --- Wait for Postgres to be ready ---
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" >/dev/null 2>&1; do
  echo "Waiting for Postgres at $DB_HOST:$DB_PORT..."
  sleep 1
done

# --- Apply migrations ---
python manage.py migrate

# --- Seed demo tenant ---
if [ "${SEED_DEMO:-0}" = "1" ]; then
  python manage.py seed_demo
fi

# --- Default command if none provided ---
if [ "$#" -eq 0 ]; then
  set -- python manage.py runserver 0.0.0.0:8000
fi

echo "Starting: $*"
exec "$@"
