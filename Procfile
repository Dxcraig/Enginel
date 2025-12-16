web: python manage.py migrate && gunicorn enginel.wsgi:application --bind 0.0.0.0:$PORT --workers 4 --timeout 120
worker: celery -A enginel worker --loglevel=info --concurrency=2
beat: celery -A enginel beat --loglevel=info --schedule=/tmp/celerybeat-schedule
