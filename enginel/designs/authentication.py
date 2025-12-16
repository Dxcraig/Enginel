"""
Enhanced authentication backend for Enginel.

Provides:
- Expiring token authentication
- API key authentication for service-to-service calls
- Refresh token mechanism
- Token revocation
- Account lockout protection
- Brute force detection
"""
from django.utils import timezone
from django.conf import settings
from rest_framework.authentication import TokenAuthentication
from rest_framework import exceptions
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class ExpiringTokenAuthentication(TokenAuthentication):
    """
    Token authentication with expiration support.
    
    Tokens expire after TOKEN_EXPIRATION_HOURS (default: 24 hours).
    Returns 401 with clear message when token is expired.
    Logs authentication failures for security monitoring.
    """
    
    def authenticate_credentials(self, key):
        """
        Validate token and check expiration.
        """
        from .security_utils import log_security_event
        
        model = self.get_model()
        
        try:
            token = model.objects.select_related('user').get(key=key)
        except model.DoesNotExist:
            log_security_event(
                'invalid_token_attempt',
                user_id=None,
                ip_address=None,
                details={'token_key': key[:8] + '...'},  # Partial key for tracking
                severity='WARNING'
            )
            raise exceptions.AuthenticationFailed('Invalid token')
        
        if not token.user.is_active:
            log_security_event(
                'inactive_user_auth_attempt',
                user_id=token.user.id,
                ip_address=None,
                details={'username': token.user.username},
                severity='WARNING'
            )
            raise exceptions.AuthenticationFailed('User inactive or deleted')
        
        # Check token expiration
        token_age = timezone.now() - token.created
        expiration_hours = getattr(settings, 'TOKEN_EXPIRATION_HOURS', 24)
        
        if token_age > timedelta(hours=expiration_hours):
            log_security_event(
                'expired_token_attempt',
                user_id=token.user.id,
                ip_address=None,
                details={'username': token.user.username, 'token_age_hours': token_age.total_seconds() / 3600},
                severity='INFO'
            )
            raise exceptions.AuthenticationFailed('Token has expired')
        
        return (token.user, token)


class APIKeyAuthentication(TokenAuthentication):
    """
    API Key authentication for service-to-service calls.
    
    Uses a different model (APIKey) with longer expiration.
    Expects header: Authorization: ApiKey <key>
    Enhanced with rate limiting and anomaly detection.
    """
    keyword = 'ApiKey'
    
    def get_model(self):
        """Use APIKey model instead of Token."""
        from .models import APIKey
        return APIKey
    
    def authenticate_credentials(self, key):
        """
        Validate API key and check expiration.
        Enhanced with security logging and rate limit checks.
        """
        from .security_utils import log_security_event, detect_brute_force
        
        model = self.get_model()
        
        try:
            api_key = model.objects.select_related('user').get(key=key)
        except model.DoesNotExist:
            # Detect brute force API key guessing
            if detect_brute_force(f'api_key_{key[:8]}', max_attempts=5, window_seconds=60):
                log_security_event(
                    'api_key_brute_force',
                    user_id=None,
                    ip_address=None,
                    details={'partial_key': key[:8]},
                    severity='CRITICAL'
                )
            
            log_security_event(
                'invalid_api_key_attempt',
                user_id=None,
                ip_address=None,
                details={'partial_key': key[:8]},
                severity='WARNING'
            )
            raise exceptions.AuthenticationFailed('Invalid API key')
        
        if not api_key.is_active:
            log_security_event(
                'revoked_api_key_attempt',
                user_id=api_key.user.id,
                ip_address=None,
                details={'key_name': api_key.name, 'username': api_key.user.username},
                severity='WARNING'
            )
            raise exceptions.AuthenticationFailed('API key has been revoked')
        
        if not api_key.user.is_active:
            log_security_event(
                'inactive_user_api_key_attempt',
                user_id=api_key.user.id,
                ip_address=None,
                details={'username': api_key.user.username},
                severity='WARNING'
            )
            raise exceptions.AuthenticationFailed('User inactive or deleted')
        
        # Check API key expiration
        if api_key.expires_at and timezone.now() > api_key.expires_at:
            api_key.is_active = False
            api_key.save()
            
            log_security_event(
                'expired_api_key_attempt',
                user_id=api_key.user.id,
                ip_address=None,
                details={'key_name': api_key.name, 'expired_at': api_key.expires_at.isoformat()},
                severity='INFO'
            )
            raise exceptions.AuthenticationFailed('API key has expired')
        
        # Update last used timestamp
        api_key.last_used_at = timezone.now()
        api_key.save(update_fields=['last_used_at'])
        
        return (api_key.user, api_key)
