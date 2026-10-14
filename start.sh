#!/bin/bash
# Script de arranque para servicios web (Render, Heroku, Railway, etc.).
#
# Uso:
#   bash start.sh [SETTINGS_MODULE]
#
# - El módulo de settings se pasa como argumento o se toma de
#   DJANGO_SETTINGS_MODULE (por defecto: config.settings_demo).
# - Render inyecta PORT; en local se usa 8000.
# - IMPORT_FIXTURES_ON_START=true  -> importa fixtures/csv tras migrar.
# - CREATE_SUPERUSER_ON_START=true -> crea el superusuario admin por defecto.

set -e

SETTINGS_MODULE="${1:-${DJANGO_SETTINGS_MODULE:-config.settings_demo}}"
PORT="${PORT:-8000}"

# WhiteNoise sirve estáticos desde staticfiles/ y el pipeline de PDF
# espera los logos en media/logos/.
mkdir -p staticfiles media/logos
if [ -d logos ]; then
  cp -n logos/* media/logos/ 2>/dev/null || true
fi

echo "=== Running migrations ($SETTINGS_MODULE) ==="
python manage.py migrate --settings="$SETTINGS_MODULE"

if [ "${IMPORT_FIXTURES_ON_START:-false}" = "true" ]; then
  echo "=== Importing CSV fixtures ==="
  python manage.py importar_fixtures_csv --path "${FIXTURES_CSV_PATH:-fixtures/csv}" --settings="$SETTINGS_MODULE"
fi

if [ "${CREATE_SUPERUSER_ON_START:-false}" = "true" ]; then
  echo "=== Creating default superuser ==="
  python manage.py create_default_superuser --settings="$SETTINGS_MODULE" || true
fi

echo "=== Collecting static files ==="
python manage.py collectstatic --noinput --settings="$SETTINGS_MODULE"

echo "=== Starting gunicorn on 0.0.0.0:$PORT ==="
exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:$PORT" \
  --env DJANGO_SETTINGS_MODULE="$SETTINGS_MODULE" \
  --workers 2 --threads 4 --timeout 300
