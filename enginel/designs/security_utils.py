"""
Security utilities for Enginel.

Provides:
- Custom exception handling with security considerations
- Input sanitization helpers
- Password strength validation
- Audit logging for security events
- Token management utilities
"""

import re
import html
import logging
from datetime import datetime, timedelta
from django.core.cache import cache
from django.contrib.auth.hashers import check_password
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF that doesn't leak sensitive information.
    
    In production, hides detailed error messages from clients while logging
    them for developers.
    """
    # Get the standard error response
    response = exception_handler(exc, context)
    
    if response is not None:
        # Log the full exception
        request = context.get('request')
        user_id = request.user.id if hasattr(request, 'user') and request.user.is_authenticated else None
        
        logger.error(
            f"API Exception: {exc.__class__.__name__} - {str(exc)} - "
            f"Path: {request.path if request else 'N/A'} - "
            f"User: {user_id if user_id else 'Anonymous'}"
        )
        
        # In production, sanitize error messages
        from django.conf import settings
        if not settings.DEBUG:
            # Don't expose internal details in production
            if response.status_code >= 500:
                response.data = {
                    'error': 'Internal server error',
                    'detail': 'An unexpected error occurred. Please try again later.',
                    'code': 'internal_error'
                }
            elif response.status_code == 404:
                response.data = {
                    'error': 'Not found',
                    'detail': 'The requested resource was not found.',
                    'code': 'not_found'
                }
            # Keep 400/401/403 messages as they're usually safe
    
    return response


def sanitize_input(text, allow_html=False):
    """
    Sanitize user input to prevent XSS and other injection attacks.
    
    Args:
        text: Input text to sanitize
        allow_html: If False, escape all HTML. If True, allow safe HTML.
    
    Returns:
        Sanitized text
    """
    if not isinstance(text, str):
        return text
    
    if not allow_html:
        # Escape all HTML entities
        return html.escape(text)
    
    # If allowing HTML, use a whitelist approach (implement as needed)
    # For now, just escape dangerous tags
    dangerous_tags = ['script', 'iframe', 'object', 'embed', 'link', 'style']
    for tag in dangerous_tags:
        text = re.sub(f'<{tag}[^>]*>.*?</{tag}>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(f'<{tag}[^>]*/?>', '', text, flags=re.IGNORECASE)
    
    return text


def validate_file_upload(file_obj, allowed_extensions=None, max_size_mb=500):
    """
    Validate uploaded file for security.
    
    Args:
        file_obj: Uploaded file object
        allowed_extensions: List of allowed extensions (e.g., ['.step', '.iges'])
        max_size_mb: Maximum file size in MB
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check file size
    if file_obj.size > max_size_mb * 1024 * 1024:
        return False, f'File size exceeds {max_size_mb}MB limit'
    
    # Check file extension
    if allowed_extensions:
        file_ext = file_obj.name.lower().split('.')[-1]
        if f'.{file_ext}' not in allowed_extensions:
            return False, f'File type not allowed. Allowed types: {", ".join(allowed_extensions)}'
    
    # Check for null bytes (potential security issue)
    if b'\x00' in file_obj.read(1024):
        file_obj.seek(0)  # Reset file pointer
        return False, 'Invalid file content detected'
    
    file_obj.seek(0)  # Reset file pointer
    
    # Check filename for path traversal
    if '..' in file_obj.name or '/' in file_obj.name or '\\' in file_obj.name:
        return False, 'Invalid filename'
    
    return True, None


def check_password_strength(password):
    """
    Check password strength beyond Django's default validators.
    
    Args:
        password: Password to check
    
    Returns:
        Tuple of (is_strong, issues_list)
    """
    issues = []
    
    # Length check
    if len(password) < 12:
        issues.append('Password must be at least 12 characters')
    
    # Character variety checks
    if not re.search(r'[a-z]', password):
        issues.append('Password must contain lowercase letters')
    
    if not re.search(r'[A-Z]', password):
        issues.append('Password must contain uppercase letters')
    
    if not re.search(r'\d', password):
        issues.append('Password must contain numbers')
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        issues.append('Password must contain special characters')
    
    # Check for common patterns
    common_patterns = ['123', 'abc', 'qwerty', 'password', 'admin']
    if any(pattern in password.lower() for pattern in common_patterns):
        issues.append('Password contains common patterns')
    
    # Check for repeated characters
    if re.search(r'(.)\1{2,}', password):
        issues.append('Password contains too many repeated characters')
    
    return len(issues) == 0, issues


def log_security_event(event_type, user_id=None, ip_address=None, details=None, severity='INFO'):
    """
    Log security-related events for audit trail.
    
    Args:
        event_type: Type of event (e.g., 'login_failed', 'password_changed')
        user_id: User ID associated with the event
        ip_address: Client IP address
        details: Additional event details (dict)
        severity: Log severity (INFO, WARNING, ERROR, CRITICAL)
    """
    log_data = {
        'event_type': event_type,
        'user_id': user_id,
        'ip_address': ip_address,
        'timestamp': datetime.now().isoformat(),
        'details': details or {}
    }
    
    # Log with appropriate severity
    log_message = f"Security Event: {event_type} - User: {user_id} - IP: {ip_address}"
    
    if severity == 'CRITICAL':
        logger.critical(log_message, extra=log_data)
    elif severity == 'ERROR':
        logger.error(log_message, extra=log_data)
    elif severity == 'WARNING':
        logger.warning(log_message, extra=log_data)
    else:
        logger.info(log_message, extra=log_data)
    
    # Store in cache for real-time monitoring (last 1000 events)
    cache_key = 'security_events'
    events = cache.get(cache_key, [])
    events.append(log_data)
    events = events[-1000:]  # Keep last 1000 events
    cache.set(cache_key, events, 86400)  # Store for 24 hours


def track_failed_login(username, ip_address):
    """
    Track failed login attempts and implement account lockout.
    
    Args:
        username: Username that failed login
        ip_address: Client IP address
    
    Returns:
        Tuple of (is_locked, remaining_attempts, lockout_duration)
    """
    # Track per username
    username_key = f'failed_login_{username}'
    username_attempts = cache.get(username_key, 0) + 1
    cache.set(username_key, username_attempts, 3600)  # Reset after 1 hour
    
    # Track per IP
    ip_key = f'failed_login_ip_{ip_address}'
    ip_attempts = cache.get(ip_key, 0) + 1
    cache.set(ip_key, ip_attempts, 3600)
    
    # Log the failed attempt
    log_security_event(
        'login_failed',
        user_id=None,
        ip_address=ip_address,
        details={'username': username, 'attempt': username_attempts},
        severity='WARNING'
    )
    
    # Lock account after 5 failed attempts
    max_attempts = 5
    lockout_duration = 1800  # 30 minutes
    
    if username_attempts >= max_attempts:
        lockout_key = f'account_locked_{username}'
        cache.set(lockout_key, True, lockout_duration)
        
        log_security_event(
            'account_locked',
            user_id=None,
            ip_address=ip_address,
            details={'username': username, 'duration': lockout_duration},
            severity='ERROR'
        )
        
        return True, 0, lockout_duration
    
    # Block IP after 10 failed attempts
    if ip_attempts >= 10:
        from designs.security_middleware import IPBlockingMiddleware
        IPBlockingMiddleware.block_ip(ip_address, duration_seconds=3600)
        
        log_security_event(
            'ip_blocked',
            user_id=None,
            ip_address=ip_address,
            details={'reason': 'too_many_failed_logins'},
            severity='CRITICAL'
        )
    
    return False, max_attempts - username_attempts, 0


def is_account_locked(username):
    """
    Check if account is locked due to failed login attempts.
    
    Args:
        username: Username to check
    
    Returns:
        Tuple of (is_locked, remaining_lockout_seconds)
    """
    lockout_key = f'account_locked_{username}'
    ttl = cache.ttl(lockout_key)
    
    if ttl is None or ttl <= 0:
        return False, 0
    
    return True, ttl


def clear_failed_login_attempts(username):
    """
    Clear failed login attempts after successful login.
    
    Args:
        username: Username that successfully logged in
    """
    username_key = f'failed_login_{username}'
    cache.delete(username_key)


def generate_secure_token(length=32):
    """
    Generate a cryptographically secure random token.
    
    Args:
        length: Token length (default: 32)
    
    Returns:
        Secure random token string
    """
    import secrets
    return secrets.token_urlsafe(length)


def validate_api_key_format(api_key):
    """
    Validate API key format.
    
    Args:
        api_key: API key to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # API key should be alphanumeric with hyphens, 32-64 characters
    if not api_key or not isinstance(api_key, str):
        return False, 'API key is required'
    
    if len(api_key) < 32 or len(api_key) > 64:
        return False, 'Invalid API key length'
    
    if not re.match(r'^[a-zA-Z0-9_-]+$', api_key):
        return False, 'Invalid API key format'
    
    return True, None


def mask_sensitive_data(data, fields=None):
    """
    Mask sensitive fields in data for logging.
    
    Args:
        data: Dictionary containing data
        fields: List of field names to mask (default: common sensitive fields)
    
    Returns:
        Dictionary with masked sensitive fields
    """
    if fields is None:
        fields = [
            'password', 'token', 'secret', 'api_key', 'access_key',
            'secret_key', 'authorization', 'cookie', 'session'
        ]
    
    if not isinstance(data, dict):
        return data
    
    masked_data = data.copy()
    
    for key in masked_data:
        # Check if key contains sensitive field name
        if any(field in key.lower() for field in fields):
            masked_data[key] = '***MASKED***'
        
        # Recursively mask nested dictionaries
        elif isinstance(masked_data[key], dict):
            masked_data[key] = mask_sensitive_data(masked_data[key], fields)
    
    return masked_data


def detect_brute_force(identifier, max_attempts=10, window_seconds=60):
    """
    Detect brute force attempts based on request frequency.
    
    Args:
        identifier: Unique identifier (e.g., IP address, username)
        max_attempts: Maximum attempts allowed in window
        window_seconds: Time window in seconds
    
    Returns:
        True if brute force detected, False otherwise
    """
    cache_key = f'brute_force_{identifier}'
    attempts = cache.get(cache_key, [])
    now = datetime.now().timestamp()
    
    # Remove old attempts outside the window
    attempts = [ts for ts in attempts if now - ts < window_seconds]
    
    # Add current attempt
    attempts.append(now)
    
    # Store updated attempts
    cache.set(cache_key, attempts, window_seconds)
    
    # Check if threshold exceeded
    if len(attempts) > max_attempts:
        log_security_event(
            'brute_force_detected',
            user_id=None,
            ip_address=identifier,
            details={'attempts': len(attempts), 'window': window_seconds},
            severity='CRITICAL'
        )
        return True
    
    return False


class SecurityAuditLog:
    """
    Centralized security audit logging.
    """
    
    @staticmethod
    def log_login_success(user, ip_address, user_agent):
        """Log successful login."""
        log_security_event(
            'login_success',
            user_id=user.id,
            ip_address=ip_address,
            details={
                'username': user.username,
                'email': user.email,
                'user_agent': user_agent
            },
            severity='INFO'
        )
    
    @staticmethod
    def log_logout(user, ip_address):
        """Log logout."""
        log_security_event(
            'logout',
            user_id=user.id,
            ip_address=ip_address,
            details={'username': user.username},
            severity='INFO'
        )
    
    @staticmethod
    def log_password_change(user, ip_address, success=True):
        """Log password change attempt."""
        log_security_event(
            'password_change_success' if success else 'password_change_failed',
            user_id=user.id,
            ip_address=ip_address,
            details={'username': user.username},
            severity='INFO' if success else 'WARNING'
        )
    
    @staticmethod
    def log_permission_denied(user, resource, ip_address):
        """Log permission denied."""
        log_security_event(
            'permission_denied',
            user_id=user.id if user and user.is_authenticated else None,
            ip_address=ip_address,
            details={
                'resource': resource,
                'username': user.username if user and user.is_authenticated else 'anonymous'
            },
            severity='WARNING'
        )
    
    @staticmethod
    def log_data_access(user, resource_type, resource_id, action, ip_address):
        """Log sensitive data access."""
        log_security_event(
            'data_access',
            user_id=user.id,
            ip_address=ip_address,
            details={
                'username': user.username,
                'resource_type': resource_type,
                'resource_id': resource_id,
                'action': action
            },
            severity='INFO'
        )
    
    @staticmethod
    def log_api_key_created(user, key_name, ip_address):
        """Log API key creation."""
        log_security_event(
            'api_key_created',
            user_id=user.id,
            ip_address=ip_address,
            details={
                'username': user.username,
                'key_name': key_name
            },
            severity='INFO'
        )
    
    @staticmethod
    def log_api_key_revoked(user, key_name, ip_address):
        """Log API key revocation."""
        log_security_event(
            'api_key_revoked',
            user_id=user.id,
            ip_address=ip_address,
            details={
                'username': user.username,
                'key_name': key_name
            },
            severity='INFO'
        )
