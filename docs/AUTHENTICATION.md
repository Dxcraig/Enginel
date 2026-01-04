# Authentication & Token Management

Complete guide to authentication, authorization, and token management in Enginel.

## Table of Contents

- [Overview](#overview)
- [Authentication Methods](#authentication-methods)
- [Token Types](#token-types)
- [API Endpoints](#api-endpoints)
- [Usage Examples](#usage-examples)
- [Security Best Practices](#security-best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

Enginel provides a comprehensive authentication system with multiple authentication methods:

1. **Token Authentication** - Primary method for API access
2. **API Keys** - Long-lived tokens for service-to-service authentication
3. **Session Authentication** - Browser-based authentication
4. **Basic Authentication** - Fallback for simple clients

### Key Features

- ✅ **Expiring Tokens** - Access tokens expire after 24 hours (configurable)
- ✅ **Refresh Tokens** - Get new access tokens without re-authenticating
- ✅ **API Keys** - Long-lived tokens for automated systems and CI/CD pipelines
- ✅ **Multi-Device Sessions** - Track and manage sessions across devices
- ✅ **Token Revocation** - Revoke compromised tokens immediately
- ✅ **Security Controls** - IP restrictions, scope limiting, and usage tracking

## Authentication Methods

### 1. Token Authentication (Recommended)

**Best for:** Web/mobile apps, API clients

Uses Bearer tokens in the Authorization header:

```
Authorization: Token abc123def456...
```

**Features:**
- Expires after 24 hours (default, configurable)
- Can be refreshed without re-authentication
- Revocable at any time
- Tracked per device/session

### 2. API Key Authentication

**Best for:** CI/CD systems, automated scripts, service-to-service calls

Uses API keys in the Authorization header:

```
Authorization: ApiKey xyz789abc123...
```

**Features:**
- Long-lived (up to 10 years)
- Named for easy identification
- Optional IP restrictions
- Optional scope restrictions
- Usage tracking (last used timestamp)

### 3. Session Authentication

**Best for:** Django admin, browsable API

Uses Django's built-in session cookies. Automatically works in the browser.

### 4. Basic Authentication

**Best for:** Quick testing, simple clients

Uses username:password in Authorization header:

```
Authorization: Basic base64(username:password)
```

## Token Types

### Access Token

Short-lived token for API access (24 hours default).

```json
{
  "access_token": "abc123def456...",
  "expires_in": 86400,
  "token_type": "Bearer"
}
```

**Configuration:**
```python
# settings.py
TOKEN_EXPIRATION_HOURS = 24  # Default: 24 hours
```

### Refresh Token

Long-lived token for obtaining new access tokens (30 days default).

```json
{
  "refresh_token": "xyz789uvw012..."
}
```

**Configuration:**
```python
# settings.py
REFRESH_TOKEN_EXPIRATION_DAYS = 30  # Default: 30 days
```

### API Key

Very long-lived token for service accounts (1 year default, up to 10 years).

```json
{
  "key": "full-64-char-key-shown-once-only...",
  "name": "Jenkins CI",
  "expires_at": "2025-12-16T10:00:00Z"
}
```

**Configuration:**
```python
# settings.py
API_KEY_EXPIRATION_DAYS = 365  # Default: 1 year
```

## API Endpoints

### Authentication Endpoints

#### POST /api/auth/login/

Authenticate user and receive access + refresh tokens.

**Request:**
```json
{
  "username": "john@example.com",
  "password": "secretpassword",
  "device_name": "iPhone" // Optional
}
```

**Response (200):**
```json
{
  "access_token": "abc123def456...",
  "refresh_token": "xyz789uvw012...",
  "expires_in": 86400,
  "token_type": "Bearer",
  "user": {
    "id": 1,
    "username": "john",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe"
  }
}
```

**Response (401):**
```json
{
  "error": "Invalid credentials"
}
```

#### POST /api/auth/refresh/

Exchange refresh token for new access token.

**Request:**
```json
{
  "refresh_token": "xyz789uvw012..."
}
```

**Response (200):**
```json
{
  "access_token": "new_abc123...",
  "expires_in": 86400,
  "token_type": "Bearer"
}
```

**Response (401):**
```json
{
  "error": "Refresh token has expired or been revoked"
}
```

#### POST /api/auth/logout/

Revoke current access token and all refresh tokens.

**Headers:**
```
Authorization: Token abc123...
```

**Response (200):**
```json
{
  "message": "Successfully logged out"
}
```

#### POST /api/auth/revoke/

Revoke a specific refresh token.

**Headers:**
```
Authorization: Token abc123...
```

**Request:**
```json
{
  "refresh_token": "xyz789uvw012..."
}
```

**Response (200):**
```json
{
  "message": "Token revoked successfully"
}
```

#### GET /api/auth/verify/

Verify current token and get expiration info.

**Headers:**
```
Authorization: Token abc123...
```

**Response (200):**
```json
{
  "valid": true,
  "user": {
    "id": 1,
    "username": "john",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe"
  },
  "token_age_hours": 2.5,
  "expires_in_hours": 21.5
}
```

#### GET /api/auth/sessions/

List all active sessions (refresh tokens) for current user.

**Headers:**
```
Authorization: Token abc123...
```

**Response (200):**
```json
[
  {
    "id": 1,
    "device_name": "iPhone",
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0...",
    "created_at": "2024-01-01T10:00:00Z",
    "expires_at": "2024-01-31T10:00:00Z",
    "is_current": true
  },
  {
    "id": 2,
    "device_name": "MacBook",
    "ip_address": "192.168.1.101",
    "user_agent": "PostmanRuntime/7.32.0",
    "created_at": "2024-01-05T14:30:00Z",
    "expires_at": "2024-02-04T14:30:00Z",
    "is_current": false
  }
]
```

### API Key Management

#### GET /api/auth/api-keys/

List all API keys for current user.

**Headers:**
```
Authorization: Token abc123...
```

**Response (200):**
```json
[
  {
    "id": 1,
    "name": "Jenkins CI",
    "key_masked": "abcd...xyz9",
    "is_active": true,
    "created_at": "2024-01-01T10:00:00Z",
    "expires_at": "2025-01-01T10:00:00Z",
    "last_used_at": "2024-12-15T08:30:00Z",
    "allowed_ips": "10.0.0.0/24",
    "scopes": "read,write"
  }
]
```

#### POST /api/auth/api-keys/

Create a new API key.

**Headers:**
```
Authorization: Token abc123...
```

**Request:**
```json
{
  "name": "GitHub Actions",
  "expires_in_days": 365,
  "allowed_ips": "192.168.1.0/24,10.0.0.5",
  "scopes": "read,write"
}
```

**Response (201):**
```json
{
  "id": 2,
  "name": "GitHub Actions",
  "key": "full-64-character-api-key-shown-only-once-save-it-now...",
  "key_masked": "full...now.",
  "is_active": true,
  "created_at": "2024-12-16T10:00:00Z",
  "expires_at": "2025-12-16T10:00:00Z",
  "last_used_at": null,
  "allowed_ips": "192.168.1.0/24,10.0.0.5",
  "scopes": "read,write"
}
```

**⚠️ Important:** The full API key is only shown once on creation. Save it securely!

#### GET /api/auth/api-keys/{id}/

Retrieve details of a specific API key.

**Headers:**
```
Authorization: Token abc123...
```

**Response (200):**
```json
{
  "id": 1,
  "name": "Jenkins CI",
  "key_masked": "abcd...xyz9",
  "is_active": true,
  "created_at": "2024-01-01T10:00:00Z",
  "expires_at": "2025-01-01T10:00:00Z",
  "last_used_at": "2024-12-15T08:30:00Z",
  "allowed_ips": "10.0.0.0/24",
  "scopes": "read,write"
}
```

#### DELETE /api/auth/api-keys/{id}/

Revoke (soft delete) an API key.

**Headers:**
```
Authorization: Token abc123...
```

**Response (204):** No content

#### POST /api/auth/api-keys/{id}/revoke/

Alternative endpoint to revoke an API key.

**Headers:**
```
Authorization: Token abc123...
```

**Response (200):**
```json
{
  "message": "API key revoked successfully"
}
```

## Usage Examples

### Example 1: Web Application Login Flow

```javascript
// 1. Login
const loginResponse = await fetch('http://localhost:8000/api/auth/login/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'john@example.com',
    password: 'secretpassword',
    device_name: 'Chrome Browser'
  })
});

const { access_token, refresh_token, user } = await loginResponse.json();

// Store tokens securely
localStorage.setItem('access_token', access_token);
localStorage.setItem('refresh_token', refresh_token);

// 2. Make authenticated API calls
const response = await fetch('http://localhost:8000/api/designs/', {
  headers: {
    'Authorization': `Token ${access_token}`
  }
});

// 3. When token expires, refresh it
if (response.status === 401) {
  const refreshResponse = await fetch('http://localhost:8000/api/auth/refresh/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      refresh_token: localStorage.getItem('refresh_token')
    })
  });
  
  const { access_token: new_token } = await refreshResponse.json();
  localStorage.setItem('access_token', new_token);
  
  // Retry original request with new token
  const retryResponse = await fetch('http://localhost:8000/api/designs/', {
    headers: {
      'Authorization': `Token ${new_token}`
    }
  });
}

// 4. Logout
await fetch('http://localhost:8000/api/auth/logout/', {
  method: 'POST',
  headers: {
    'Authorization': `Token ${access_token}`
  }
});

localStorage.removeItem('access_token');
localStorage.removeItem('refresh_token');
```

### Example 2: Python Script with API Key

```python
import requests
import os

# Store API key in environment variable
API_KEY = os.getenv('ENGINEL_API_KEY')
BASE_URL = 'http://localhost:8000'

# Make authenticated requests
headers = {
    'Authorization': f'ApiKey {API_KEY}'
}

# Upload a design
with open('turbine_blade.step', 'rb') as f:
    response = requests.post(
        f'{BASE_URL}/api/designs/',
        headers=headers,
        files={'file': f},
        data={
            'name': 'Turbine Blade v3',
            'series': 'TB-001'
        }
    )

design = response.json()
print(f"Created design: {design['id']}")

# Check analysis job status
job_id = design['analysis_job']
response = requests.get(
    f'{BASE_URL}/api/analysis-jobs/{job_id}/',
    headers=headers
)

job = response.json()
print(f"Job status: {job['status']}")
```

### Example 3: cURL Commands

```bash
# Login
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"john@example.com","password":"secretpassword"}'

# Save the tokens
export ACCESS_TOKEN="abc123def456..."
export REFRESH_TOKEN="xyz789uvw012..."

# Make authenticated request
curl http://localhost:8000/api/designs/ \
  -H "Authorization: Token $ACCESS_TOKEN"

# Refresh token
curl -X POST http://localhost:8000/api/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH_TOKEN\"}"

# Create API key
curl -X POST http://localhost:8000/api/auth/api-keys/ \
  -H "Authorization: Token $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jenkins CI",
    "expires_in_days": 365,
    "scopes": "read,write"
  }'

# Use API key
export API_KEY="xyz789abc123..."
curl http://localhost:8000/api/designs/ \
  -H "Authorization: ApiKey $API_KEY"

# Logout
curl -X POST http://localhost:8000/api/auth/logout/ \
  -H "Authorization: Token $ACCESS_TOKEN"
```

### Example 4: Session Management

```javascript
// List all active sessions
const sessions = await fetch('http://localhost:8000/api/auth/sessions/', {
  headers: { 'Authorization': `Token ${access_token}` }
}).then(r => r.json());

console.log('Active sessions:', sessions);

// Revoke a specific session (e.g., lost phone)
const oldSessionToken = sessions.find(s => s.device_name === 'iPhone')?.id;

await fetch('http://localhost:8000/api/auth/revoke/', {
  method: 'POST',
  headers: {
    'Authorization': `Token ${access_token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    refresh_token: oldSessionToken
  })
});

// Logout from all devices
await fetch('http://localhost:8000/api/auth/logout/', {
  method: 'POST',
  headers: { 'Authorization': `Token ${access_token}` }
});
```

## Security Best Practices

### Token Storage

**✅ DO:**
- Store tokens in httpOnly cookies (web apps)
- Use secure storage APIs (iOS Keychain, Android Keystore)
- Encrypt tokens before storing (mobile apps)
- Use environment variables for API keys (servers)

**❌ DON'T:**
- Store tokens in localStorage (XSS vulnerable)
- Commit tokens to git repositories
- Share tokens between users
- Log tokens in application logs

### Token Transmission

**✅ DO:**
- Always use HTTPS in production
- Use Authorization header (not query params)
- Rotate tokens regularly
- Implement token expiration

**❌ DON'T:**
- Send tokens in URL query parameters
- Send tokens over HTTP (unencrypted)
- Reuse tokens across different apps

### API Key Management

**✅ DO:**
- Create separate API keys for each service
- Use descriptive names for API keys
- Set expiration dates on API keys
- Restrict API keys by IP address when possible
- Limit API key scopes to minimum required
- Rotate API keys regularly
- Revoke unused API keys

**❌ DON'T:**
- Share API keys between services
- Create API keys without expiration
- Hardcode API keys in source code
- Give API keys broader permissions than needed

### Session Management

**✅ DO:**
- Monitor active sessions regularly
- Revoke sessions on password change
- Implement "logout from all devices" feature
- Track suspicious login activity
- Notify users of new logins

**❌ DON'T:**
- Allow unlimited concurrent sessions
- Keep sessions alive indefinitely
- Ignore suspicious login patterns

### Configuration

Recommended production settings:

```python
# settings.py

# Token expiration (hours)
TOKEN_EXPIRATION_HOURS = 12  # Shorter for high-security apps

# Refresh token expiration (days)
REFRESH_TOKEN_EXPIRATION_DAYS = 30

# API key expiration (days)
API_KEY_EXPIRATION_DAYS = 90  # Rotate quarterly

# Require HTTPS in production
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Security headers
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

## Troubleshooting

### Token Expired Error

**Problem:**
```json
{
  "detail": "Token has expired"
}
```

**Solution:**
1. Use the refresh token to get a new access token
2. If refresh token also expired, user must login again

```javascript
// Auto-retry with refresh
async function fetchWithRefresh(url, options) {
  let response = await fetch(url, options);
  
  if (response.status === 401) {
    // Try to refresh token
    const refreshResponse = await fetch('/api/auth/refresh/', {
      method: 'POST',
      body: JSON.stringify({
        refresh_token: localStorage.getItem('refresh_token')
      })
    });
    
    if (refreshResponse.ok) {
      const { access_token } = await refreshResponse.json();
      localStorage.setItem('access_token', access_token);
      
      // Retry with new token
      options.headers['Authorization'] = `Token ${access_token}`;
      response = await fetch(url, options);
    }
  }
  
  return response;
}
```

### Invalid Token Error

**Problem:**
```json
{
  "detail": "Invalid token"
}
```

**Possible Causes:**
1. Token was revoked (user logged out)
2. Token was manually deleted from database
3. Wrong authentication header format

**Solution:**
1. Clear stored tokens
2. Redirect user to login
3. Check header format: `Authorization: Token abc123...`

### API Key Not Working

**Problem:**
```json
{
  "detail": "Invalid API key"
}
```

**Checklist:**
- [ ] Using correct header format: `Authorization: ApiKey xyz...`
- [ ] API key is still active (not revoked)
- [ ] API key hasn't expired
- [ ] Request is from allowed IP (if IP restrictions set)
- [ ] Request is within allowed scopes

### Cannot Create API Key

**Problem:**
```json
{
  "detail": "Authentication credentials were not provided"
}
```

**Solution:**
Must be authenticated with access token to create API keys:

```bash
# First login to get access token
curl -X POST http://localhost:8000/api/auth/login/ \
  -d '{"username":"user","password":"pass"}'

# Then use access token to create API key
curl -X POST http://localhost:8000/api/auth/api-keys/ \
  -H "Authorization: Token <access_token>" \
  -d '{"name":"MyKey","expires_in_days":365}'
```

### Refresh Token Expired

**Problem:**
```json
{
  "error": "Refresh token has expired or been revoked"
}
```

**Solution:**
Cannot refresh automatically. User must login again with username/password.

**Prevention:**
- Set longer refresh token expiration (30+ days)
- Implement "remember me" feature with longer expiration
- Send email reminder before refresh token expires

### Too Many Sessions

**Problem:**
User has many old sessions accumulating.

**Solution:**
Implement automatic cleanup:

```python
# Run periodically (e.g., daily cron job)
from django.utils import timezone
from designs.models import RefreshToken

# Delete expired refresh tokens
RefreshToken.objects.filter(
    expires_at__lt=timezone.now()
).delete()

# Optional: Limit active sessions per user
from django.contrib.auth import get_user_model

User = get_user_model()
for user in User.objects.all():
    # Keep only 5 most recent sessions
    old_tokens = RefreshToken.objects.filter(
        user=user,
        is_revoked=False
    ).order_by('-created_at')[5:]
    
    for token in old_tokens:
        token.is_revoked = True
        token.save()
```

## Migration from Old System

If migrating from session-only authentication:

### Step 1: Add Token Support

Existing session auth continues to work. Add token authentication alongside:

```python
# Settings remain backward compatible
'DEFAULT_AUTHENTICATION_CLASSES': [
    'designs.authentication.ExpiringTokenAuthentication',
    'designs.authentication.APIKeyAuthentication',
    'rest_framework.authentication.SessionAuthentication',  # Still works
    'rest_framework.authentication.BasicAuthentication',
]
```

### Step 2: Run Migrations

```bash
docker exec enginel_app python manage.py makemigrations
docker exec enginel_app python manage.py migrate
```

### Step 3: Generate Tokens for Existing Users

```python
# Management command or shell
from designs.models import CustomUser
from rest_framework.authtoken.models import Token

for user in CustomUser.objects.all():
    Token.objects.get_or_create(user=user)
```

### Step 4: Update Clients

Gradually migrate clients from session to token auth:

```javascript
// Old (session-based)
fetch('/api/designs/', { credentials: 'include' })

// New (token-based)
fetch('/api/designs/', {
  headers: { 'Authorization': `Token ${token}` }
})
```

### Step 5: Monitor Usage

Track authentication method usage:

```python
# Add middleware to log auth methods
class AuthMethodLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if hasattr(request, 'auth'):
            auth_type = type(request.auth).__name__
            # Log auth_type for analytics
        
        return self.get_response(request)
```

## Performance Considerations

### Database Queries

Token authentication adds 1 database query per request:
- Fetch token by key
- Join with user table

Optimize with:
- Database indexes on token key (already added)
- Connection pooling (already configured)
- Read replicas for token lookups (production)

### Token Validation Caching

For very high traffic, cache token validations:

```python
from django.core.cache import cache

class CachedExpiringTokenAuthentication(ExpiringTokenAuthentication):
    def authenticate_credentials(self, key):
        # Check cache first
        cache_key = f'token:{key}'
        cached_user = cache.get(cache_key)
        
        if cached_user:
            return (cached_user, None)
        
        # Fall back to database
        user, token = super().authenticate_credentials(key)
        
        # Cache for 5 minutes
        cache.set(cache_key, user, 300)
        
        return (user, token)
```

### API Key Last Used Updates

Last used timestamp updates can create write contention. Consider:
- Update only if > 1 hour since last update
- Use async task to update timestamp
- Disable last used tracking in high-throughput scenarios

## Support

For authentication issues:
1. Check this documentation
2. Review error logs: `/api/monitoring/errors/`
3. Verify token with: `/api/auth/verify/`
4. Check active sessions: `/api/auth/sessions/`

---

**Related Documentation:**
- [Multi-Tenant Organizations](MULTI_TENANT.md)
- [Audit Logging](AUDIT_LOGGING.md)
- [Error Handling](ERROR_HANDLING.md)
