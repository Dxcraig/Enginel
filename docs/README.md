# Enginel API Documentation

Complete documentation for the Enginel Engineering Intelligence Kernel.

## Quick Start

- **[API Quick Start Guide](API_QUICKSTART.md)** - Get started with the API in 5 minutes
- **[API Reference](API_REFERENCE.md)** - Complete endpoint reference
- **[OpenAPI Specification](openapi.yaml)** - Machine-readable API spec for Swagger/tooling

## Core Features

### Authentication & Security
- **[Authentication](AUTHENTICATION.md)** - Token authentication, API keys, refresh tokens, and session management

### Design Management
- **[BOM Extraction](BOM_EXTRACTION.md)** - Bill of Materials extraction from CAD assemblies
- **[Unit Conversion](UNIT_CONVERSION.md)** - Automatic unit detection and conversion

### Data & Search
- **[Audit Logging](AUDIT_LOGGING.md)** - Compliance audit trail and activity tracking
- **[Search & Filtering](SEARCH_FILTERING.md)** - Advanced search, filtering, and ordering capabilities
- **[Caching](CACHING.md)** - Redis-based caching for performance optimization

### Operations
- **[Multi-Tenant Organizations](MULTI_TENANT.md)** - Organization isolation and access control
- **[Background Jobs](BACKGROUND_JOBS.md)** - Async task processing and monitoring
- **[Email Notifications](EMAIL_NOTIFICATIONS.md)** - User notifications and preferences
- **[Error Handling](ERROR_HANDLING.md)** - Error tracking, monitoring, and recovery

## Documentation Index

| Document | Description | Topics Covered |
|----------|-------------|----------------|
| [API Reference](API_REFERENCE.md) | Complete REST API documentation | All endpoints, request/response schemas, error codes |
| [API Quick Start](API_QUICKSTART.md) | Getting started tutorial | Authentication, basic workflows, Python examples |
| [OpenAPI Spec](openapi.yaml) | Machine-readable API specification | Swagger UI, client generation, validation |
| [Authentication](AUTHENTICATION.md) | Authentication system guide | Token auth, API keys, refresh tokens, security |
| [Audit Logging](AUDIT_LOGGING.md) | Compliance audit trail | Activity tracking, compliance reporting, queries |
| [Background Jobs](BACKGROUND_JOBS.md) | Async task monitoring | Job tracking, progress monitoring, metrics |
| [BOM Extraction](BOM_EXTRACTION.md) | Bill of Materials extraction | Assembly parsing, hierarchy, part lists |
| [Caching](CACHING.md) | Performance optimization | Redis caching, cache strategies, invalidation |
| [Email Notifications](EMAIL_NOTIFICATIONS.md) | Email notification system | User preferences, notification types, delivery |
| [Error Handling](ERROR_HANDLING.md) | Error tracking & monitoring | Error logging, performance monitoring, debugging |
| [Multi-Tenant](MULTI_TENANT.md) | Organization management | Multi-tenancy, roles, permissions, isolation |
| [Search & Filtering](SEARCH_FILTERING.md) | Search capabilities | Full-text search, filtering, ordering, pagination |
| [Unit Conversion](UNIT_CONVERSION.md) | Unit handling | Auto-detection, conversion, validation |

## Getting Started

1. **Start Here**: Read the [API Quick Start Guide](API_QUICKSTART.md)
2. **Authentication**: Set up authentication using the [Authentication Guide](AUTHENTICATION.md)
3. **API Reference**: Browse all endpoints in the [API Reference](API_REFERENCE.md)
4. **Deep Dive**: Explore feature-specific guides for your use case

## API Overview

### Base URL
```
http://localhost:8000/api  (development)
https://api.enginel.example.com/api  (production)
```

### Authentication
```bash
# Get access token
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"your-username","password":"your-password"}'

# Use token in requests
curl -H "Authorization: Token <your-token>" \
  http://localhost:8000/api/designs/
```

### Key Endpoints

| Category | Endpoint | Description |
|----------|----------|-------------|
| Auth | `/api/auth/login/` | User authentication |
| Organizations | `/api/organizations/` | Multi-tenant organizations |
| Users | `/api/users/` | User management |
| Design Series | `/api/series/` | Part number families |
| Designs | `/api/designs/` | CAD file uploads and metadata |
| BOM | `/api/bom-nodes/` | Bill of Materials hierarchy |
| Jobs | `/api/analysis-jobs/` | Background task tracking |
| Reviews | `/api/reviews/` | Design review workflows |
| Markups | `/api/markups/` | 3D annotations and comments |
| Audit Logs | `/api/audit-logs/` | Compliance audit trail |
| Notifications | `/api/notifications/` | Email notification management |

## Common Use Cases

### Upload and Process a Design

```python
import requests

# 1. Authenticate
response = requests.post('http://localhost:8000/api/auth/login/', 
    json={'username': 'user', 'password': 'pass'})
token = response.json()['access_token']
headers = {'Authorization': f'Token {token}'}

# 2. Create design series
series = requests.post('http://localhost:8000/api/series/',
    headers=headers,
    json={
        'organization': 'org-uuid',
        'part_number': 'PART-001',
        'name': 'My Part'
    }).json()

# 3. Upload design file
with open('design.step', 'rb') as f:
    files = {'file': f}
    data = {
        'series': series['id'],
        'filename': 'design.step'
    }
    design = requests.post('http://localhost:8000/api/designs/',
        headers=headers,
        files=files,
        data=data).json()

# 4. Check processing status
status = requests.get(f"http://localhost:8000/api/designs/{design['id']}/",
    headers=headers).json()
print(f"Status: {status['status']}")
```

### Query Audit Logs

```python
# Get recent activity
logs = requests.get('http://localhost:8000/api/audit-logs/',
    headers=headers,
    params={
        'action': 'UPLOAD',
        'ordering': '-timestamp',
        'page_size': 50
    }).json()

for log in logs['results']:
    print(f"{log['timestamp']}: {log['actor_username']} - {log['action']}")
```

### Manage Notifications

```python
# Update notification preferences
requests.patch('http://localhost:8000/api/notifications/preferences/',
    headers=headers,
    json={
        'email_enabled': True,
        'delivery_method': 'HOURLY',
        'notify_design_approved': True
    })

# Get notification history
history = requests.get('http://localhost:8000/api/notifications/history/',
    headers=headers).json()
```

## Tools & Integration

### Swagger UI

View interactive API documentation:
1. Copy contents of [openapi.yaml](openapi.yaml)
2. Open https://editor.swagger.io
3. Paste YAML to explore endpoints interactively

### Generate Python Client

```bash
# Install OpenAPI Generator
npm install -g @openapitools/openapi-generator-cli

# Generate Python client
openapi-generator-cli generate \
  -i openapi.yaml \
  -g python \
  -o ./enginel-client
```

### Postman Collection

Import [openapi.yaml](openapi.yaml) into Postman for easy testing:
1. Open Postman
2. Import → Upload Files
3. Select openapi.yaml
4. All endpoints will be available in collection

## API Features

### Pagination

All list endpoints support pagination:
```bash
GET /api/designs/?page=2&page_size=50
```

### Filtering

Filter by field values:
```bash
GET /api/designs/?status=APPROVED&classification=ITAR
```

### Searching

Full-text search across multiple fields:
```bash
GET /api/designs/?search=engine+mount
```

### Ordering

Sort results by any field:
```bash
GET /api/designs/?ordering=-created_at
```

### Field Selection

Request specific fields only:
```bash
GET /api/designs/?fields=id,filename,status
```

## Error Handling

All errors return consistent JSON format:
```json
{
  "error": "Validation error",
  "detail": "Invalid part number format",
  "code": "VALIDATION_ERROR"
}
```

Common HTTP status codes:
- `200 OK` - Success
- `201 Created` - Resource created
- `400 Bad Request` - Invalid input
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Permission denied
- `404 Not Found` - Resource not found
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error

## Rate Limiting

- **API requests**: 1000/hour per user
- **Burst limit**: 100/minute
- **Email notifications**: 100/hour per user

Rate limit headers:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1640000000
```

## Support

- **Issues**: Report bugs and request features via GitHub Issues
- **Email**: support@enginel.example.com
- **Documentation**: This docs folder
- **API Status**: http://localhost:8000/api/health/

## Version History

- **v1.0** (Current) - Initial release with full feature set
  - REST API with 60+ endpoints
  - Token authentication with refresh tokens
  - Multi-tenant organizations
  - CAD file processing and BOM extraction
  - Background job monitoring
  - Email notifications
  - Comprehensive audit logging
  - Advanced search and filtering
  - Redis caching layer

## Contributing

When adding new features:
1. Update relevant documentation files
2. Add examples to API_QUICKSTART.md
3. Update API_REFERENCE.md with new endpoints
4. Update openapi.yaml specification
5. Add integration tests

## License

Proprietary - All rights reserved
