"""
Celery configuration for Enginel.

Sets up Celery for asynchronous task processing.
"""
import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'enginel.settings')

# Create Celery app
app = Celery('enginel')

# Load config from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# Periodic task schedule
app.conf.beat_schedule = {
    'process-pending-notifications': {
        'task': 'designs.tasks.process_pending_notifications',
        'schedule': 300.0,  # Every 5 minutes
    },
    'send-digest-notifications': {
        'task': 'designs.tasks.send_digest_notifications',
        'schedule': crontab(minute=0),  # Every hour
    },
    'cleanup-old-notifications': {
        'task': 'designs.tasks.cleanup_old_notifications',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    print(f'Request: {self.request!r}')
