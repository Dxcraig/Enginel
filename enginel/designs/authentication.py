"""
Enhanced authentication backend for Enginel.

Provides:
- Expiring token authentication
- API key authentication for service-to-service calls
- Refresh token mechanism
- Token revocation
"""
from django.utils import timezone
from django.conf import settings
from rest_framework.authentication import TokenAuthentication
from rest_framework import exceptions
from datetime import timedelta


class ExpiringTokenAuthentication(TokenAuthentication):
    """
    Token authentication with expiration support.
    
    Tokens expire after TOKEN_EXPIRATION_HOURS (default: 24 hours).
    Returns 401 with clear message when token is expired.
    """
    
    def authenticate_credentials(self, key):
        """
        Validate token and check expiration.
        """
        model = self.get_model()
        
        try:
            token = model.objects.select_related('user').get(key=key)
        except model.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token')
        
        if not token.user.is_active:
            raise exceptions.AuthenticationFailed('User inactive or deleted')
        
        # Check token expiration
        token_age = timezone.now() - token.created
        expiration_hours = getattr(settings, 'TOKEN_EXPIRATION_HOURS', 24)
        
        if token_age > timedelta(hours=expiration_hours):
            raise exceptions.AuthenticationFailed('Token has expired')
        
        return (token.user, token)


class APIKeyAuthentication(TokenAuthentication):
    """
    API Key authentication for service-to-service calls.
    
    Uses a different model (APIKey) with longer expiration.
    Expects header: Authorization: ApiKey <key>
    """
    keyword = 'ApiKey'
    
    def get_model(self):
        """Use APIKey model instead of Token."""
        from .models import APIKey
        return APIKey
    
    def authenticate_credentials(self, key):
        """
        Validate API key and check expiration.
        """
        model = self.get_model()
        
        try:
            api_key = model.objects.select_related('user').get(key=key)
        except model.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid API key')
        
        if not api_key.is_active:
            raise exceptions.AuthenticationFailed('API key has been revoked')
        
        if not api_key.user.is_active:
            raise exceptions.AuthenticationFailed('User inactive or deleted')
        
        # Check API key expiration
        if api_key.expires_at and timezone.now() > api_key.expires_at:
            api_key.is_active = False
            api_key.save()
            raise exceptions.AuthenticationFailed('API key has expired')
        
        # Update last used timestamp
        api_key.last_used_at = timezone.now()
        api_key.save(update_fields=['last_used_at'])
        
        return (api_key.user, api_key)
