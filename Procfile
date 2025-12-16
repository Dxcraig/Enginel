# Railway Procfile
# Defines the commands to run for each service

# Web service (Django app)
web: cd enginel && gunicorn enginel.wsgi:application --bind 0.0.0.0:$PORT --workers 4 --threads 2 --timeout 120 --access-logfile - --error-logfile -

# Celery worker service
worker: cd enginel && celery -A enginel worker -l info --concurrency=4

# Celery beat service (scheduled tasks)
beat: cd enginel && celery -A enginel beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
