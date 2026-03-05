#!/bin/bash
set -e

echo "Checking DB connectivity..."

python - <<'PY'
import os, sys, time
import psycopg2

host=os.getenv("DB_HOST")
port=os.getenv("DB_PORT","5432")
name=os.getenv("DB_NAME")
user=os.getenv("DB_USER")
pwd=os.getenv("DB_PASSWORD")
sslmode=os.getenv("DB_SSL_MODE","prefer")

print(f"DB: host={host} port={port} db={name} user={user} sslmode={sslmode}", flush=True)

last_err=None
for i in range(1, 11):
    try:
        conn = psycopg2.connect(
            host=host, port=port, dbname=name, user=user, password=pwd,
            connect_timeout=5,
            sslmode=sslmode,
        )
        conn.close()
        print("DB connection OK", flush=True)
        sys.exit(0)
    except Exception as e:
        last_err = e
        print(f"DB connect attempt {i}/10 failed: {e}", flush=True)
        time.sleep(2)

print("DB is NOT reachable, exiting.", flush=True)
raise SystemExit(1)
PY

echo "Running migrations..."
python manage.py migrate --noinput

echo "Starting gunicorn..."
exec gunicorn pet_store.wsgi:application \
  --bind 0.0.0.0:8080 \
  --workers 1 \
  --threads 4 \
  --timeout 120 \
  --graceful-timeout 30 \
  --keep-alive 5 \
  --access-logfile - \
  --error-logfile -
