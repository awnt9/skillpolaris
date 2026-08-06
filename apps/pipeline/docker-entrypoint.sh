#!/bin/sh
set -eu

ALEMBIC_INI="${ALEMBIC_INI:-apps/pipeline/alembic.ini}"
MAX_ATTEMPTS="${MIGRATE_MAX_ATTEMPTS:-60}"
SLEEP_SECONDS="${MIGRATE_RETRY_SECONDS:-2}"

echo "Applying database migrations..."
attempt=1
until uv run --package pipeline alembic -c "$ALEMBIC_INI" upgrade head; do
  if [ "$attempt" -ge "$MAX_ATTEMPTS" ]; then
    echo "Migrations failed after ${MAX_ATTEMPTS} attempts" >&2
    exit 1
  fi
  echo "Database not ready (attempt ${attempt}/${MAX_ATTEMPTS}); retrying in ${SLEEP_SECONDS}s..."
  attempt=$((attempt + 1))
  sleep "$SLEEP_SECONDS"
done
echo "Migrations applied."

exec "$@"
