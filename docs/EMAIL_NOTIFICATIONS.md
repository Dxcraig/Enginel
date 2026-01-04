# Email Notifications

Comprehensive email notification system for Enginel with user preferences, rate limiting, retry logic, and automated triggers.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Configuration](#configuration)
- [Notification Types](#notification-types)
- [User Preferences](#user-preferences)
- [API Endpoints](#api-endpoints)
- [Automated Triggers](#automated-triggers)
- [Email Templates](#email-templates)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

## Overview

The email notification system provides:

- **Automated notifications** for design lifecycle events (upload, approval, review)
- **User preference management** with granular per-notification-type controls
- **Rate limiting** to prevent email overload (100 emails per user per hour)
- **Retry logic** with exponential backoff (up to 3 retries)
- **Batch processing** for digest emails (hourly, daily, weekly)
- **Quiet hours** support to suppress notifications during off-hours
- **Priority queuing** for urgent notifications (LOW, NORMAL, HIGH, URGENT)

## Features

### Notification Management

- **Multi-channel support**: Email (with SMS/push notification extensibility)
- **Template-based emails**: Plain text and HTML versions
- **Delivery preferences**: Immediate, hourly digest, daily digest, weekly digest
- **Priority levels**: LOW, NORMAL, HIGH, URGENT
- **Status tracking**: PENDING, QUEUED, SENDING, SENT, FAILED, CANCELLED

### User Controls

- **Master email toggle**: Enable/disable all notifications
- **Per-type preferences**: Control each notification type individually
- **Quiet hours**: Suppress notifications during specified times
- **Delivery method**: Choose between immediate or digest emails

### System Features

- **Rate limiting**: 100 emails per user per hour (configurable)
- **Automatic retries**: Up to 3 retries with exponential backoff
- **Background processing**: Celery tasks for async email delivery
- **Periodic cleanup**: Auto-delete old sent notifications
- **Audit trail**: Complete notification history

## Configuration

### Environment Variables

Add to `.env`:

```bash
# Email Backend (console for dev, smtp for prod)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@enginel.example.com

# Notification Settings
NOTIFICATIONS_ENABLED=True
NOTIFICATION_BATCH_SIZE=50
NOTIFICATION_RETRY_DELAY=300
NOTIFICATION_MAX_RETRIES=3

# Rate Limiting
EMAIL_RATE_LIMIT_PER_USER=100
EMAIL_RATE_LIMIT_WINDOW=3600
```

### Production Email Setup

#### Gmail

```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-specific-password
```

**Note**: Enable 2FA on Gmail and generate an App Password.

#### AWS SES

```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=email-smtp.us-east-1.amazonaws.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-ses-smtp-username
EMAIL_HOST_PASSWORD=your-ses-smtp-password
```

#### SendGrid

```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your-sendgrid-api-key
```

## Notification Types

| Type | Description | Default Enabled | Priority |
|------|-------------|----------------|----------|
| `DESIGN_UPLOADED` | New design uploaded to series | ✅ | NORMAL |
| `DESIGN_APPROVED` | Design approved by reviewer | ✅ | HIGH |
| `DESIGN_REJECTED` | Design rejected by reviewer | ✅ | HIGH |
| `REVIEW_STARTED` | Review session started | ✅ | NORMAL |
| `REVIEW_COMPLETED` | Review session completed | ✅ | HIGH |
| `MARKUP_ADDED` | Comment added to design | ✅ | NORMAL |
| `JOB_COMPLETED` | Background job completed | ✅ | NORMAL |
| `JOB_FAILED` | Background job failed | ✅ | HIGH |
| `ORGANIZATION_INVITE` | Invited to organization | ✅ | HIGH |
| `ROLE_CHANGED` | Role in organization changed | ✅ | HIGH |
| `PASSWORD_RESET` | Password reset requested | ✅ | URGENT |
| `ACCOUNT_ACTIVATED` | Account activated | ✅ | NORMAL |
| `SECURITY_ALERT` | Security event detected | ✅ | URGENT |

## User Preferences

### API Management

#### Get Preferences

```bash
GET /api/notifications/preferences/
Authorization: Token <token>
```

Response:
```json
{
  "user": 3,
  "email_enabled": true,
  "notify_design_uploaded": true,
  "notify_design_approved": true,
  "delivery_method": "IMMEDIATE",
  "quiet_hours_enabled": false,
  "quiet_hours_start": null,
  "quiet_hours_end": null
}
```

#### Update Preferences

```bash
PATCH /api/notifications/preferences/
Authorization: Token <token>
Content-Type: application/json

{
  "email_enabled": true,
  "delivery_method": "HOURLY",
  "quiet_hours_enabled": true,
  "quiet_hours_start": "22:00:00",
  "quiet_hours_end": "08:00:00",
  "notify_design_uploaded": false
}
```

### Delivery Methods

- **IMMEDIATE**: Send emails immediately (default)
- **HOURLY**: Bundle notifications into hourly digest
- **DAILY**: Send one email per day
- **WEEKLY**: Send one email per week

### Quiet Hours

Configure times when notifications should be suppressed:

```json
{
  "quiet_hours_enabled": true,
  "quiet_hours_start": "22:00:00",
  "quiet_hours_end": "08:00:00"
}
```

**Note**: Quiet hours use UTC timezone.

## API Endpoints

### Notification Management

#### Get Notification History

```bash
GET /api/notifications/history/
Authorization: Token <token>

Query Parameters:
- status: Filter by status (PENDING, SENT, FAILED)
- type: Filter by notification type
- page: Page number (default: 1)
- page_size: Items per page (default: 50)
```

Response:
```json
{
  "count": 10,
  "next": "http://localhost:8000/api/notifications/history/?page=2",
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "notification_type": "DESIGN_UPLOADED",
      "subject": "New design uploaded",
      "status": "SENT",
      "queued_at": "2025-12-16T12:00:00Z",
      "sent_at": "2025-12-16T12:00:05Z",
      "recipient_email": "user@example.com"
    }
  ]
}
```

#### Get Notification Statistics

```bash
GET /api/notifications/stats/
Authorization: Token <token>
```

Response:
```json
{
  "by_status": {
    "SENT": 45,
    "PENDING": 3,
    "FAILED": 2
  },
  "by_type": {
    "DESIGN_UPLOADED": 20,
    "DESIGN_APPROVED": 15,
    "JOB_COMPLETED": 10
  },
  "pending_count": 3
}
```

#### Send Test Notification

```bash
POST /api/notifications/test/
Authorization: Token <token>
```

Response:
```json
{
  "message": "Test notification queued successfully",
  "notification_id": "uuid",
  "recipient": "user@example.com"
}
```

## Automated Triggers

Notifications are automatically triggered by system events via Django signals:

### Design Events

```python
# Design uploaded
design = DesignAsset.objects.create(...)
# → Notifies organization members

# Design approved
design.status = 'APPROVED'
design.save()
# → Notifies design owner

# Design rejected
design.status = 'REJECTED'
design.save()
# → Notifies design owner
```

### Review Events

```python
# Review started
review = ReviewSession.objects.create(...)
# → Notifies design owner

# Review completed
review.status = 'APPROVED'
review.save()
# → Notifies design owner
```

### Comment Events

```python
# Markup added
markup = Markup.objects.create(...)
# → Notifies design owner (if different from author)
```

### Job Events

```python
# Job completed
job.status = 'SUCCESS'
job.save()
# → Notifies job owner

# Job failed
job.status = 'FAILURE'
job.save()
# → Notifies job owner with error details
```

## Email Templates

### Template Structure

Emails consist of:
- **Subject**: Short, descriptive title
- **Plain text body**: Accessible, no-HTML version
- **HTML body**: Formatted version (optional, future enhancement)

### Example Template

```python
subject = f"Design approved: {design.series.part_number}"
message = f"""
Hello {user.first_name or user.username},

Your design has been approved:

Part Number: {design.series.part_number}
Filename: {design.filename}
Version: {design.version_number}

Congratulations! Your design is ready for production.

Best regards,
The Enginel Team
"""
```

### Customization

Templates are defined in `designs/notifications.py` in the `NotificationService` class. Each notification type has a dedicated method:

- `notify_design_uploaded()`
- `notify_design_approved()`
- `notify_design_rejected()`
- `notify_review_started()`
- `notify_review_completed()`
- `notify_markup_added()`
- `notify_job_completed()`
- `notify_job_failed()`
- `notify_organization_invite()`
- `notify_role_changed()`

## Testing

### Development Testing

With console backend (default), emails appear in terminal:

```bash
docker-compose logs -f celery_worker
```

### Send Test Email

```bash
curl -X POST http://localhost:8000/api/notifications/test/ \
  -H "Authorization: Token <your-token>" \
  -H "Content-Type: application/json"
```

### Manual Notification Creation

```python
from designs.notifications import NotificationService
from designs.models import CustomUser

user = CustomUser.objects.get(username='testuser')

NotificationService.create_notification(
    recipient=user,
    notification_type='SECURITY_ALERT',
    subject='Test Notification',
    message_plain='This is a test message',
    priority='HIGH'
)
```

### Check Processing

```bash
# View notification history
curl -H "Authorization: Token <token>" \
  http://localhost:8000/api/notifications/history/

# Check stats
curl -H "Authorization: Token <token>" \
  http://localhost:8000/api/notifications/stats/
```

## Troubleshooting

### Emails Not Sending

**Check backend configuration:**
```bash
docker-compose exec web python manage.py shell
>>> from django.conf import settings
>>> print(settings.EMAIL_BACKEND)
>>> print(settings.NOTIFICATIONS_ENABLED)
```

**Check Celery workers:**
```bash
docker-compose logs celery_worker
docker-compose logs celery_beat
```

**Check pending notifications:**
```python
from designs.models import EmailNotification
print(EmailNotification.objects.filter(status='PENDING').count())
```

### Rate Limiting Issues

**Check rate limit:**
```bash
docker-compose exec web python manage.py shell
>>> from django.conf import settings
>>> print(settings.EMAIL_RATE_LIMIT_PER_USER)
>>> print(settings.EMAIL_RATE_LIMIT_WINDOW)
```

**Check recent emails:**
```python
from designs.models import EmailNotification
from django.utils import timezone
from datetime import timedelta

recent = EmailNotification.objects.filter(
    queued_at__gte=timezone.now() - timedelta(hours=1)
).count()
print(f"Emails sent in last hour: {recent}")
```

### Failed Notifications

**View failed notifications:**
```python
from designs.models import EmailNotification
failed = EmailNotification.objects.filter(status='FAILED')
for notif in failed:
    print(f"{notif.id}: {notif.error_message}")
```

**Retry failed notifications:**
```python
failed = EmailNotification.objects.filter(status='FAILED')
failed.update(status='PENDING', next_retry_at=None, retry_count=0)
```

### Quiet Hours Not Working

**Check user preferences:**
```python
from designs.models import NotificationPreference
prefs = NotificationPreference.objects.get(user__username='testuser')
print(f"Enabled: {prefs.quiet_hours_enabled}")
print(f"Start: {prefs.quiet_hours_start}")
print(f"End: {prefs.quiet_hours_end}")
```

**Test quiet hours logic:**
```python
print(prefs.is_in_quiet_hours())
```

## Celery Periodic Tasks

The system includes automatic background processing:

### Task Schedule

- **process_pending_notifications**: Every 5 minutes
  - Processes pending notifications in batches
  - Respects rate limits and quiet hours

- **send_digest_notifications**: Every hour
  - Sends digest emails for users with HOURLY delivery method
  - Bundles multiple notifications into single email

- **cleanup_old_notifications**: Daily at 2 AM
  - Removes sent/cancelled notifications older than 30 days
  - Keeps database clean

### Manual Task Execution

```python
from designs.tasks import process_pending_notifications

# Execute immediately
result = process_pending_notifications.delay()

# Check result
print(result.get())
```

## Admin Interface

### View Notifications

Django admin at `/admin/designs/emailnotification/`:

- **List view**: Filter by status, type, priority
- **Detail view**: Full notification details
- **Actions**: Mark as sent, cancel, retry failed

### View Preferences

Django admin at `/admin/designs/notificationpreference/`:

- **List view**: All user preferences
- **Edit**: Modify user notification settings

## Best Practices

### For Developers

1. **Use appropriate priority levels**:
   - URGENT: Security, password resets
   - HIGH: Approvals, rejections, role changes
   - NORMAL: Uploads, comments, job completions
   - LOW: Non-critical updates

2. **Keep messages concise**:
   - Clear subject lines
   - Actionable content
   - Include relevant links

3. **Respect user preferences**:
   - Always check `should_send_notification()`
   - Honor quiet hours
   - Respect rate limits

4. **Handle failures gracefully**:
   - Use try-except blocks
   - Log errors appropriately
   - Let retry logic work

### For System Administrators

1. **Monitor email delivery**:
   - Check Celery logs regularly
   - Watch for failed notifications
   - Track bounce rates

2. **Tune rate limits**:
   - Adjust based on user feedback
   - Monitor email provider limits
   - Scale with user growth

3. **Optimize performance**:
   - Use batch processing
   - Clean up old notifications
   - Index notification queries

4. **Security considerations**:
   - Use TLS for SMTP
   - Secure email credentials
   - Validate recipient addresses
   - Monitor for spam abuse

## Future Enhancements

Planned improvements:

- [ ] HTML email templates with branding
- [ ] SMS notifications via Twilio
- [ ] Push notifications (web/mobile)
- [ ] In-app notification center
- [ ] Advanced templating with Jinja2
- [ ] A/B testing for email content
- [ ] Notification analytics dashboard
- [ ] Webhook notifications
- [ ] Slack/Teams integration
- [ ] Email preview before sending

## Support

For issues or questions:

1. Check logs: `docker-compose logs celery_worker`
2. Review [Troubleshooting](#troubleshooting) section
3. Test with `/api/notifications/test/` endpoint
4. Contact support with notification ID and error details
