#!/bin/bash
set -e

echo "=== Running migrations ==="
python manage.py migrate --settings=config.settings_demo

echo "=== Collecting static files ==="
python manage.py collectstatic --noinput --settings=config.settings_demo

echo "=== Starting gunicorn ==="
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000
