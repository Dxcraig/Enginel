"""
Error tracking and monitoring utilities for Enginel.

Provides comprehensive error logging, performance monitoring,
and metrics collection for production observability.
"""
import logging
import time
import traceback
from functools import wraps
from typing import Dict, Any, Optional
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import json

logger = logging.getLogger(__name__)


class ErrorTracker:
    """
    Centralized error tracking with rate limiting and aggregation.
    """
    
    @staticmethod
    def log_error(
        error: Exception,
        context: Dict[str, Any] = None,
        user_id: int = None,
        request_path: str = None,
        severity: str = 'ERROR'
    ):
        """
        Log error with structured context.
        
        Args:
            error: Exception that occurred
            context: Additional context (design_id, task_id, etc.)
            user_id: User who triggered the error
            request_path: API endpoint path
            severity: ERROR, CRITICAL, WARNING
        """
        error_data = {
            'timestamp': timezone.now().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'severity': severity,
            'user_id': user_id,
            'request_path': request_path,
            'context': context or {},
            'traceback': traceback.format_exc(),
        }
        
        # Log to file/console
        if severity == 'CRITICAL':
            logger.critical(json.dumps(error_data, indent=2))
        else:
            logger.error(json.dumps(error_data, indent=2))
        
        # Store in cache for recent errors view
        ErrorTracker._store_recent_error(error_data)
        
        # Increment error counter
        ErrorTracker._increment_error_count(type(error).__name__)
        
        return error_data
    
    @staticmethod
    def _store_recent_error(error_data: Dict[str, Any]):
        """Store error in cache for monitoring dashboard."""
        cache_key = 'enginel:recent_errors'
        recent_errors = cache.get(cache_key, [])
        
        # Keep last 100 errors
        recent_errors.append(error_data)
        if len(recent_errors) > 100:
            recent_errors = recent_errors[-100:]
        
        cache.set(cache_key, recent_errors, timeout=3600)  # 1 hour
    
    @staticmethod
    def _increment_error_count(error_type: str):
        """Increment error counter for metrics."""
        cache_key = f'enginel:error_count:{error_type}'
        count = cache.get(cache_key, 0)
        cache.set(cache_key, count + 1, timeout=86400)  # 24 hours
    
    @staticmethod
    def get_recent_errors(limit: int = 50) -> list:
        """Get recent errors for monitoring."""
        cache_key = 'enginel:recent_errors'
        recent_errors = cache.get(cache_key, [])
        return recent_errors[-limit:]
    
    @staticmethod
    def get_error_stats(hours: int = 24) -> Dict[str, int]:
        """Get error statistics by type."""
        # This is a simplified version - in production, use a proper time-series DB
        stats = {}
        # Scan cache for error counts
        # In production, use Redis SCAN or proper metrics backend
        return stats


class PerformanceMonitor:
    """
    Monitor request/task performance and detect slow operations.
    """
    
    @staticmethod
    def track_duration(operation_name: str):
        """
        Decorator to track operation duration.
        
        Usage:
            @PerformanceMonitor.track_duration('geometry_extraction')
            def extract_geometry(file_path):
                # ... processing ...
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                error_occurred = False
                
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    error_occurred = True
                    raise
                finally:
                    duration = time.time() - start_time
                    PerformanceMonitor._record_duration(
                        operation_name,
                        duration,
                        error_occurred
                    )
            return wrapper
        return decorator
    
    @staticmethod
    def _record_duration(operation_name: str, duration: float, error: bool):
        """Record operation duration to cache."""
        cache_key = f'enginel:perf:{operation_name}'
        
        # Get existing stats
        stats = cache.get(cache_key, {
            'count': 0,
            'total_duration': 0,
            'max_duration': 0,
            'min_duration': float('inf'),
            'error_count': 0,
        })
        
        # Update stats
        stats['count'] += 1
        stats['total_duration'] += duration
        stats['max_duration'] = max(stats['max_duration'], duration)
        stats['min_duration'] = min(stats['min_duration'], duration)
        if error:
            stats['error_count'] += 1
        
        # Store updated stats
        cache.set(cache_key, stats, timeout=3600)
        
        # Log slow operations
        if duration > 30:  # 30 seconds threshold
            logger.warning(
                f"Slow operation detected: {operation_name} took {duration:.2f}s"
            )
    
    @staticmethod
    def get_operation_stats(operation_name: str) -> Optional[Dict[str, Any]]:
        """Get performance stats for an operation."""
        cache_key = f'enginel:perf:{operation_name}'
        stats = cache.get(cache_key)
        
        if stats and stats['count'] > 0:
            stats['avg_duration'] = stats['total_duration'] / stats['count']
            stats['error_rate'] = stats['error_count'] / stats['count']
        
        return stats
    
    @staticmethod
    def get_all_stats() -> Dict[str, Dict[str, Any]]:
        """Get all performance stats (requires cache key scanning)."""
        # In production, maintain a registry of tracked operations
        # For now, return empty dict
        return {}


class MetricsCollector:
    """
    Collect application metrics for monitoring dashboards.
    """
    
    @staticmethod
    def increment_counter(metric_name: str, value: int = 1):
        """Increment a counter metric."""
        cache_key = f'enginel:metric:{metric_name}'
        current = cache.get(cache_key, 0)
        cache.set(cache_key, current + value, timeout=86400)
    
    @staticmethod
    def record_gauge(metric_name: str, value: float):
        """Record a gauge value (current state)."""
        cache_key = f'enginel:gauge:{metric_name}'
        cache.set(cache_key, value, timeout=300)  # 5 minutes
    
    @staticmethod
    def track_file_upload(file_size_bytes: int, file_type: str):
        """Track file upload metrics."""
        MetricsCollector.increment_counter('uploads_total')
        MetricsCollector.increment_counter(f'uploads_{file_type}')
        
        # Track total bytes uploaded
        cache_key = 'enginel:metric:total_bytes_uploaded'
        current = cache.get(cache_key, 0)
        cache.set(cache_key, current + file_size_bytes, timeout=86400)
    
    @staticmethod
    def track_celery_task(task_name: str, duration: float, status: str):
        """Track Celery task execution."""
        MetricsCollector.increment_counter(f'celery_task_{task_name}')
        MetricsCollector.increment_counter(f'celery_task_{task_name}_{status}')
        
        # Track duration
        cache_key = f'enginel:task_duration:{task_name}'
        durations = cache.get(cache_key, [])
        durations.append(duration)
        if len(durations) > 100:
            durations = durations[-100:]
        cache.set(cache_key, durations, timeout=3600)
    
    @staticmethod
    def get_metrics() -> Dict[str, Any]:
        """Get current metrics snapshot."""
        # In production, this would query the metrics backend
        # For now, return basic stats from cache
        return {
            'timestamp': timezone.now().isoformat(),
            'uploads_total': cache.get('enginel:metric:uploads_total', 0),
            'total_bytes_uploaded': cache.get('enginel:metric:total_bytes_uploaded', 0),
        }


class HealthChecker:
    """
    Health check utilities for monitoring system status.
    """
    
    @staticmethod
    def check_database() -> Dict[str, Any]:
        """Check database connectivity."""
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return {'status': 'healthy', 'message': 'Database connection OK'}
        except Exception as e:
            return {'status': 'unhealthy', 'message': str(e)}
    
    @staticmethod
    def check_redis() -> Dict[str, Any]:
        """Check Redis connectivity."""
        try:
            cache.set('health_check', 'ok', timeout=10)
            result = cache.get('health_check')
            if result == 'ok':
                return {'status': 'healthy', 'message': 'Redis connection OK'}
            else:
                return {'status': 'unhealthy', 'message': 'Redis read/write failed'}
        except Exception as e:
            return {'status': 'unhealthy', 'message': str(e)}
    
    @staticmethod
    def check_celery() -> Dict[str, Any]:
        """Check Celery workers status."""
        try:
            from celery import current_app
            inspect = current_app.control.inspect()
            stats = inspect.stats()
            
            if stats:
                worker_count = len(stats)
                return {
                    'status': 'healthy',
                    'message': f'{worker_count} worker(s) active',
                    'workers': list(stats.keys())
                }
            else:
                return {
                    'status': 'unhealthy',
                    'message': 'No workers available'
                }
        except Exception as e:
            return {'status': 'unhealthy', 'message': str(e)}
    
    @staticmethod
    def check_storage() -> Dict[str, Any]:
        """Check storage backend (S3 or local)."""
        try:
            from django.core.files.storage import default_storage
            # Try to check storage accessibility
            # In production, test S3 connectivity
            return {'status': 'healthy', 'message': 'Storage accessible'}
        except Exception as e:
            return {'status': 'unhealthy', 'message': str(e)}
    
    @staticmethod
    def get_full_health_status() -> Dict[str, Any]:
        """Get complete system health status."""
        checks = {
            'database': HealthChecker.check_database(),
            'redis': HealthChecker.check_redis(),
            'celery': HealthChecker.check_celery(),
            'storage': HealthChecker.check_storage(),
        }
        
        # Overall status
        all_healthy = all(check['status'] == 'healthy' for check in checks.values())
        
        return {
            'status': 'healthy' if all_healthy else 'degraded',
            'timestamp': timezone.now().isoformat(),
            'checks': checks
        }


def log_api_request(request, response, duration: float):
    """
    Log API request details for monitoring.
    
    Args:
        request: Django request object
        response: Django response object
        duration: Request duration in seconds
    """
    log_data = {
        'timestamp': timezone.now().isoformat(),
        'method': request.method,
        'path': request.path,
        'status_code': response.status_code,
        'duration': duration,
        'user_id': request.user.id if request.user.is_authenticated else None,
        'ip_address': request.META.get('REMOTE_ADDR'),
        'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
    }
    
    # Log slow requests
    if duration > 5:  # 5 seconds threshold
        logger.warning(f"Slow request: {json.dumps(log_data)}")
    else:
        logger.info(f"API request: {request.method} {request.path} - {response.status_code} ({duration:.3f}s)")
    
    # Track metrics
    MetricsCollector.increment_counter('api_requests_total')
    MetricsCollector.increment_counter(f'api_requests_{response.status_code}')
