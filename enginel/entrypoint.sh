#!/bin/sh

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Creating superuser if needed..."
python manage.py ensure_superuser

# Detect if we're running on Railway or other production environment
if [ -n "$RAILWAY_ENVIRONMENT" ] || [ "$DJANGO_ENV" = "production" ]; then
    echo "Starting production server with Gunicorn..."
    exec gunicorn enginel.wsgi:application \
        --bind [::]:${PORT:-8000} \
        --workers ${GUNICORN_WORKERS:-4} \
        --threads ${GUNICORN_THREADS:-2} \
        --timeout 120 \
        --access-logfile - \
        --error-logfile - \
        --log-level info
else
    echo "Starting development server..."
    exec python manage.py runserver 0.0.0.0:8000
fi