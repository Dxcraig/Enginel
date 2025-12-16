"""
Django signals for automatic cache invalidation and email notifications.

Listens for model save/delete events and:
- Invalidates related caches
- Triggers email notifications for important events
"""
from django.db.models.signals import post_save, post_delete, m2m_changed, pre_save
from django.dispatch import receiver
from designs.models import (
    Organization, CustomUser, DesignSeries, DesignAsset,
    AssemblyNode, AnalysisJob, ReviewSession, Markup, AuditLog
)
from designs.cache import invalidate_model_cache, CacheManager, CacheKey
import logging

logger = logging.getLogger(__name__)


@receiver([post_save, post_delete], sender=Organization)
def invalidate_organization_cache(sender, instance, **kwargs):
    """Invalidate organization caches on save/delete."""
    invalidate_model_cache(instance, instance.id)
    
    # Also invalidate members cache
    cache_manager = CacheManager('default')
    cache_manager.delete(CacheKey.org_members(str(instance.id)))
    cache_manager.delete(CacheKey.org_storage(str(instance.id)))
    
    logger.debug(f"Invalidated cache for organization {instance.id}")


@receiver([post_save, post_delete], sender=CustomUser)
def invalidate_user_cache(sender, instance, **kwargs):
    """Invalidate user caches on save/delete."""
    invalidate_model_cache(instance, instance.id)
    
    # Invalidate user's organizations cache
    cache_manager = CacheManager('default')
    cache_manager.delete(CacheKey.user_organizations(instance.id))
    
    # Invalidate permissions cache for all user's organizations
    for membership in instance.organization_memberships.all():
        cache_manager.delete(CacheKey.user_permissions(
            instance.id, 
            str(membership.organization_id)
        ))
    
    logger.debug(f"Invalidated cache for user {instance.id}")


@receiver([post_save, post_delete], sender=DesignSeries)
def invalidate_series_cache(sender, instance, **kwargs):
    """Invalidate design series caches on save/delete."""
    invalidate_model_cache(instance, instance.id)
    
    # Invalidate series versions list
    cache_manager = CacheManager('default')
    cache_manager.delete(CacheKey.series_versions(str(instance.id)))
    
    # Invalidate organization's design list caches
    cache_manager.delete_pattern(f"design:list:org={instance.organization_id}:*")
    
    logger.debug(f"Invalidated cache for design series {instance.id}")


@receiver([post_save, post_delete], sender=DesignAsset)
def invalidate_design_cache(sender, instance, **kwargs):
    """Invalidate design asset caches on save/delete."""
    invalidate_model_cache(instance, instance.id)
    
    cache_manager = CacheManager('default')
    longterm_manager = CacheManager('longterm')
    
    # Invalidate specific design caches
    cache_manager.delete(CacheKey.design_detail(str(instance.id)))
    cache_manager.delete(CacheKey.design_bom(str(instance.id)))
    longterm_manager.delete(CacheKey.design_metadata(str(instance.id)))
    
    # Invalidate series caches
    if instance.series:
        cache_manager.delete(CacheKey.series_detail(str(instance.series_id)))
        cache_manager.delete(CacheKey.series_versions(str(instance.series_id)))
        
        # Invalidate organization's design list caches
        cache_manager.delete_pattern(f"design:list:org={instance.series.organization_id}:*")
        
        # Invalidate organization storage cache
        cache_manager.delete(CacheKey.org_storage(str(instance.series.organization_id)))
    
    logger.debug(f"Invalidated cache for design asset {instance.id}")


@receiver([post_save, post_delete], sender=AssemblyNode)
def invalidate_bom_cache(sender, instance, **kwargs):
    """Invalidate BOM caches when assembly nodes change."""
    if instance.design_asset:
        cache_manager = CacheManager('default')
        longterm_manager = CacheManager('longterm')
        
        # Invalidate BOM tree cache
        cache_manager.delete(CacheKey.design_bom(str(instance.design_asset_id)))
        
        # Invalidate design metadata (contains BOM info)
        longterm_manager.delete(CacheKey.design_metadata(str(instance.design_asset_id)))
        
        logger.debug(f"Invalidated BOM cache for design {instance.design_asset_id}")


@receiver([post_save, post_delete], sender=AnalysisJob)
def invalidate_analysis_cache(sender, instance, **kwargs):
    """Invalidate analysis job caches."""
    invalidate_model_cache(instance, instance.id)
    
    # Invalidate design detail cache (includes analysis jobs)
    if instance.design_asset:
        cache_manager = CacheManager('default')
        cache_manager.delete(CacheKey.design_detail(str(instance.design_asset_id)))
    
    logger.debug(f"Invalidated cache for analysis job {instance.id}")


@receiver([post_save, post_delete], sender=ReviewSession)
def invalidate_review_cache(sender, instance, **kwargs):
    """Invalidate review session caches."""
    invalidate_model_cache(instance, instance.id)
    
    cache_manager = CacheManager('default')
    
    # Invalidate review detail and markups
    cache_manager.delete(CacheKey.review_detail(str(instance.id)))
    cache_manager.delete(CacheKey.review_markups(str(instance.id)))
    
    # Invalidate design detail cache (includes reviews)
    if instance.design_asset:
        cache_manager.delete(CacheKey.design_detail(str(instance.design_asset_id)))
    
    logger.debug(f"Invalidated cache for review session {instance.id}")


@receiver([post_save, post_delete], sender=Markup)
def invalidate_markup_cache(sender, instance, **kwargs):
    """Invalidate markup caches."""
    invalidate_model_cache(instance, instance.id)
    
    # Invalidate review markups list
    if instance.review_session:
        cache_manager = CacheManager('default')
        cache_manager.delete(CacheKey.review_markups(str(instance.review_session_id)))
        cache_manager.delete(CacheKey.review_detail(str(instance.review_session_id)))
    
    logger.debug(f"Invalidated cache for markup {instance.id}")


@receiver([post_save, post_delete], sender=AuditLog)
def invalidate_audit_cache(sender, instance, **kwargs):
    """Invalidate audit log caches."""
    # Audit logs are write-heavy, read-light
    # Only invalidate specific queries if needed
    cache_manager = CacheManager('default')
    
    # Invalidate user's audit log cache
    if instance.user:
        cache_manager.delete_pattern(f"audit:user={instance.user_id}:*")
    
    # Invalidate organization's audit log cache
    if instance.organization:
        cache_manager.delete_pattern(f"audit:org={instance.organization_id}:*")


@receiver(m2m_changed, sender=ReviewSession.reviewers.through)
def invalidate_review_participants_cache(sender, instance, action, **kwargs):
    """Invalidate review cache when reviewers change."""
    if action in ('post_add', 'post_remove', 'post_clear'):
        cache_manager = CacheManager('default')
        cache_manager.delete(CacheKey.review_detail(str(instance.id)))
        
        logger.debug(f"Invalidated reviewers cache for review {instance.id}")


# Email Notification Signals

@receiver(post_save, sender=DesignAsset)
def notify_design_uploaded(sender, instance, created, **kwargs):
    """
    Notify organization members when a new design is uploaded.
    """
    from django.conf import settings
    from designs.notifications import NotificationService
    
    if created and settings.NOTIFICATIONS_ENABLED:
        try:
            NotificationService.notify_design_uploaded(instance)
            logger.info(f"Queued upload notifications for design {instance.id}")
        except Exception as e:
            logger.error(f"Error queuing upload notifications: {e}")


@receiver(pre_save, sender=DesignAsset)
def track_design_status_change(sender, instance, **kwargs):
    """
    Track design status changes to trigger appropriate notifications.
    """
    if instance.pk:  # Only for updates, not creates
        try:
            old_instance = DesignAsset.objects.get(pk=instance.pk)
            
            # Check if status changed
            if old_instance.status != instance.status:
                # Store old status for post_save signal
                instance._old_status = old_instance.status
        except DesignAsset.DoesNotExist:
            pass


@receiver(post_save, sender=DesignAsset)
def notify_design_status_change(sender, instance, created, **kwargs):
    """
    Notify design owner when design status changes (approved/rejected).
    """
    from django.conf import settings
    from designs.notifications import NotificationService
    
    if created or not settings.NOTIFICATIONS_ENABLED:
        return
    
    old_status = getattr(instance, '_old_status', None)
    
    if old_status and old_status != instance.status:
        try:
            if instance.status == 'APPROVED':
                NotificationService.notify_design_approved(instance)
                logger.info(f"Queued approval notification for design {instance.id}")
            
            elif instance.status == 'REJECTED':
                NotificationService.notify_design_rejected(instance)
                logger.info(f"Queued rejection notification for design {instance.id}")
        
        except Exception as e:
            logger.error(f"Error queuing status change notification: {e}")


@receiver(post_save, sender=ReviewSession)
def notify_review_lifecycle(sender, instance, created, **kwargs):
    """
    Notify design owner about review session lifecycle events.
    """
    from django.conf import settings
    from designs.notifications import NotificationService
    
    if not settings.NOTIFICATIONS_ENABLED:
        return
    
    try:
        if created:
            # Review session started
            NotificationService.notify_review_started(instance)
            logger.info(f"Queued review start notification for session {instance.id}")
        else:
            # Check if review was completed
            if instance.status in ['APPROVED', 'REJECTED', 'COMPLETED']:
                # Avoid duplicate notifications - check if we already notified
                if not hasattr(instance, '_notified'):
                    NotificationService.notify_review_completed(instance)
                    instance._notified = True
                    logger.info(f"Queued review completion notification for session {instance.id}")
    
    except Exception as e:
        logger.error(f"Error queuing review notification: {e}")


@receiver(post_save, sender=Markup)
def notify_markup_created(sender, instance, created, **kwargs):
    """
    Notify design owner when someone adds a markup/comment.
    """
    from django.conf import settings
    from designs.notifications import NotificationService
    
    if created and settings.NOTIFICATIONS_ENABLED:
        try:
            NotificationService.notify_markup_added(instance)
            logger.info(f"Queued markup notification for markup {instance.id}")
        except Exception as e:
            logger.error(f"Error queuing markup notification: {e}")


@receiver(post_save, sender=AnalysisJob)
def notify_job_status_change(sender, instance, created, **kwargs):
    """
    Notify user when their background job completes or fails.
    """
    from django.conf import settings
    from designs.notifications import NotificationService
    
    if created or not settings.NOTIFICATIONS_ENABLED:
        return
    
    try:
        if instance.status == 'SUCCESS':
            NotificationService.notify_job_completed(instance)
            logger.info(f"Queued job completion notification for job {instance.id}")
        
        elif instance.status == 'FAILURE':
            NotificationService.notify_job_failed(instance)
            logger.info(f"Queued job failure notification for job {instance.id}")
    
    except Exception as e:
        logger.error(f"Error queuing job notification: {e}")
