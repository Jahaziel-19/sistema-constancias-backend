release: python manage.py migrate --settings=config.settings_demo && python manage.py collectstatic --noinput --settings=config.settings_demo
web: gunicorn config.wsgi:application --bind 0.0.0.0:8000
