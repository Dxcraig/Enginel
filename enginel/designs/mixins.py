"""
Mixins for adding caching to DRF ViewSets.

Provides automatic caching of list and retrieve responses with
proper cache key generation and invalidation.
"""
from rest_framework.response import Response
from designs.cache import CacheManager, CacheKey
import logging

logger = logging.getLogger(__name__)


class CachedViewSetMixin:
    """
    Mixin to add caching to ViewSet list and retrieve actions.
    
    Override cache_timeout to customize TTL.
    Override get_cache_key_prefix to customize cache key namespace.
    
    Example:
        class DesignAssetViewSet(CachedViewSetMixin, viewsets.ModelViewSet):
            cache_timeout = 300  # 5 minutes
            cache_list = True
            cache_retrieve = True
    """
    
    cache_timeout = 300  # Default 5 minutes
    cache_alias = 'default'
    cache_list = True  # Cache list responses
    cache_retrieve = True  # Cache retrieve responses
    
    def get_cache_key_prefix(self):
        """Get cache key prefix based on model name."""
        return self.queryset.model.__name__.lower()
    
    def get_list_cache_key(self):
        """
        Generate cache key for list endpoint.
        
        Includes query parameters to ensure different queries get different caches.
        """
        prefix = self.get_cache_key_prefix()
        
        # Build key from query params
        query_params = self.request.query_params.dict()
        
        # Add user context for permission-based filtering
        user_id = self.request.user.id if self.request.user.is_authenticated else 'anon'
        
        return CacheManager.make_key(
            'list',
            user_id,
            prefix=prefix,
            **query_params
        )
    
    def get_retrieve_cache_key(self, pk):
        """Generate cache key for retrieve endpoint."""
        prefix = self.get_cache_key_prefix()
        user_id = self.request.user.id if self.request.user.is_authenticated else 'anon'
        
        return CacheManager.make_key(
            'detail',
            pk,
            user_id,
            prefix=prefix
        )
    
    def list(self, request, *args, **kwargs):
        """Override list to add caching."""
        if not self.cache_list:
            return super().list(request, *args, **kwargs)
        
        cache_key = self.get_list_cache_key()
        cache_manager = CacheManager(self.cache_alias)
        
        # Try to get from cache
        cached_response = cache_manager.get(cache_key)
        if cached_response is not None:
            logger.debug(f"Cache hit for list: {cache_key}")
            return Response(cached_response)
        
        # Get fresh data
        response = super().list(request, *args, **kwargs)
        
        # Cache successful responses
        if response.status_code == 200:
            cache_manager.set(cache_key, response.data, self.cache_timeout)
            logger.debug(f"Cached list response: {cache_key}")
        
        return response
    
    def retrieve(self, request, *args, **kwargs):
        """Override retrieve to add caching."""
        if not self.cache_retrieve:
            return super().retrieve(request, *args, **kwargs)
        
        # Get primary key from kwargs (handle different lookup fields)
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        pk = kwargs.get(lookup_url_kwarg)
        
        cache_key = self.get_retrieve_cache_key(pk)
        cache_manager = CacheManager(self.cache_alias)
        
        # Try to get from cache
        cached_response = cache_manager.get(cache_key)
        if cached_response is not None:
            logger.debug(f"Cache hit for retrieve: {cache_key}")
            return Response(cached_response)
        
        # Get fresh data
        response = super().retrieve(request, *args, **kwargs)
        
        # Cache successful responses
        if response.status_code == 200:
            cache_manager.set(cache_key, response.data, self.cache_timeout)
            logger.debug(f"Cached retrieve response: {cache_key}")
        
        return response
    
    def perform_create(self, serializer):
        """Override create to invalidate list cache."""
        result = super().perform_create(serializer)
        self.invalidate_list_cache()
        return result
    
    def perform_update(self, serializer):
        """Override update to invalidate caches."""
        instance = self.get_object()
        pk = getattr(instance, self.lookup_field, instance.pk)
        
        result = super().perform_update(serializer)
        
        # Invalidate both detail and list caches
        self.invalidate_detail_cache(pk)
        self.invalidate_list_cache()
        
        return result
    
    def perform_destroy(self, instance):
        """Override destroy to invalidate caches."""
        pk = getattr(instance, self.lookup_field, instance.pk)
        
        result = super().perform_destroy(instance)
        
        # Invalidate both detail and list caches
        self.invalidate_detail_cache(pk)
        self.invalidate_list_cache()
        
        return result
    
    def invalidate_list_cache(self):
        """Invalidate all list caches for this resource."""
        prefix = self.get_cache_key_prefix()
        pattern = f"{prefix}:*:list:*"
        
        cache_manager = CacheManager(self.cache_alias)
        deleted = cache_manager.delete_pattern(pattern)
        
        if deleted > 0:
            logger.debug(f"Invalidated {deleted} list cache entries for {prefix}")
    
    def invalidate_detail_cache(self, pk):
        """Invalidate detail cache for specific instance."""
        cache_key = self.get_retrieve_cache_key(pk)
        cache_manager = CacheManager(self.cache_alias)
        cache_manager.delete(cache_key)
        
        logger.debug(f"Invalidated detail cache: {cache_key}")


class LongtermCachedMixin(CachedViewSetMixin):
    """
    Mixin for resources that change infrequently.
    
    Uses longterm cache backend with 1 hour TTL.
    Ideal for geometry metadata, BOM trees, analysis results.
    """
    cache_timeout = 3600  # 1 hour
    cache_alias = 'longterm'


class ShortCachedMixin(CachedViewSetMixin):
    """
    Mixin for frequently changing resources.
    
    Uses default cache with 2 minute TTL.
    Ideal for search results, lists with filters.
    """
    cache_timeout = 120  # 2 minutes
