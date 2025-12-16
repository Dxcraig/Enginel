#!/bin/sh

echo "Waiting for postgres..."
while ! nc -z ${DB_HOST:-db} ${DB_PORT:-5432}; do
  sleep 0.1
done
echo "PostgreSQL started"

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Running migrations..."
python manage.py migrate

echo "Starting server..."
# Use Gunicorn in production, Django runserver in development
if [ "$RAILWAY_ENVIRONMENT" ]; then
    echo "Starting Gunicorn on port ${PORT:-8000}..."
    gunicorn enginel.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${GUNICORN_WORKERS:-4} --timeout ${GUNICORN_TIMEOUT:-120} --log-level info
else
    echo "Starting Django development server..."
    python manage.py runserver 0.0.0.0:8000
fi
