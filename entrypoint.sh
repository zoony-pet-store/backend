#!/bin/bash
set -e

python manage.py migrate --noinput
exec gunicorn pet_store.wsgi:application --bind 0.0.0.0:8080 --workers 2 --timeout 90
