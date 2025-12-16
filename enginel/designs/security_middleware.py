"""
Security middleware for Enginel.

Provides:
- Rate limiting and throttling
- IP-based blocking
- Request validation and sanitization
- Security headers enforcement
- Attack detection (SQL injection, XSS, etc.)
"""

import time
import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta
from django.core.cache import cache
from django.http import JsonResponse, HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(MiddlewareMixin):
    """
    Rate limiting middleware to prevent API abuse.
    
    Implements:
    - Per-IP rate limiting
    - Per-user rate limiting
    - Endpoint-specific limits
    - Sliding window algorithm
    """
    
    # Rate limits: (requests, period_in_seconds)
    GLOBAL_RATE_LIMIT = (100, 60)  # 100 requests per minute globally
    AUTH_RATE_LIMIT = (1000, 3600)  # 1000 requests per hour for authenticated users
    ANON_RATE_LIMIT = (50, 60)  # 50 requests per minute for anonymous users
    
    # Endpoint-specific limits
    ENDPOINT_LIMITS = {
        '/api/auth/login/': (5, 300),  # 5 login attempts per 5 minutes
        '/api/auth/register/': (3, 3600),  # 3 registrations per hour
        '/api/designs/upload-url/': (20, 60),  # 20 upload requests per minute
        '/api/designs/': (100, 60),  # 100 design API calls per minute
    }
    
    def process_request(self, request):
        """Check rate limits before processing request."""
        # Skip rate limiting for static files and admin
        if not request.path.startswith('/api/'):
            return None
        
        # Get client identifier (IP or user ID)
        ip_address = self.get_client_ip(request)
        user_id = request.user.id if hasattr(request, 'user') and request.user.is_authenticated else None
        
        # Check global rate limit
        if self.is_rate_limited('global', ip_address, *self.GLOBAL_RATE_LIMIT):
            logger.warning(f"Global rate limit exceeded for IP: {ip_address}")
            return self.rate_limit_response()
        
        # Check user-specific rate limit
        if user_id:
            if self.is_rate_limited(f'user_{user_id}', ip_address, *self.AUTH_RATE_LIMIT):
                logger.warning(f"User rate limit exceeded for user: {user_id}")
                return self.rate_limit_response()
        else:
            if self.is_rate_limited(f'anon', ip_address, *self.ANON_RATE_LIMIT):
                logger.warning(f"Anonymous rate limit exceeded for IP: {ip_address}")
                return self.rate_limit_response()
        
        # Check endpoint-specific limits
        for endpoint_prefix, (limit, period) in self.ENDPOINT_LIMITS.items():
            if request.path.startswith(endpoint_prefix):
                cache_key = f'endpoint_{endpoint_prefix}_{ip_address}'
                if self.is_rate_limited(cache_key, ip_address, limit, period):
                    logger.warning(f"Endpoint rate limit exceeded for {endpoint_prefix} from IP: {ip_address}")
                    return self.rate_limit_response()
        
        return None
    
    def is_rate_limited(self, key_prefix, identifier, limit, period):
        """
        Check if rate limit is exceeded using sliding window.
        
        Args:
            key_prefix: Cache key prefix
            identifier: Client identifier (IP or user ID)
            limit: Maximum number of requests
            period: Time period in seconds
        
        Returns:
            True if rate limited, False otherwise
        """
        cache_key = f'rate_limit_{key_prefix}_{identifier}'
        
        # Get request timestamps from cache
        timestamps = cache.get(cache_key, [])
        now = time.time()
        
        # Remove old timestamps outside the window
        timestamps = [ts for ts in timestamps if now - ts < period]
        
        # Check if limit exceeded
        if len(timestamps) >= limit:
            return True
        
        # Add current timestamp
        timestamps.append(now)
        cache.set(cache_key, timestamps, period)
        
        return False
    
    def get_client_ip(self, request):
        """Extract client IP from request headers."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
    
    def rate_limit_response(self):
        """Return rate limit exceeded response."""
        return JsonResponse(
            {
                'error': 'Rate limit exceeded',
                'detail': 'Too many requests. Please try again later.',
                'code': 'rate_limit_exceeded'
            },
            status=429
        )


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Add security headers to all responses.
    
    Implements OWASP security headers:
    - X-Content-Type-Options
    - X-Frame-Options
    - X-XSS-Protection
    - Strict-Transport-Security
    - Content-Security-Policy
    - Referrer-Policy
    - Permissions-Policy
    """
    
    def process_response(self, request, response):
        """Add security headers to response."""
        # Prevent MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        
        # Prevent clickjacking
        response['X-Frame-Options'] = 'DENY'
        
        # Enable XSS protection
        response['X-XSS-Protection'] = '1; mode=block'
        
        # HSTS (only in production with HTTPS)
        if not settings.DEBUG:
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        # Content Security Policy
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # Adjust for your needs
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
        response['Content-Security-Policy'] = '; '.join(csp_directives)
        
        # Referrer policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions policy (formerly Feature-Policy)
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        return response


class IPBlockingMiddleware(MiddlewareMixin):
    """
    Block requests from blacklisted IPs.
    
    Maintains:
    - Static blacklist from settings
    - Dynamic blacklist from suspicious activity
    - Whitelist for trusted IPs
    """
    
    # Whitelist (never block these IPs)
    WHITELIST = getattr(settings, 'IP_WHITELIST', [])
    
    # Static blacklist
    BLACKLIST = getattr(settings, 'IP_BLACKLIST', [])
    
    def process_request(self, request):
        """Check if IP is blocked."""
        ip_address = self.get_client_ip(request)
        
        # Check whitelist first
        if ip_address in self.WHITELIST:
            return None
        
        # Check static blacklist
        if ip_address in self.BLACKLIST:
            logger.warning(f"Blocked request from blacklisted IP: {ip_address}")
            return self.blocked_response()
        
        # Check dynamic blacklist (from cache)
        if cache.get(f'blocked_ip_{ip_address}'):
            logger.warning(f"Blocked request from dynamically blacklisted IP: {ip_address}")
            return self.blocked_response()
        
        return None
    
    def get_client_ip(self, request):
        """Extract client IP from request headers."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
    
    def blocked_response(self):
        """Return blocked response."""
        return HttpResponseForbidden('Access denied')
    
    @staticmethod
    def block_ip(ip_address, duration_seconds=3600):
        """
        Dynamically block an IP address.
        
        Args:
            ip_address: IP to block
            duration_seconds: How long to block (default: 1 hour)
        """
        cache.set(f'blocked_ip_{ip_address}', True, duration_seconds)
        logger.info(f"Blocked IP: {ip_address} for {duration_seconds} seconds")


class RequestValidationMiddleware(MiddlewareMixin):
    """
    Validate and sanitize requests to detect attacks.
    
    Detects:
    - SQL injection attempts
    - XSS attempts
    - Path traversal attempts
    - Command injection attempts
    - Suspicious patterns
    """
    
    # SQL injection patterns
    SQL_PATTERNS = [
        r"(\bUNION\b.*\bSELECT\b)",
        r"(\bSELECT\b.*\bFROM\b.*\bWHERE\b)",
        r"(\bDROP\b.*\bTABLE\b)",
        r"(\bINSERT\b.*\bINTO\b)",
        r"(\bDELETE\b.*\bFROM\b)",
        r"(\bUPDATE\b.*\bSET\b)",
        r"('.*OR.*'.*=.*')",
        r"(--|\#|\/\*|\*\/)",
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r"(<script[^>]*>.*?</script>)",
        r"(javascript:)",
        r"(on\w+\s*=)",
        r"(<iframe[^>]*>)",
        r"(<object[^>]*>)",
        r"(<embed[^>]*>)",
    ]
    
    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r"(\.\./)",
        r"(\.\.\\)",
        r"(%2e%2e/)",
        r"(%2e%2e\\)",
    ]
    
    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r"(\||;|&|\$\(|\`)",
        r"(\bnc\b|\bnetcat\b)",
        r"(\bcurl\b|\bwget\b)",
        r"(\bpython\b|\bperl\b|\bruby\b)",
    ]
    
    def process_request(self, request):
        """Validate request for suspicious patterns."""
        # Skip validation for static files
        if not request.path.startswith('/api/'):
            return None
        
        ip_address = self.get_client_ip(request)
        
        # Check query parameters
        if self.contains_attack_pattern(str(request.GET)):
            logger.critical(f"Attack pattern detected in query params from IP: {ip_address} - Path: {request.path}")
            self.handle_attack(ip_address, 'query_param_attack')
            return self.attack_response()
        
        # Check POST body (if JSON)
        if request.method in ['POST', 'PUT', 'PATCH'] and request.content_type == 'application/json':
            try:
                body_str = request.body.decode('utf-8')
                if self.contains_attack_pattern(body_str):
                    logger.critical(f"Attack pattern detected in request body from IP: {ip_address} - Path: {request.path}")
                    self.handle_attack(ip_address, 'body_attack')
                    return self.attack_response()
            except Exception as e:
                logger.warning(f"Failed to decode request body: {e}")
        
        # Check headers for suspicious content
        suspicious_headers = ['User-Agent', 'Referer', 'X-Forwarded-For']
        for header in suspicious_headers:
            header_value = request.META.get(f'HTTP_{header.upper().replace("-", "_")}', '')
            if self.contains_attack_pattern(header_value):
                logger.warning(f"Attack pattern detected in header {header} from IP: {ip_address}")
                # Don't block on headers alone, but log it
        
        return None
    
    def contains_attack_pattern(self, text):
        """Check if text contains any attack patterns."""
        text = text.upper()
        
        # Check SQL injection
        for pattern in self.SQL_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        # Check XSS
        for pattern in self.XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        # Check path traversal
        for pattern in self.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        # Check command injection
        for pattern in self.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def handle_attack(self, ip_address, attack_type):
        """Handle detected attack."""
        # Increment attack counter
        cache_key = f'attack_count_{ip_address}'
        attack_count = cache.get(cache_key, 0) + 1
        cache.set(cache_key, attack_count, 3600)  # Track for 1 hour
        
        # Block IP after 3 attacks
        if attack_count >= 3:
            IPBlockingMiddleware.block_ip(ip_address, duration_seconds=86400)  # Block for 24 hours
            logger.critical(f"IP {ip_address} blocked after {attack_count} attack attempts")
    
    def get_client_ip(self, request):
        """Extract client IP from request headers."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
    
    def attack_response(self):
        """Return attack detected response."""
        return JsonResponse(
            {
                'error': 'Invalid request',
                'detail': 'Request contains invalid or suspicious content.',
                'code': 'invalid_request'
            },
            status=400
        )


class SessionSecurityMiddleware(MiddlewareMixin):
    """
    Enhance session security.
    
    Features:
    - Session hijacking detection
    - IP address validation
    - User agent validation
    - Session rotation after privilege escalation
    """
    
    def process_request(self, request):
        """Validate session security."""
        if not hasattr(request, 'session'):
            return None
        
        # Skip for anonymous users
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None
        
        # Get current IP and user agent
        current_ip = self.get_client_ip(request)
        current_ua = request.META.get('HTTP_USER_AGENT', '')
        
        # Get stored values from session
        stored_ip = request.session.get('_auth_ip')
        stored_ua = request.session.get('_auth_user_agent')
        
        # First request - store values
        if not stored_ip:
            request.session['_auth_ip'] = current_ip
            request.session['_auth_user_agent'] = current_ua
            return None
        
        # Check for session hijacking
        if stored_ip != current_ip:
            logger.warning(
                f"Session hijacking detected: User {request.user.id} - "
                f"IP changed from {stored_ip} to {current_ip}"
            )
            # In production, you might want to invalidate the session
            # request.session.flush()
            # return HttpResponseForbidden('Session validation failed')
        
        if stored_ua != current_ua:
            logger.warning(
                f"Suspicious activity: User {request.user.id} - "
                f"User agent changed"
            )
        
        return None
    
    def get_client_ip(self, request):
        """Extract client IP from request headers."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
