#!/bin/sh
set -eu

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
    echo "Running database migrations because RUN_MIGRATIONS=1."
    python manage.py migrate --noinput
else
    echo "Skipping database migrations. Set RUN_MIGRATIONS=1 for an explicit migration run."
fi

echo "Collecting static files."
python manage.py collectstatic --noinput

exec "$@"
