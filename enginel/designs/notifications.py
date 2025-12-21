"""
Email notification service for Enginel.

Handles email notification creation, queuing, and delivery with:
- Template-based email generation
- Rate limiting
- Retry logic
- Batch processing
- User preference checking
"""
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.db import transaction
from designs.models import (
    CustomUser,
    EmailNotification,
    NotificationPreference,
    DesignAsset,
    ReviewSession,
    Markup,
    AnalysisJob,
    # Organization model removed - multi-tenant feature not fully implemented
)
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for creating and managing email notifications.
    """
    
    @staticmethod
    def get_or_create_preferences(user):
        """Get or create notification preferences for a user."""
        prefs, created = NotificationPreference.objects.get_or_create(
            user=user,
            defaults={
                'email_enabled': True,
                'delivery_method': 'IMMEDIATE',
            }
        )
        return prefs
    
    @staticmethod
    def should_send_notification(user, notification_type):
        """
        Check if notification should be sent based on user preferences.
        
        Args:
            user: CustomUser instance
            notification_type: String like 'DESIGN_UPLOADED'
        
        Returns:
            Boolean indicating whether to send notification
        """
        if not settings.NOTIFICATIONS_ENABLED:
            return False
        
        prefs = NotificationService.get_or_create_preferences(user)
        
        # Check master email enabled
        if not prefs.email_enabled:
            return False
        
        # Check quiet hours
        if prefs.is_in_quiet_hours():
            logger.info(f"Notification for {user.username} skipped due to quiet hours")
            return False
        
        # Check specific notification type preference
        type_mapping = {
            'DESIGN_UPLOADED': 'notify_design_uploaded',
            'DESIGN_APPROVED': 'notify_design_approved',
            'DESIGN_REJECTED': 'notify_design_rejected',
            'REVIEW_STARTED': 'notify_review_started',
            'REVIEW_COMPLETED': 'notify_review_completed',
            'MARKUP_ADDED': 'notify_markup_added',
            'JOB_COMPLETED': 'notify_job_completed',
            'JOB_FAILED': 'notify_job_failed',
            # Organization features disabled - model removed
            # 'ORGANIZATION_INVITE': 'notify_organization_invite',
            # 'ROLE_CHANGED': 'notify_role_changed',
        }
        
        pref_field = type_mapping.get(notification_type)
        if pref_field:
            return getattr(prefs, pref_field, True)
        
        # Default to True for unknown types
        return True
    
    @staticmethod
    def check_rate_limit(user):
        """
        Check if user has exceeded email rate limit.
        
        Args:
            user: CustomUser instance
        
        Returns:
            Boolean indicating whether user can receive more emails
        """
        window_start = timezone.now() - timezone.timedelta(seconds=settings.EMAIL_RATE_LIMIT_WINDOW)
        
        recent_count = EmailNotification.objects.filter(
            recipient=user,
            queued_at__gte=window_start,
            status__in=['SENT', 'SENDING', 'QUEUED']
        ).count()
        
        return recent_count < settings.EMAIL_RATE_LIMIT_PER_USER
    
    @staticmethod
    def create_notification(
        recipient,
        notification_type,
        subject,
        message_plain,
        message_html='',
        context_data=None,
        priority='NORMAL'
    ):
        """
        Create a new email notification.
        
        Args:
            recipient: CustomUser instance
            notification_type: String from EmailNotification.NOTIFICATION_TYPES
            subject: Email subject line
            message_plain: Plain text email body
            message_html: HTML email body (optional)
            context_data: Dict of additional context for templates
            priority: Priority level (LOW, NORMAL, HIGH, URGENT)
        
        Returns:
            EmailNotification instance or None if not sent
        """
        # Check if notification should be sent
        if not NotificationService.should_send_notification(recipient, notification_type):
            logger.info(f"Notification {notification_type} for {recipient.username} blocked by preferences")
            return None
        
        # Check rate limit
        if not NotificationService.check_rate_limit(recipient):
            logger.warning(f"Rate limit exceeded for {recipient.username}")
            return None
        
        # Create notification
        notification = EmailNotification.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            subject=subject,
            message_plain=message_plain,
            message_html=message_html,
            context_data=context_data or {},
            priority=priority,
            status='PENDING',
            rate_limit_key=f"user:{recipient.id}:hour"
        )
        
        logger.info(f"Created notification {notification.id} for {recipient.email}")
        return notification
    
    # Convenience methods for common notification types
    
    @staticmethod
    def notify_design_uploaded(design_asset, followers=None):
        """
        Notify users when a new design is uploaded.
        
        Args:
            design_asset: DesignAsset instance
            followers: List of CustomUser instances to notify (optional)
        """
        if followers is None:
            # Organization feature disabled - just notify uploader for now
            # In future, could notify based on series followers or project members
            followers = []
        
        for user in followers:
            subject = f"New design uploaded: {design_asset.series.part_number}"
            message = f"""
Hello {user.first_name or user.username},

A new design has been uploaded to the series you're following:

Part Number: {design_asset.series.part_number}
Series: {design_asset.series.name}
Filename: {design_asset.filename}
Version: {design_asset.version_number}
Uploaded by: {design_asset.uploaded_by.username}

View the design: {settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost:8000'}/designs/{design_asset.id}/

Best regards,
The Enginel Team
            """.strip()
            
            NotificationService.create_notification(
                recipient=user,
                notification_type='DESIGN_UPLOADED',
                subject=subject,
                message_plain=message,
                context_data={
                    'design_id': str(design_asset.id),
                    'part_number': design_asset.series.part_number,
                    'filename': design_asset.filename,
                    'uploader': design_asset.uploaded_by.username,
                }
            )
    
    @staticmethod
    def notify_design_approved(design_asset):
        """Notify design owner when their design is approved."""
        user = design_asset.uploaded_by
        subject = f"Design approved: {design_asset.series.part_number}"
        message = f"""
Hello {user.first_name or user.username},

Your design has been approved:

Part Number: {design_asset.series.part_number}
Filename: {design_asset.filename}
Version: {design_asset.version_number}

Congratulations! Your design is ready for production.

Best regards,
The Enginel Team
        """.strip()
        
        return NotificationService.create_notification(
            recipient=user,
            notification_type='DESIGN_APPROVED',
            subject=subject,
            message_plain=message,
            context_data={'design_id': str(design_asset.id)},
            priority='HIGH'
        )
    
    @staticmethod
    def notify_design_rejected(design_asset, reason=''):
        """Notify design owner when their design is rejected."""
        user = design_asset.uploaded_by
        subject = f"Design rejected: {design_asset.series.part_number}"
        message = f"""
Hello {user.first_name or user.username},

Your design has been rejected:

Part Number: {design_asset.series.part_number}
Filename: {design_asset.filename}
Version: {design_asset.version_number}
Reason: {reason or 'No reason provided'}

Please review the feedback and resubmit when ready.

Best regards,
The Enginel Team
        """.strip()
        
        return NotificationService.create_notification(
            recipient=user,
            notification_type='DESIGN_REJECTED',
            subject=subject,
            message_plain=message,
            context_data={'design_id': str(design_asset.id), 'reason': reason},
            priority='HIGH'
        )
    
    @staticmethod
    def notify_review_started(review_session):
        """Notify design owner when a review session is started."""
        design = review_session.design_asset
        user = design.uploaded_by
        subject = f"Review started: {design.series.part_number}"
        message = f"""
Hello {user.first_name or user.username},

A review session has been started on your design:

Part Number: {design.series.part_number}
Filename: {design.filename}
Reviewer: {review_session.reviewer.username}
Status: {review_session.status}

You can track the review progress in the Enginel dashboard.

Best regards,
The Enginel Team
        """.strip()
        
        return NotificationService.create_notification(
            recipient=user,
            notification_type='REVIEW_STARTED',
            subject=subject,
            message_plain=message,
            context_data={
                'review_id': str(review_session.id),
                'design_id': str(design.id),
                'reviewer': review_session.reviewer.username,
            }
        )
    
    @staticmethod
    def notify_review_completed(review_session):
        """Notify design owner when a review session is completed."""
        design = review_session.design_asset
        user = design.uploaded_by
        subject = f"Review completed: {design.series.part_number}"
        message = f"""
Hello {user.first_name or user.username},

The review of your design has been completed:

Part Number: {design.series.part_number}
Filename: {design.filename}
Reviewer: {review_session.reviewer.username}
Status: {review_session.status}
Comments: {len(review_session.comments.all())} comments

Check the review details for feedback and next steps.

Best regards,
The Enginel Team
        """.strip()
        
        return NotificationService.create_notification(
            recipient=user,
            notification_type='REVIEW_COMPLETED',
            subject=subject,
            message_plain=message,
            context_data={
                'review_id': str(review_session.id),
                'design_id': str(design.id),
                'status': review_session.status,
            },
            priority='HIGH'
        )
    
    @staticmethod
    def notify_markup_added(markup):
        """Notify design owner when someone adds a markup."""
        design = markup.design_asset
        user = design.uploaded_by
        
        # Don't notify if user added their own markup
        if markup.author.id == user.id:
            return None
        
        subject = f"New comment on your design: {design.series.part_number}"
        message = f"""
Hello {user.first_name or user.username},

{markup.author.username} added a comment to your design:

Part Number: {design.series.part_number}
Filename: {design.filename}
Comment: {markup.content[:200]}{'...' if len(markup.content) > 200 else ''}

View the comment in the Enginel dashboard.

Best regards,
The Enginel Team
        """.strip()
        
        return NotificationService.create_notification(
            recipient=user,
            notification_type='MARKUP_ADDED',
            subject=subject,
            message_plain=message,
            context_data={
                'markup_id': str(markup.id),
                'design_id': str(design.id),
                'author': markup.author.username,
            }
        )
    
    @staticmethod
    def notify_job_completed(job):
        """Notify user when their background job completes."""
        if not job.design_asset or not job.design_asset.uploaded_by:
            return None
        
        user = job.design_asset.uploaded_by
        subject = f"Processing complete: {job.job_type}"
        
        # Calculate duration if available
        duration = job.get_duration()
        duration_text = f"\nDuration: {duration:.1f} seconds" if duration else ""
        
        message = f"""
Hello {user.first_name or user.username},

Your background processing job has completed successfully:

Job Type: {job.job_type}
Design: {job.design_asset.filename}{duration_text}

The results are now available in your design dashboard.

Best regards,
The Enginel Team
        """.strip()
        
        return NotificationService.create_notification(
            recipient=user,
            notification_type='JOB_COMPLETED',
            subject=subject,
            message_plain=message,
            context_data={
                'job_id': str(job.id),
                'job_type': job.job_type,
                'design_id': str(job.design_asset.id),
            }
        )
    
    @staticmethod
    def notify_job_failed(job):
        """Notify user when their background job fails."""
        if not job.design_asset or not job.design_asset.uploaded_by:
            return None
        
        user = job.design_asset.uploaded_by
        subject = f"Processing failed: {job.job_type}"
        message = f"""
Hello {user.first_name or user.username},

Unfortunately, your background processing job has failed:

Job Type: {job.job_type}
Design: {job.design_asset.filename}
Error: {job.error_message[:200] if job.error_message else 'Unknown error'}

Our team has been notified and is investigating the issue. We'll get back to you soon.

Best regards,
The Enginel Team
        """.strip()
        
        return NotificationService.create_notification(
            recipient=user,
            notification_type='JOB_FAILED',
            subject=subject,
            message_plain=message,
            context_data={
                'job_id': str(job.id),
                'job_type': job.job_type,
                'error': job.error_message,
            },
            priority='HIGH'
        )
    
    # Organization invite feature disabled - Organization model removed
    # Organization invite feature disabled - Organization model removed
    # @staticmethod
    # def notify_organization_invite(user, organization, inviter, role='MEMBER'):
    #     """Notify user when invited to join an organization."""
    #     pass
    
    # Organization role change feature disabled - Organization model removed
    # @staticmethod  
    # def notify_role_changed(user, organization, old_role, new_role, changed_by):
    #     """Notify user when their role in an organization changes."""
    #     pass


class EmailSender:
    """
    Handles actual email sending with Django's email backend.
    """
    
    @staticmethod
    def send_notification(notification):
        """
        Send an email notification.
        
        Args:
            notification: EmailNotification instance
        
        Returns:
            Boolean indicating success
        """
        try:
            notification.status = 'SENDING'
            notification.save(update_fields=['status'])
            
            # Create email message
            email = EmailMultiAlternatives(
                subject=notification.subject,
                body=notification.message_plain,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[notification.recipient.email],
            )
            
            # Add HTML alternative if provided
            if notification.message_html:
                email.attach_alternative(notification.message_html, "text/html")
            
            # Send email
            email.send(fail_silently=False)
            
            # Mark as sent
            notification.mark_sent()
            logger.info(f"Successfully sent notification {notification.id} to {notification.recipient.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send notification {notification.id}: {str(e)}")
            notification.mark_failed(str(e))
            return False
    
    @staticmethod
    def send_batch(notifications):
        """
        Send a batch of notifications.
        
        Args:
            notifications: QuerySet or list of EmailNotification instances
        
        Returns:
            Dict with success/failure counts
        """
        results = {'sent': 0, 'failed': 0}
        
        for notification in notifications:
            if EmailSender.send_notification(notification):
                results['sent'] += 1
            else:
                results['failed'] += 1
        
        return results
