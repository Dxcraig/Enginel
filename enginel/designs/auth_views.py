"""
Token management views for authentication.

Provides endpoints for:
- Token generation (login)
- Token refresh
- Token revocation
- API key management
"""
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.utils import timezone
from datetime import timedelta
from django.conf import settings

from .models import CustomUser, APIKey, RefreshToken
from .serializers import (
    LoginSerializer,
    TokenSerializer,
    RefreshTokenSerializer,
    APIKeySerializer,
    CreateAPIKeySerializer,
)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    Authenticate user and return access token + refresh token.
    
    POST /api/auth/login/
    Body:
    {
        "username": "john@example.com",
        "password": "secretpassword"
    }
    
    Returns:
    {
        "access_token": "abc123...",
        "refresh_token": "xyz789...",
        "expires_in": 86400,
        "token_type": "Bearer",
        "user": {
            "id": 1,
            "username": "john",
            "email": "john@example.com"
        }
    }
    """
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    username = serializer.validated_data['username']
    password = serializer.validated_data['password']
    
    # Authenticate user
    user = authenticate(username=username, password=password)
    
    if not user:
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    if not user.is_active:
        return Response(
            {'error': 'User account is disabled'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Create or get access token
    token, created = Token.objects.get_or_create(user=user)
    
    # If token exists but is old, regenerate it
    if not created:
        token_age = timezone.now() - token.created
        expiration_hours = getattr(settings, 'TOKEN_EXPIRATION_HOURS', 24)
        
        if token_age > timedelta(hours=expiration_hours):
            token.delete()
            token = Token.objects.create(user=user)
    
    # Create refresh token
    refresh_token = RefreshToken.objects.create(
        user=user,
        access_token_key=token.key,
        device_name=request.data.get('device_name', ''),
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
    )
    
    # Calculate expiration time
    expiration_hours = getattr(settings, 'TOKEN_EXPIRATION_HOURS', 24)
    expires_in = int(timedelta(hours=expiration_hours).total_seconds())
    
    return Response({
        'access_token': token.key,
        'refresh_token': refresh_token.token,
        'expires_in': expires_in,
        'token_type': 'Bearer',
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
        }
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token_view(request):
    """
    Exchange refresh token for new access token.
    
    POST /api/auth/refresh/
    Body:
    {
        "refresh_token": "xyz789..."
    }
    
    Returns:
    {
        "access_token": "new_abc123...",
        "expires_in": 86400,
        "token_type": "Bearer"
    }
    """
    serializer = RefreshTokenSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    refresh_token_str = serializer.validated_data['refresh_token']
    
    try:
        refresh_token = RefreshToken.objects.select_related('user').get(
            token=refresh_token_str
        )
    except RefreshToken.DoesNotExist:
        return Response(
            {'error': 'Invalid refresh token'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Check if refresh token is valid
    if not refresh_token.is_valid():
        return Response(
            {'error': 'Refresh token has expired or been revoked'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Revoke old access token
    try:
        old_token = Token.objects.get(key=refresh_token.access_token_key)
        old_token.delete()
    except Token.DoesNotExist:
        pass
    
    # Create new access token
    new_token = Token.objects.create(user=refresh_token.user)
    
    # Update refresh token with new access token key
    refresh_token.access_token_key = new_token.key
    refresh_token.save()
    
    # Calculate expiration time
    expiration_hours = getattr(settings, 'TOKEN_EXPIRATION_HOURS', 24)
    expires_in = int(timedelta(hours=expiration_hours).total_seconds())
    
    return Response({
        'access_token': new_token.key,
        'expires_in': expires_in,
        'token_type': 'Bearer'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Revoke user's current access token and all refresh tokens.
    
    POST /api/auth/logout/
    Headers:
        Authorization: Token abc123...
    
    Returns:
    {
        "message": "Successfully logged out"
    }
    """
    # Delete access token
    request.user.auth_token.delete()
    
    # Revoke all refresh tokens
    RefreshToken.objects.filter(user=request.user).update(is_revoked=True)
    
    return Response({'message': 'Successfully logged out'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def revoke_token_view(request):
    """
    Revoke a specific refresh token.
    
    POST /api/auth/revoke/
    Body:
    {
        "refresh_token": "xyz789..."
    }
    
    Returns:
    {
        "message": "Token revoked successfully"
    }
    """
    serializer = RefreshTokenSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    refresh_token_str = serializer.validated_data['refresh_token']
    
    try:
        refresh_token = RefreshToken.objects.get(
            token=refresh_token_str,
            user=request.user
        )
        refresh_token.is_revoked = True
        refresh_token.save()
        
        return Response({'message': 'Token revoked successfully'})
    except RefreshToken.DoesNotExist:
        return Response(
            {'error': 'Invalid refresh token'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_sessions_view(request):
    """
    List all active sessions (refresh tokens) for the current user.
    
    GET /api/auth/sessions/
    
    Returns:
    [
        {
            "id": 1,
            "device_name": "iPhone",
            "ip_address": "192.168.1.1",
            "created_at": "2024-01-01T10:00:00Z",
            "expires_at": "2024-01-31T10:00:00Z",
            "is_current": true
        }
    ]
    """
    refresh_tokens = RefreshToken.objects.filter(
        user=request.user,
        is_revoked=False,
        expires_at__gt=timezone.now()
    )
    
    # Identify current session
    current_token_key = None
    if hasattr(request.user, 'auth_token'):
        current_token_key = request.user.auth_token.key
    
    sessions = []
    for rt in refresh_tokens:
        sessions.append({
            'id': rt.id,
            'device_name': rt.device_name or 'Unknown Device',
            'ip_address': rt.ip_address,
            'user_agent': rt.user_agent[:100] if rt.user_agent else '',
            'created_at': rt.created_at,
            'expires_at': rt.expires_at,
            'is_current': rt.access_token_key == current_token_key
        })
    
    return Response(sessions)


# API Key Management Views

class APIKeyListCreateView(generics.ListCreateAPIView):
    """
    List all API keys for current user or create a new one.
    
    GET /api/auth/api-keys/
    Returns list of API keys (key is masked except on creation)
    
    POST /api/auth/api-keys/
    Body:
    {
        "name": "Jenkins CI",
        "expires_in_days": 365,
        "scopes": "read,write"
    }
    
    Returns full API key only once on creation.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = APIKeySerializer
    
    def get_queryset(self):
        return APIKey.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        # Set expiration date
        expires_in_days = self.request.data.get('expires_in_days')
        expires_at = None
        
        if expires_in_days:
            expires_at = timezone.now() + timedelta(days=int(expires_in_days))
        else:
            # Default to 1 year
            default_days = getattr(settings, 'API_KEY_EXPIRATION_DAYS', 365)
            expires_at = timezone.now() + timedelta(days=default_days)
        
        # Save the API key
        api_key = serializer.save(
            user=self.request.user,
            expires_at=expires_at
        )
        
        # Mark to show full key in response
        api_key._show_full_key = True


class APIKeyDetailView(generics.RetrieveDestroyAPIView):
    """
    Retrieve or delete (revoke) an API key.
    
    GET /api/auth/api-keys/{id}/
    Returns details of specific API key
    
    DELETE /api/auth/api-keys/{id}/
    Revokes the API key (soft delete)
    """
    permission_classes = [IsAuthenticated]
    serializer_class = APIKeySerializer
    
    def get_queryset(self):
        return APIKey.objects.filter(user=self.request.user)
    
    def perform_destroy(self, instance):
        # Soft delete - mark as inactive instead of deleting
        instance.is_active = False
        instance.save()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def revoke_api_key_view(request, pk):
    """
    Revoke an API key.
    
    POST /api/auth/api-keys/{id}/revoke/
    """
    try:
        api_key = APIKey.objects.get(pk=pk, user=request.user)
        api_key.is_active = False
        api_key.save()
        
        return Response({'message': 'API key revoked successfully'})
    except APIKey.DoesNotExist:
        return Response(
            {'error': 'API key not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verify_token_view(request):
    """
    Verify current token is valid and return user info.
    
    GET /api/auth/verify/
    Headers:
        Authorization: Token abc123...
    
    Returns:
    {
        "valid": true,
        "user": {
            "id": 1,
            "username": "john",
            "email": "john@example.com"
        },
        "token_age_hours": 2.5,
        "expires_in_hours": 21.5
    }
    """
    token = request.user.auth_token
    token_age = timezone.now() - token.created
    
    expiration_hours = getattr(settings, 'TOKEN_EXPIRATION_HOURS', 24)
    expires_in = timedelta(hours=expiration_hours) - token_age
    
    return Response({
        'valid': True,
        'user': {
            'id': request.user.id,
            'username': request.user.username,
            'email': request.user.email,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
        },
        'token_age_hours': round(token_age.total_seconds() / 3600, 2),
        'expires_in_hours': round(max(0, expires_in.total_seconds()) / 3600, 2)
    })
