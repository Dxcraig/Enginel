"""
Caching utilities for Enginel.

Provides decorators, helpers, and strategies for caching API responses,
database queries, and expensive computations (geometry processing, BOM extraction).

Cache Strategy:
- API responses: 5 minutes (default cache)
- Geometry metadata: 1 hour (longterm cache)
- Organization data: 15 minutes
- User permissions: 10 minutes
- BOM data: 30 minutes
- Search results: 2 minutes

Cache Invalidation:
- Automatic on model save/delete via signals
- Manual invalidation via cache_manager functions
- Time-based expiration as fallback
"""
import hashlib
import json
import functools
from typing import Any, Callable, Optional, Union
from django.core.cache import caches, cache as default_cache
from django.db.models import Model
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Centralized cache management for Enginel.
    
    Provides methods for getting, setting, deleting, and invalidating cache keys
    with consistent key generation and logging.
    """
    
    def __init__(self, cache_alias: str = 'default'):
        """
        Initialize cache manager with specific cache backend.
        
        Args:
            cache_alias: Name of cache backend ('default', 'longterm', 'sessions')
        """
        self.cache = caches[cache_alias]
        self.cache_alias = cache_alias
    
    @staticmethod
    def make_key(*args, prefix: str = '', **kwargs) -> str:
        """
        Generate consistent cache key from arguments.
        
        Args:
            *args: Positional arguments to include in key
            prefix: Key prefix for namespacing
            **kwargs: Keyword arguments to include in key
        
        Returns:
            Hashed cache key string
        
        Example:
            >>> CacheManager.make_key('design', 123, format='step', prefix='geometry')
            'geometry:a1b2c3d4...'
        """
        # Combine all arguments into a stable string
        key_parts = [str(arg) for arg in args]
        
        # Add kwargs in sorted order for consistency
        for k in sorted(kwargs.keys()):
            key_parts.append(f"{k}={kwargs[k]}")
        
        # Create hash of combined parts
        key_data = ':'.join(key_parts)
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        
        # Add prefix if provided
        if prefix:
            return f"{prefix}:{key_hash}"
        return key_hash
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from cache with logging.
        
        Args:
            key: Cache key
            default: Value to return if key not found
        
        Returns:
            Cached value or default
        """
        try:
            value = self.cache.get(key, default)
            if value is not None and value != default:
                logger.debug(f"Cache hit: {key} (alias={self.cache_alias})")
            else:
                logger.debug(f"Cache miss: {key} (alias={self.cache_alias})")
            return value
        except Exception as e:
            logger.warning(f"Cache get error for {key}: {e}")
            return default
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """
        Set value in cache with logging.
        
        Args:
            key: Cache key
            value: Value to cache
            timeout: Optional timeout in seconds (None = use default)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.cache.set(key, value, timeout)
            logger.debug(f"Cache set: {key} (alias={self.cache_alias}, timeout={timeout})")
            return True
        except Exception as e:
            logger.warning(f"Cache set error for {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key to delete
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.cache.delete(key)
            logger.debug(f"Cache delete: {key} (alias={self.cache_alias})")
            return True
        except Exception as e:
            logger.warning(f"Cache delete error for {key}: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.
        
        Args:
            pattern: Pattern to match (e.g., 'design:*', 'user:123:*')
        
        Returns:
            Number of keys deleted
        """
        try:
            # django-redis provides delete_pattern
            deleted = self.cache.delete_pattern(pattern)
            logger.info(f"Cache delete pattern: {pattern} ({deleted} keys, alias={self.cache_alias})")
            return deleted
        except Exception as e:
            logger.warning(f"Cache delete pattern error for {pattern}: {e}")
            return 0
    
    def clear(self) -> bool:
        """
        Clear entire cache.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.cache.clear()
            logger.warning(f"Cache cleared (alias={self.cache_alias})")
            return True
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False
    
    def get_or_set(self, key: str, default_func: Callable, timeout: Optional[int] = None) -> Any:
        """
        Get value from cache, or set it using default_func if not found.
        
        Args:
            key: Cache key
            default_func: Function to call if cache miss
            timeout: Optional timeout in seconds
        
        Returns:
            Cached or newly computed value
        
        Example:
            >>> def expensive_query():
            ...     return DesignAsset.objects.filter(status='COMPLETED').count()
            >>> count = cache_manager.get_or_set('design_count', expensive_query, 300)
        """
        value = self.get(key)
        if value is None:
            value = default_func()
            self.set(key, value, timeout)
        return value


# Global cache managers
default_cache_manager = CacheManager('default')
longterm_cache_manager = CacheManager('longterm')


def cache_result(timeout: int = 300, cache_alias: str = 'default', 
                 key_prefix: str = '', key_func: Optional[Callable] = None):
    """
    Decorator to cache function results.
    
    Args:
        timeout: Cache timeout in seconds (default 5 minutes)
        cache_alias: Cache backend to use
        key_prefix: Prefix for cache keys
        key_func: Optional function to generate custom cache key
    
    Example:
        >>> @cache_result(timeout=600, key_prefix='geometry')
        ... def calculate_volume(design_id):
        ...     # Expensive computation
        ...     return volume
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = CacheManager.make_key(
                    func.__name__, *args, 
                    prefix=key_prefix, 
                    **kwargs
                )
            
            # Try to get from cache
            cache_manager = CacheManager(cache_alias)
            cached_value = cache_manager.get(cache_key)
            
            if cached_value is not None:
                return cached_value
            
            # Compute and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, timeout)
            
            return result
        
        return wrapper
    return decorator


def cache_queryset(timeout: int = 300, key_prefix: str = 'qs'):
    """
    Decorator to cache Django queryset results.
    
    Converts queryset to list for caching (querysets can't be pickled).
    
    Args:
        timeout: Cache timeout in seconds
        key_prefix: Prefix for cache keys
    
    Example:
        >>> @cache_queryset(timeout=600, key_prefix='designs')
        ... def get_active_designs(org_id):
        ...     return DesignAsset.objects.filter(
        ...         series__organization_id=org_id,
        ...         upload_status='COMPLETED'
        ...     )
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = CacheManager.make_key(
                func.__name__, *args,
                prefix=key_prefix,
                **kwargs
            )
            
            cached_value = default_cache_manager.get(cache_key)
            
            if cached_value is not None:
                return cached_value
            
            # Execute queryset and convert to list
            result = func(*args, **kwargs)
            
            # Handle both querysets and already-evaluated results
            if hasattr(result, '_result_cache'):
                # It's a queryset, convert to list
                result_list = list(result)
            else:
                result_list = result
            
            default_cache_manager.set(cache_key, result_list, timeout)
            
            return result_list
        
        return wrapper
    return decorator


def invalidate_cache(*keys: str, pattern: Optional[str] = None, 
                     cache_alias: str = 'default'):
    """
    Invalidate cache keys or patterns.
    
    Args:
        *keys: Specific cache keys to delete
        pattern: Pattern to match for deletion (e.g., 'design:*')
        cache_alias: Cache backend to use
    
    Example:
        >>> # Invalidate specific keys
        >>> invalidate_cache('design:123:metadata', 'design:123:bom')
        
        >>> # Invalidate pattern
        >>> invalidate_cache(pattern='design:123:*')
    """
    cache_manager = CacheManager(cache_alias)
    
    # Delete specific keys
    for key in keys:
        cache_manager.delete(key)
    
    # Delete pattern if provided
    if pattern:
        cache_manager.delete_pattern(pattern)


def invalidate_model_cache(model: Union[Model, type], instance_id: Optional[Any] = None):
    """
    Invalidate cache for a model instance or all instances of a model.
    
    Args:
        model: Django model class or instance
        instance_id: Optional specific instance ID to invalidate
    
    Example:
        >>> # Invalidate all DesignAsset caches
        >>> invalidate_model_cache(DesignAsset)
        
        >>> # Invalidate specific design
        >>> design = DesignAsset.objects.get(pk=some_id)
        >>> invalidate_model_cache(design, design.id)
    """
    # Get model class if instance provided
    if isinstance(model, Model):
        model_class = model.__class__
        instance_id = model.pk
    else:
        model_class = model
    
    model_name = model_class.__name__.lower()
    
    # Invalidate specific instance
    if instance_id:
        pattern = f"{model_name}:{instance_id}:*"
        logger.info(f"Invalidating cache for {model_name} instance {instance_id}")
    else:
        pattern = f"{model_name}:*"
        logger.info(f"Invalidating all cache for {model_name}")
    
    # Invalidate in all cache backends
    for alias in ['default', 'longterm']:
        cache_manager = CacheManager(alias)
        cache_manager.delete_pattern(pattern)


class CacheKey:
    """
    Cache key constants and generators for consistent key naming.
    """
    
    # Design-related keys
    @staticmethod
    def design_detail(design_id: str) -> str:
        """Cache key for design asset detail."""
        return f"design:{design_id}:detail"
    
    @staticmethod
    def design_metadata(design_id: str) -> str:
        """Cache key for design geometry metadata."""
        return f"design:{design_id}:metadata"
    
    @staticmethod
    def design_bom(design_id: str) -> str:
        """Cache key for design BOM tree."""
        return f"design:{design_id}:bom"
    
    @staticmethod
    def design_list(org_id: str, **filters) -> str:
        """Cache key for design list queries."""
        filter_str = ':'.join(f"{k}={v}" for k, v in sorted(filters.items()))
        return f"design:list:org={org_id}:{filter_str}"
    
    # Series-related keys
    @staticmethod
    def series_detail(series_id: str) -> str:
        """Cache key for design series detail."""
        return f"series:{series_id}:detail"
    
    @staticmethod
    def series_versions(series_id: str) -> str:
        """Cache key for series versions list."""
        return f"series:{series_id}:versions"
    
    # User-related keys
    @staticmethod
    def user_permissions(user_id: int) -> str:
        """Cache key for user permissions."""
        return f"user:{user_id}:permissions"
    
    # Review-related keys
    @staticmethod
    def review_detail(review_id: str) -> str:
        """Cache key for review session detail."""
        return f"review:{review_id}:detail"
    
    @staticmethod
    def review_markups(review_id: str) -> str:
        """Cache key for review markups list."""
        return f"review:{review_id}:markups"
    
    # Search-related keys
    @staticmethod
    def search_results(query: str, model: str, **filters) -> str:
        """Cache key for search results."""
        filter_str = ':'.join(f"{k}={v}" for k, v in sorted(filters.items()))
        query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
        return f"search:{model}:{query_hash}:{filter_str}"


def get_cache_stats() -> dict:
    """
    Get cache statistics and health information.
    
    Returns:
        Dictionary with cache stats for each backend
    """
    stats = {}
    
    for alias in ['default', 'longterm', 'sessions']:
        try:
            cache = caches[alias]
            # Get Redis info if available
            if hasattr(cache, '_cache') and hasattr(cache._cache, 'get_client'):
                client = cache._cache.get_client()
                info = client.info('stats')
                
                stats[alias] = {
                    'connected': True,
                    'keyspace_hits': info.get('keyspace_hits', 0),
                    'keyspace_misses': info.get('keyspace_misses', 0),
                    'total_commands_processed': info.get('total_commands_processed', 0),
                    'used_memory_human': client.info('memory').get('used_memory_human', 'N/A'),
                }
                
                # Calculate hit rate
                hits = stats[alias]['keyspace_hits']
                misses = stats[alias]['keyspace_misses']
                total = hits + misses
                if total > 0:
                    stats[alias]['hit_rate'] = round((hits / total) * 100, 2)
                else:
                    stats[alias]['hit_rate'] = 0
            else:
                stats[alias] = {'connected': True, 'type': 'unknown'}
                
        except Exception as e:
            stats[alias] = {'connected': False, 'error': str(e)}
    
    return stats
