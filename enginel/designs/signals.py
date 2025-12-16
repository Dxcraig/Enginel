"""
Django signals for automatic cache invalidation.

Listens for model save/delete events and invalidates related caches.
"""
from django.db.models.signals import post_save, post_delete, m2m_changed
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
