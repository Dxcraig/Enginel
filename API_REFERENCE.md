# Enginel API Reference

Complete reference documentation for the Enginel REST API.

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Base URL](#base-url)
- [Common Patterns](#common-patterns)
- [API Endpoints](#api-endpoints)
  - [Organizations](#organizations)
  - [Users](#users)
  - [Design Series](#design-series)
  - [Design Assets](#design-assets)
  - [Assembly Nodes (BOM)](#assembly-nodes-bom)
  - [Analysis Jobs](#analysis-jobs)
  - [Review Sessions](#review-sessions)
  - [Markups](#markups)
  - [Audit Logs](#audit-logs)
  - [Authentication](#authentication-endpoints)
  - [Health & Monitoring](#health--monitoring)
- [Data Models](#data-models)
- [Error Responses](#error-responses)
- [Rate Limiting](#rate-limiting)

## Overview

Enginel provides a RESTful API for managing CAD designs, bills of materials, review workflows, and compliance tracking. All endpoints return JSON responses and require authentication (except health checks).

### API Version

Current Version: **v1.0**  
Last Updated: December 16, 2025

### API Features

- ✅ Token-based authentication
- ✅ Multi-tenant organization isolation
- ✅ ITAR compliance controls
- ✅ Comprehensive audit logging
- ✅ Real-time background job tracking
- ✅ Advanced search and filtering
- ✅ Redis-backed caching
- ✅ Pagination support
- ✅ Bulk operations

## Authentication

All API endpoints (except health checks) require authentication. See [Authentication Documentation](./AUTHENTICATION.md) for detailed information.

### Authentication Methods

1. **Token Authentication** (Recommended)
```
Authorization: Token abc123def456...
```

2. **API Key Authentication** (For services)
```
Authorization: ApiKey xyz789abc123...
```

3. **Session Authentication** (Browser only)
```
Cookie: sessionid=...
```

### Getting Started

```bash
# 1. Login to get token
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"user@example.com","password":"password"}'

# Response:
{
  "access_token": "abc123...",
  "refresh_token": "xyz789...",
  "expires_in": 86400,
  "token_type": "Bearer"
}

# 2. Use token in requests
curl http://localhost:8000/api/designs/ \
  -H "Authorization: Token abc123..."
```

## Base URL

**Development:** `http://localhost:8000/api/`  
**Production:** `https://api.enginel.example.com/api/`

All endpoints are prefixed with `/api/`.

## Common Patterns

### Pagination

All list endpoints support pagination:

**Request:**
```
GET /api/designs/?page=2&page_size=25
```

**Response:**
```json
{
  "count": 150,
  "next": "http://localhost:8000/api/designs/?page=3",
  "previous": "http://localhost:8000/api/designs/?page=1",
  "results": [...]
}
```

**Parameters:**
- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 50, max: 100)

### Filtering

Most endpoints support field-based filtering:

```
GET /api/designs/?status=APPROVED&classification=UNCLASSIFIED
GET /api/analysis-jobs/?status=SUCCESS&job_type=PROCESSING
GET /api/audit-logs/?action=CREATE&resource_type=DesignAsset
```

See [Search & Filtering Documentation](./SEARCH_FILTERING.md) for complete filter reference.

### Searching

Use the `search` parameter for text search:

```
GET /api/designs/?search=turbine
GET /api/series/?search=bracket
```

### Ordering

Use `ordering` parameter to sort results:

```
GET /api/designs/?ordering=-created_at  # Descending
GET /api/designs/?ordering=part_number  # Ascending
GET /api/designs/?ordering=-created_at,part_number  # Multiple fields
```

### Field Selection

Request specific fields only:

```
GET /api/designs/?fields=id,filename,status
```

### Timestamps

All timestamps are in ISO 8601 format with UTC timezone:

```
2025-12-16T10:30:45.123456Z
```

---

## API Endpoints

## Organizations

Manage multi-tenant organizations and memberships.

### List Organizations

```
GET /api/organizations/
```

**Response:**
```json
{
  "count": 2,
  "results": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "name": "Acme Engineering",
      "slug": "acme-engineering",
      "description": "Advanced aerospace components",
      "is_active": true,
      "is_us_organization": true,
      "subscription_tier": "ENTERPRISE",
      "max_users": 100,
      "max_storage_gb": 1000,
      "member_count": 45,
      "storage_used_gb": 234.5,
      "contact_email": "admin@acme.com",
      "contact_phone": "+1-555-0100",
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": "2025-12-16T10:00:00Z"
    }
  ]
}
```

**Filters:**
- `is_active` - boolean
- `is_us_organization` - boolean
- `subscription_tier` - STARTER, PROFESSIONAL, ENTERPRISE
- `search` - Search name, slug, description

### Create Organization

```
POST /api/organizations/
```

**Request:**
```json
{
  "name": "New Company Inc",
  "slug": "new-company",
  "description": "Manufacturing and design",
  "is_us_organization": true,
  "subscription_tier": "PROFESSIONAL",
  "max_users": 50,
  "max_storage_gb": 500,
  "contact_email": "admin@newco.com",
  "contact_phone": "+1-555-0200"
}
```

**Response:** `201 Created` with organization object

### Get Organization

```
GET /api/organizations/{id}/
```

### Update Organization

```
PUT /api/organizations/{id}/
PATCH /api/organizations/{id}/
```

### Delete Organization

```
DELETE /api/organizations/{id}/
```

**Response:** `204 No Content`

### Get Organization Members

```
GET /api/organizations/{id}/members/
```

**Response:**
```json
[
  {
    "id": 1,
    "user": 5,
    "username": "john.doe",
    "email": "john@acme.com",
    "role": "ADMIN",
    "joined_at": "2025-01-15T10:00:00Z"
  }
]
```

**Roles:**
- `OWNER` - Full control
- `ADMIN` - Manage members and settings
- `MEMBER` - Create and edit designs
- `VIEWER` - Read-only access

### Add Organization Member

```
POST /api/organizations/{id}/add_member/
```

**Request:**
```json
{
  "user_id": 10,
  "role": "MEMBER"
}
```

**Permissions:** Requires OWNER or ADMIN role

---

## Users

Manage users and their profiles.

### List Users

```
GET /api/users/
```

**Response:**
```json
{
  "count": 1,
  "results": [
    {
      "id": 1,
      "username": "john.doe",
      "email": "john@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "is_us_person": true,
      "security_clearance_level": "SECRET",
      "organization": "Acme Engineering",
      "phone_number": "+1-555-0100",
      "date_joined": "2025-01-01T00:00:00Z",
      "organizations": [
        {
          "organization_id": "123e4567...",
          "organization_name": "Acme Engineering",
          "role": "ADMIN"
        }
      ]
    }
  ]
}
```

**Filters:**
- `is_us_person` - boolean
- `security_clearance_level` - UNCLASSIFIED, CONFIDENTIAL, SECRET, TOP_SECRET
- `search` - Search username, email, name

### Get User

```
GET /api/users/{id}/
```

### Get Current User

```
GET /api/users/me/
```

Returns the authenticated user's profile.

---

## Design Series

Manage part numbers and design families.

### List Design Series

```
GET /api/series/
```

**Response:**
```json
{
  "count": 1,
  "results": [
    {
      "id": "456e7890-e89b-12d3-a456-426614174000",
      "organization": "123e4567-e89b-12d3-a456-426614174000",
      "organization_name": "Acme Engineering",
      "part_number": "TB-001",
      "name": "Turbine Blade Assembly",
      "description": "High-temperature titanium blade",
      "category": "AEROSPACE",
      "created_by": 1,
      "created_by_username": "john.doe",
      "created_at": "2025-06-01T00:00:00Z",
      "updated_at": "2025-12-16T10:00:00Z"
    }
  ]
}
```

**Filters:**
- `organization` - UUID
- `part_number` - exact match
- `category` - text
- `created_by` - user ID
- `search` - Search part_number, name, description

### Create Design Series

```
POST /api/series/
```

**Request:**
```json
{
  "organization": "123e4567-e89b-12d3-a456-426614174000",
  "part_number": "TB-002",
  "name": "Turbine Blade Mark II",
  "description": "Improved blade design with better heat resistance",
  "category": "AEROSPACE"
}
```

**Response:** `201 Created`

**Permissions:** Requires MEMBER role in organization

### Get Design Series

```
GET /api/series/{id}/
```

### Update Design Series

```
PUT /api/series/{id}/
PATCH /api/series/{id}/
```

### Delete Design Series

```
DELETE /api/series/{id}/
```

### Get Series Designs

Get all design versions for this series:

```
GET /api/series/{id}/designs/
```

**Response:**
```json
[
  {
    "id": "789abc...",
    "version_number": 1,
    "filename": "turbine_blade_v1.step",
    "status": "APPROVED"
  },
  {
    "id": "def123...",
    "version_number": 2,
    "filename": "turbine_blade_v2.step",
    "status": "IN_REVIEW"
  }
]
```

---

## Design Assets

Manage CAD files and design metadata.

### List Design Assets

```
GET /api/designs/
```

**Response:**
```json
{
  "count": 1,
  "results": [
    {
      "id": "789abc-e89b-12d3-a456-426614174000",
      "series": "456e7890-e89b-12d3-a456-426614174000",
      "part_number": "TB-001",
      "series_name": "Turbine Blade Assembly",
      "version_number": 2,
      "filename": "turbine_blade_v2.step",
      "file_size_bytes": 15728640,
      "file_hash": "sha256:abc123...",
      "revision": "Rev B",
      "classification": "UNCLASSIFIED",
      "status": "APPROVED",
      "is_valid_geometry": true,
      "validation_errors": [],
      "bounding_box": {
        "min": {"x": 0, "y": 0, "z": 0},
        "max": {"x": 100, "y": 50, "z": 25}
      },
      "volume_cubic_mm": 125000,
      "surface_area_sq_mm": 15000,
      "center_of_mass": {"x": 50, "y": 25, "z": 12.5},
      "mass_kg": 0.563,
      "material": "Ti-6Al-4V",
      "uploaded_by": 1,
      "uploaded_by_username": "john.doe",
      "created_at": "2025-12-15T10:00:00Z",
      "updated_at": "2025-12-16T10:00:00Z"
    }
  ]
}
```

**Filters:**
- `series` - UUID
- `part_number` - text
- `version_number` - integer
- `classification` - UNCLASSIFIED, CONFIDENTIAL, SECRET, TOP_SECRET, ITAR
- `status` - UPLOADING, PROCESSING, APPROVED, IN_REVIEW, REJECTED, ARCHIVED
- `is_valid_geometry` - boolean
- `material` - text
- `uploaded_by` - user ID
- `created_at__gte` / `created_at__lte` - date range
- `search` - Search filename, part_number, material

### Get Upload URL

Get a pre-signed URL for uploading CAD files:

```
POST /api/designs/upload-url/
```

**Request:**
```json
{
  "filename": "turbine_blade_v3.step",
  "file_size": 16777216,
  "content_type": "application/step"
}
```

**Response:**
```json
{
  "upload_url": "http://localhost:8000/media/uploads/tmp_abc123.step",
  "upload_id": "abc123-temp-id",
  "expires_at": "2025-12-16T11:00:00Z"
}
```

### Create Design Asset

```
POST /api/designs/
```

**Request:**
```json
{
  "series": "456e7890-e89b-12d3-a456-426614174000",
  "filename": "turbine_blade_v3.step",
  "file_path": "/uploads/tmp_abc123.step",
  "upload_id": "abc123-temp-id",
  "revision": "Rev C",
  "classification": "UNCLASSIFIED",
  "material": "Ti-6Al-4V"
}
```

**Response:** `201 Created`

**Note:** This triggers asynchronous processing (geometry extraction, validation, BOM extraction).

### Finalize Upload

Complete the upload and start processing:

```
POST /api/designs/{id}/finalize_upload/
```

**Request:**
```json
{
  "file_hash": "sha256:calculated-hash"
}
```

**Response:**
```json
{
  "status": "PROCESSING",
  "analysis_job_id": "job-123-456",
  "message": "File upload finalized, processing started"
}
```

### Get Design Asset

```
GET /api/designs/{id}/
```

### Update Design Asset

```
PATCH /api/designs/{id}/
```

**Request:**
```json
{
  "status": "APPROVED",
  "material": "Ti-6Al-4V Grade 5"
}
```

### Delete Design Asset

```
DELETE /api/designs/{id}/
```

### Download Design File

```
GET /api/designs/{id}/download/
```

**Response:** Binary file download with appropriate Content-Type header

### Get Design Metadata

Get extracted geometric and material properties:

```
GET /api/designs/{id}/metadata/
```

**Response:**
```json
{
  "geometry": {
    "bounding_box": {"min": {...}, "max": {...}},
    "volume_cubic_mm": 125000,
    "surface_area_sq_mm": 15000,
    "center_of_mass": {"x": 50, "y": 25, "z": 12.5}
  },
  "material": {
    "name": "Ti-6Al-4V",
    "density_kg_m3": 4500,
    "mass_kg": 0.563
  },
  "validation": {
    "is_valid": true,
    "errors": [],
    "warnings": ["Self-intersecting surfaces detected"]
  }
}
```

### Start Review

Initiate a design review workflow:

```
POST /api/designs/{id}/start_review/
```

**Request:**
```json
{
  "reviewer_ids": [5, 7, 12],
  "due_date": "2025-12-20T00:00:00Z",
  "notes": "Please review before production"
}
```

**Response:**
```json
{
  "review_session_id": "review-abc-123",
  "status": "IN_REVIEW"
}
```

### Approve Design

```
POST /api/designs/{id}/approve/
```

**Request:**
```json
{
  "notes": "Design meets all requirements"
}
```

**Permissions:** Requires assigned reviewer

### Unit Conversion

Convert measurement units in design metadata:

```
GET /api/designs/convert-units/?value=100&from_unit=mm&to_unit=in
```

**Response:**
```json
{
  "original_value": 100,
  "from_unit": "mm",
  "to_unit": "in",
  "converted_value": 3.937,
  "conversion_factor": 0.03937
}
```

**Supported Units:**
- Length: mm, cm, m, in, ft
- Volume: mm3, cm3, m3, in3, ft3
- Mass: g, kg, lb, oz
- Area: mm2, cm2, m2, in2, ft2

---

## Assembly Nodes (BOM)

Manage hierarchical Bill of Materials.

### List Assembly Nodes

```
GET /api/bom-nodes/
```

**Response:**
```json
{
  "count": 1,
  "results": [
    {
      "id": 1,
      "design_asset": "789abc...",
      "parent": null,
      "path": "0001",
      "depth": 1,
      "part_name": "Turbine Assembly",
      "part_number": "TB-001-ASM",
      "quantity": 1,
      "unit_of_measure": "EA",
      "reference_designator": "A1",
      "notes": "Main assembly",
      "created_at": "2025-12-16T10:00:00Z"
    }
  ]
}
```

**Filters:**
- `design_asset` - UUID
- `parent` - node ID (null for root nodes)
- `part_number` - text
- `search` - Search part_name, part_number

### Create Assembly Node

```
POST /api/bom-nodes/
```

**Request:**
```json
{
  "design_asset": "789abc...",
  "parent": 1,
  "part_name": "Bolt",
  "part_number": "HW-M8-20",
  "quantity": 12,
  "unit_of_measure": "EA",
  "reference_designator": "B1-B12"
}
```

### Get Assembly Node

```
GET /api/bom-nodes/{id}/
```

### Update Assembly Node

```
PATCH /api/bom-nodes/{id}/
```

### Delete Assembly Node

```
DELETE /api/bom-nodes/{id}/
```

**Note:** Deleting a parent node deletes all children (cascading delete).

---

## Analysis Jobs

Track background processing tasks.

### List Analysis Jobs

```
GET /api/analysis-jobs/
```

**Response:**
```json
{
  "count": 1,
  "results": [
    {
      "id": "job-123-456",
      "design_asset": "789abc...",
      "job_type": "PROCESSING",
      "status": "SUCCESS",
      "celery_task_id": "celery-abc-123",
      "started_at": "2025-12-16T10:00:00Z",
      "completed_at": "2025-12-16T10:05:30Z",
      "duration_seconds": 330,
      "result": {
        "geometry_extracted": true,
        "bom_items": 45,
        "validation_passed": true
      },
      "error_message": null,
      "retry_count": 0
    }
  ]
}
```

**Filters:**
- `design_asset` - UUID
- `job_type` - PROCESSING, VALIDATION, BOM_EXTRACTION, EXPORT
- `status` - PENDING, PROCESSING, SUCCESS, FAILURE, CANCELLED
- `started_at__gte` / `started_at__lte` - date range

### Get Analysis Job

```
GET /api/analysis-jobs/{id}/
```

### Get Job Status

Get Celery task status:

```
GET /api/analysis-jobs/{id}/status/
```

**Response:**
```json
{
  "status": "PROCESSING",
  "state": "STARTED",
  "result": null,
  "error": null,
  "celery_info": {
    "task_id": "celery-abc-123",
    "name": "designs.tasks.process_design_asset",
    "args": ["789abc..."],
    "kwargs": {},
    "worker": "celery@worker1",
    "retries": 0
  }
}
```

### Get Job Progress

Get real-time progress for long-running jobs:

```
GET /api/analysis-jobs/{id}/progress/
```

**Response:**
```json
{
  "current": 3,
  "total": 5,
  "percent": 60,
  "status_message": "Running validation checks..."
}
```

### Cancel Job

```
POST /api/analysis-jobs/{id}/cancel/
```

**Request:**
```json
{
  "force": false
}
```

**Response:**
```json
{
  "message": "Job cancelled successfully",
  "status": "CANCELLED"
}
```

### Get Active Jobs

List currently running jobs:

```
GET /api/analysis-jobs/active/
```

**Response:**
```json
{
  "count": 2,
  "tasks": [
    {
      "task_id": "celery-abc-123",
      "name": "process_design_asset",
      "args": ["789abc..."],
      "worker": "celery@worker1",
      "time_start": 1702728000
    }
  ]
}
```

### Get Job Metrics

Get aggregated job statistics:

```
GET /api/analysis-jobs/metrics/?job_type=PROCESSING
```

**Response:**
```json
{
  "job_type": "PROCESSING",
  "total_count": 150,
  "success_count": 145,
  "failure_count": 5,
  "success_rate": 96.67,
  "avg_duration_seconds": 245.5,
  "min_duration_seconds": 120,
  "max_duration_seconds": 480
}
```

### Get Job Failures

Analyze recent failures:

```
GET /api/analysis-jobs/failures/?days=7
```

**Response:**
```json
{
  "total_failures": 12,
  "top_errors": [
    {
      "error": "Invalid STEP file format",
      "count": 5
    },
    {
      "error": "Geometry extraction timeout",
      "count": 4
    }
  ],
  "failures": [...]
}
```

---

## Review Sessions

Manage collaborative design reviews.

### List Review Sessions

```
GET /api/reviews/
```

**Response:**
```json
{
  "count": 1,
  "results": [
    {
      "id": "review-abc-123",
      "design_asset": "789abc...",
      "reviewers": [5, 7, 12],
      "status": "IN_PROGRESS",
      "due_date": "2025-12-20T00:00:00Z",
      "notes": "Pre-production review",
      "created_by": 1,
      "created_at": "2025-12-16T10:00:00Z",
      "completed_at": null
    }
  ]
}
```

**Filters:**
- `design_asset` - UUID
- `status` - PENDING, IN_PROGRESS, COMPLETED, CANCELLED
- `reviewers` - user ID
- `created_by` - user ID
- `due_date__lte` - date

### Create Review Session

```
POST /api/reviews/
```

**Request:**
```json
{
  "design_asset": "789abc...",
  "reviewers": [5, 7, 12],
  "due_date": "2025-12-20T00:00:00Z",
  "notes": "Focus on structural integrity"
}
```

### Get Review Session

```
GET /api/reviews/{id}/
```

### Update Review Session

```
PATCH /api/reviews/{id}/
```

### Approve Review

```
POST /api/reviews/{id}/approve/
```

**Request:**
```json
{
  "comments": "All requirements met",
  "approved": true
}
```

**Permissions:** Must be assigned reviewer

### Reject Review

```
POST /api/reviews/{id}/reject/
```

**Request:**
```json
{
  "comments": "Dimensions do not match specification",
  "reason": "INCORRECT_DIMENSIONS"
}
```

---

## Markups

Manage 3D annotations and comments on designs.

### List Markups

```
GET /api/markups/
```

**Response:**
```json
{
  "count": 1,
  "results": [
    {
      "id": 1,
      "design_asset": "789abc...",
      "review_session": "review-abc-123",
      "author": 5,
      "author_username": "jane.smith",
      "position": {"x": 25.5, "y": 12.3, "z": 8.7},
      "camera_position": {"x": 100, "y": 100, "z": 100},
      "camera_target": {"x": 25.5, "y": 12.3, "z": 8.7},
      "annotation_text": "Check tolerance here",
      "severity": "MAJOR",
      "status": "OPEN",
      "created_at": "2025-12-16T10:30:00Z",
      "resolved_at": null
    }
  ]
}
```

**Filters:**
- `design_asset` - UUID
- `review_session` - review ID
- `author` - user ID
- `severity` - INFO, MINOR, MAJOR, CRITICAL
- `status` - OPEN, RESOLVED, DISMISSED

### Create Markup

```
POST /api/markups/
```

**Request:**
```json
{
  "design_asset": "789abc...",
  "review_session": "review-abc-123",
  "position": {"x": 25.5, "y": 12.3, "z": 8.7},
  "camera_position": {"x": 100, "y": 100, "z": 100},
  "camera_target": {"x": 25.5, "y": 12.3, "z": 8.7},
  "annotation_text": "Wall thickness appears insufficient",
  "severity": "MAJOR"
}
```

### Get Markup

```
GET /api/markups/{id}/
```

### Update Markup

```
PATCH /api/markups/{id}/
```

### Delete Markup

```
DELETE /api/markups/{id}/
```

### Resolve Markup

```
POST /api/markups/{id}/resolve/
```

**Request:**
```json
{
  "resolution_notes": "Increased wall thickness to 3mm"
}
```

### Dismiss Markup

```
POST /api/markups/{id}/dismiss/
```

**Request:**
```json
{
  "reason": "Not applicable for this revision"
}
```

---

## Audit Logs

Read-only access to compliance audit trail.

### List Audit Logs

```
GET /api/audit-logs/
```

**Response:**
```json
{
  "count": 1,
  "results": [
    {
      "id": 1,
      "actor_id": 1,
      "actor_username": "john.doe",
      "action": "CREATE",
      "action_display": "Create",
      "resource_type": "DesignAsset",
      "resource_id": "789abc...",
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0...",
      "changes": {
        "filename": "turbine_blade_v3.step",
        "classification": "UNCLASSIFIED"
      },
      "timestamp": "2025-12-16T10:00:00Z"
    }
  ]
}
```

**Filters:**
- `actor_id` - user ID
- `action` - CREATE, UPDATE, DELETE, APPROVE, REJECT
- `resource_type` - DesignAsset, ReviewSession, Organization, etc.
- `resource_id` - UUID or ID
- `timestamp__gte` / `timestamp__lte` - date range

### Get Audit Log

```
GET /api/audit-logs/{id}/
```

### Search Audit Logs

```
GET /api/audit-logs/search/?q=turbine&resource_type=DesignAsset
```

### Export Audit Logs

```
GET /api/audit-logs/export/?format=csv&start_date=2025-12-01
```

**Formats:** csv, json, pdf

---

## Authentication Endpoints

See [Authentication Documentation](./AUTHENTICATION.md) for detailed information.

### Login

```
POST /api/auth/login/
```

### Logout

```
POST /api/auth/logout/
```

### Refresh Token

```
POST /api/auth/refresh/
```

### Verify Token

```
GET /api/auth/verify/
```

### List Sessions

```
GET /api/auth/sessions/
```

### Manage API Keys

```
GET /api/auth/api-keys/
POST /api/auth/api-keys/
DELETE /api/auth/api-keys/{id}/
```

---

## Health & Monitoring

Public health check endpoints (no authentication required).

### Health Check

```
GET /api/health/
```

**Response:**
```json
{
  "status": "ok",
  "service": "enginel"
}
```

### Detailed Health Check

```
GET /api/health/detailed/
```

**Response:**
```json
{
  "status": "healthy",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "celery": "ok"
  },
  "timestamp": "2025-12-16T10:00:00Z"
}
```

### Monitoring Dashboard

```
GET /api/monitoring/dashboard/
```

**Permissions:** Admin only

### Error Logs

```
GET /api/monitoring/errors/?hours=24
```

**Permissions:** Admin only

### Performance Stats

```
GET /api/monitoring/performance/
```

**Permissions:** Admin only

---

## Data Models

### Organization

```typescript
{
  id: UUID,
  name: string,
  slug: string,
  description: string,
  is_active: boolean,
  is_us_organization: boolean,
  subscription_tier: "STARTER" | "PROFESSIONAL" | "ENTERPRISE",
  max_users: number,
  max_storage_gb: number,
  contact_email: string,
  contact_phone: string,
  created_at: timestamp,
  updated_at: timestamp
}
```

### User

```typescript
{
  id: number,
  username: string,
  email: string,
  first_name: string,
  last_name: string,
  is_us_person: boolean,
  security_clearance_level: "UNCLASSIFIED" | "CONFIDENTIAL" | "SECRET" | "TOP_SECRET",
  organization: string,
  phone_number: string,
  date_joined: timestamp
}
```

### Design Series

```typescript
{
  id: UUID,
  organization: UUID,
  part_number: string,
  name: string,
  description: string,
  category: string,
  created_by: number,
  created_at: timestamp,
  updated_at: timestamp
}
```

### Design Asset

```typescript
{
  id: UUID,
  series: UUID,
  version_number: number,
  filename: string,
  file_size_bytes: number,
  file_hash: string,
  revision: string,
  classification: "UNCLASSIFIED" | "CONFIDENTIAL" | "SECRET" | "TOP_SECRET" | "ITAR",
  status: "UPLOADING" | "PROCESSING" | "APPROVED" | "IN_REVIEW" | "REJECTED" | "ARCHIVED",
  is_valid_geometry: boolean,
  validation_errors: string[],
  bounding_box: {min: Point3D, max: Point3D},
  volume_cubic_mm: number,
  surface_area_sq_mm: number,
  center_of_mass: Point3D,
  mass_kg: number,
  material: string,
  uploaded_by: number,
  created_at: timestamp,
  updated_at: timestamp
}
```

### Point3D

```typescript
{
  x: number,
  y: number,
  z: number
}
```

---

## Error Responses

### Standard Error Format

```json
{
  "error": "Error message",
  "detail": "Detailed error description",
  "code": "ERROR_CODE",
  "field_errors": {
    "field_name": ["Error message"]
  }
}
```

### HTTP Status Codes

- `200 OK` - Success
- `201 Created` - Resource created
- `204 No Content` - Success with no response body
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Permission denied
- `404 Not Found` - Resource not found
- `409 Conflict` - Resource conflict (e.g., duplicate)
- `422 Unprocessable Entity` - Validation error
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error
- `503 Service Unavailable` - Service temporarily unavailable

### Common Error Codes

- `AUTHENTICATION_FAILED` - Invalid credentials
- `TOKEN_EXPIRED` - Access token expired
- `PERMISSION_DENIED` - Insufficient permissions
- `RESOURCE_NOT_FOUND` - Requested resource doesn't exist
- `VALIDATION_ERROR` - Data validation failed
- `ITAR_VIOLATION` - ITAR compliance check failed
- `ORGANIZATION_LIMIT_EXCEEDED` - Subscription limit reached
- `FILE_TOO_LARGE` - File exceeds size limit
- `INVALID_FILE_FORMAT` - Unsupported file format
- `GEOMETRY_EXTRACTION_FAILED` - CAD processing error

### Example Error Responses

**401 Unauthorized:**
```json
{
  "detail": "Authentication credentials were not provided."
}
```

**403 Forbidden:**
```json
{
  "detail": "Access denied: ITAR-controlled designs require US person status."
}
```

**400 Bad Request:**
```json
{
  "error": "Validation error",
  "field_errors": {
    "part_number": ["This field is required."],
    "classification": ["Invalid choice. Must be one of: UNCLASSIFIED, CONFIDENTIAL, SECRET, TOP_SECRET, ITAR"]
  }
}
```

---

## Rate Limiting

Rate limits apply per user/API key:

- **Standard:** 1000 requests/hour
- **Burst:** 100 requests/minute
- **Upload:** 50 uploads/hour

**Headers:**
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 945
X-RateLimit-Reset: 1702731600
```

**429 Response:**
```json
{
  "error": "Rate limit exceeded",
  "detail": "Request limit is 1000 per hour. Try again in 45 minutes.",
  "retry_after": 2700
}
```

---

## Related Documentation

- [Authentication Guide](./AUTHENTICATION.md)
- [Search & Filtering](./SEARCH_FILTERING.md)
- [Background Jobs](./BACKGROUND_JOBS.md)
- [Multi-Tenant Organizations](./MULTI_TENANT.md)
- [Error Handling](./ERROR_HANDLING.md)
- [Caching Strategy](./CACHING.md)
- [Audit Logging](./AUDIT_LOGGING.md)
- [BOM Extraction](./BOM_EXTRACTION.md)
- [Unit Conversion](./UNIT_CONVERSION.md)

---

**API Version:** 1.0  
**Last Updated:** December 16, 2025  
**Support:** For API support, check error logs at `/api/monitoring/errors/`
