"""
Django middleware for error tracking and performance monitoring.

Automatically tracks all requests, errors, and performance metrics.
"""
import time
import logging
from django.utils.deprecation import MiddlewareMixin
from .monitoring import ErrorTracker, log_api_request, MetricsCollector

logger = logging.getLogger(__name__)


class ErrorTrackingMiddleware(MiddlewareMixin):
    """
    Middleware to track all exceptions and log them with context.
    """
    
    def process_exception(self, request, exception):
        """Called when a view raises an exception."""
        context = {
            'method': request.method,
            'path': request.path,
            'query_params': dict(request.GET),
        }
        
        # Don't log request body for security (may contain passwords, tokens)
        # In production, you might want to log it for POST/PUT with PII redaction
        
        user_id = request.user.id if hasattr(request, 'user') and request.user.is_authenticated else None
        
        ErrorTracker.log_error(
            error=exception,
            context=context,
            user_id=user_id,
            request_path=request.path,
            severity='ERROR'
        )
        
        # Don't suppress the exception - let Django's error handling continue
        return None


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log all API requests with performance metrics.
    """
    
    def process_request(self, request):
        """Mark request start time."""
        request._start_time = time.time()
    
    def process_response(self, request, response):
        """Log request after response is ready."""
        if hasattr(request, '_start_time'):
            duration = time.time() - request._start_time
            
            # Only log API requests (not static files, admin, etc.)
            if request.path.startswith('/api/'):
                log_api_request(request, response, duration)
        
        return response


class PerformanceMonitoringMiddleware(MiddlewareMixin):
    """
    Middleware to track request performance and detect slow endpoints.
    """
    
    def process_request(self, request):
        """Mark request start time."""
        request._perf_start = time.time()
    
    def process_response(self, request, response):
        """Track performance metrics."""
        if hasattr(request, '_perf_start'):
            duration = time.time() - request._perf_start
            
            # Track API endpoint performance
            if request.path.startswith('/api/'):
                endpoint = request.path
                method = request.method
                
                # Store performance data
                from .monitoring import PerformanceMonitor
                PerformanceMonitor._record_duration(
                    f"api_{method}_{endpoint}",
                    duration,
                    error=response.status_code >= 400
                )
        
        return response


class MetricsMiddleware(MiddlewareMixin):
    """
    Middleware to collect application metrics.
    """
    
    def process_response(self, request, response):
        """Collect metrics from requests."""
        # Track API requests by status code
        if request.path.startswith('/api/'):
            MetricsCollector.increment_counter('http_requests_total')
            MetricsCollector.increment_counter(f'http_status_{response.status_code}')
            
            # Track by endpoint
            endpoint = request.path.split('/')[2] if len(request.path.split('/')) > 2 else 'unknown'
            MetricsCollector.increment_counter(f'endpoint_{endpoint}')
        
        return response
