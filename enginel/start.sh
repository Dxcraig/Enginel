#!/usr/bin/env bash
# Start script for Render web service

set -o errexit  # Exit on error

echo "Starting Gunicorn server..."
exec gunicorn enginel.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 4 \
    --threads 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
