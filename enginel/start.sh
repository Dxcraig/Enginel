#!/bin/sh
set -e

echo "Running migrations..."
python manage.py migrate --noinput

echo "Creating superuser..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model
import os

User = get_user_model()
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin')

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f'Superuser "{username}" created successfully!')
else:
    print(f'Superuser "{username}" already exists.')
EOF

echo "Starting Gunicorn..."
exec gunicorn enginel.wsgi --bind 0.0.0.0:${PORT:-8000} --workers 4
