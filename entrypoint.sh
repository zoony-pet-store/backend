#!/bin/bash
set -e

echo "Checking database connectivity..."

python - <<'PY'
import os
import sys
import time
from urllib.parse import urlsplit

import psycopg2


database_url = os.getenv("DATABASE_URL")

if not database_url:
    print(
        "ERROR: DATABASE_URL environment variable is not set.",
        file=sys.stderr,
        flush=True,
    )
    raise SystemExit(1)


# Виводимо безпечну інформацію без пароля
parsed_url = urlsplit(database_url)

print(
    "DB: "
    f"host={parsed_url.hostname} "
    f"port={parsed_url.port or 5432} "
    f"database={parsed_url.path.lstrip('/')} "
    f"user={parsed_url.username}",
    flush=True,
)


last_error = None

for attempt in range(1, 11):
    try:
        connection = psycopg2.connect(
            database_url,
            connect_timeout=5,
            sslmode="require",
        )
        connection.close()

        print("Database connection OK", flush=True)
        break

    except Exception as error:
        last_error = error

        print(
            f"Database connection attempt {attempt}/10 failed: {error}",
            flush=True,
        )

        if attempt < 10:
            time.sleep(2)

else:
    print(
        f"Database is not reachable: {last_error}",
        file=sys.stderr,
        flush=True,
    )
    raise SystemExit(1)
PY


echo "Running database migrations..."
python manage.py migrate --noinput


echo "Collecting static files..."
python manage.py collectstatic --noinput


echo "Starting Gunicorn on port ${PORT:-8080}..."

exec gunicorn pet_store.wsgi:application \
  --bind "0.0.0.0:${PORT:-8080}" \
  --workers 1 \
  --threads 4 \
  --timeout 120 \
  --graceful-timeout 30 \
  --keep-alive 5 \
  --access-logfile - \
  --error-logfile -
