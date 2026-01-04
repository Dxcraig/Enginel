# Search & Filtering

This document describes the comprehensive search and filtering capabilities in Enginel, enabling powerful queries across all resources.

## Overview

Enginel provides three complementary mechanisms for finding data:

1. **Full-Text Search**: Quick keyword search across multiple fields using `?search=keyword`
2. **Advanced Filtering**: Precise filters for specific fields using `django-filter` with 25+ filter types
3. **Ordering**: Sort results by multiple fields with `?ordering=field1,-field2` (ascending/descending)

All endpoints support pagination with `?page=N` and `?page_size=50` (default 50 items per page).

## Architecture

### Technology Stack

- **django-filter 25.2**: Advanced filtering with FilterSet classes
- **DRF SearchFilter**: Full-text search across specified fields  
- **DRF OrderingFilter**: Multi-field sorting
- **PostgreSQL**: Database-level filtering and indexing

### Filter Backends

All ViewSets use three filter backends in order:

```python
filter_backends = [
    DjangoFilterBackend,      # Advanced field-specific filters
    SearchFilter,              # Full-text keyword search
    OrderingFilter,            # Result sorting
]
```

## General Syntax

### Combining Filters

Multiple filters are combined with AND logic:

```
GET /api/designs/?file_format=step&min_file_size_mb=10&uploaded_after=2025-01-01
```

This returns STEP files >= 10MB uploaded after January 1, 2025.

### Search + Filters

You can combine search with filters:

```
GET /api/designs/?search=bracket&file_format=step&has_geometry=true
```

### Ordering

Order by one or more fields (prefix with `-` for descending):

```
GET /api/designs/?ordering=-created_at,file_size
```

This sorts by newest first, then by file size ascending.

## API Endpoints

### Users

**Endpoint**: `/api/users/`

**Search Fields**: username, email, first_name, last_name, organization

**Filters**:

| Filter | Type | Description | Example |
|--------|------|-------------|---------|
| `username` | String | Username (case-insensitive) | `?username=john` |
| `email` | String | Email address | `?email=john@example.com` |
| `first_name` | String | First name | `?first_name=John` |
| `last_name` | String | Last name | `?last_name=Doe` |
| `organization` | String | Organization name | `?organization=acme` |
| `security_clearance_level` | Choice | Exact clearance (UNCLASSIFIED, CONFIDENTIAL, SECRET, TOP_SECRET) | `?security_clearance_level=SECRET` |
| `min_clearance` | Choice | Minimum clearance level (hierarchical) | `?min_clearance=CONFIDENTIAL` |
| `is_us_person` | Boolean | ITAR compliance | `?is_us_person=true` |
| `is_active` | Boolean | Active account | `?is_active=true` |
| `is_staff` | Boolean | Staff status | `?is_staff=true` |
| `is_superuser` | Boolean | Admin status | `?is_superuser=false` |
| `joined_after` | DateTime | Account created after | `?joined_after=2025-01-01` |
| `joined_before` | DateTime | Account created before | `?joined_before=2025-12-31` |

**Ordering Fields**: username, date_joined, last_login

**Examples**:

```bash
# Find ITAR-compliant users with SECRET clearance
GET /api/users/?is_us_person=true&min_clearance=SECRET

# Search for user
GET /api/users/?search=john.doe

# New users this month
GET /api/users/?joined_after=2025-12-01
```

---

### Design Series (Part Numbers)

**Endpoint**: `/api/series/`

**Search Fields**: part_number, name, description

**Filters**:

| Filter | Type | Description | Example |
|--------|------|-------------|---------|
| `part_number` | String | Part number (case-insensitive) | `?part_number=PN-001` |
| `name` | String | Series name | `?name=bracket` |
| `description` | String | Description text | `?description=aluminum` |
| `status` | Choice | Status (DRAFT, IN_REVIEW, RELEASED, OBSOLETE) | `?status=RELEASED` |
| `classification_level` | String | Classification | `?classification_level=SECRET` |
| `requires_itar_compliance` | Boolean | ITAR-controlled | `?requires_itar_compliance=true` |
| `has_versions` | Boolean | Has uploaded files | `?has_versions=true` |
| `min_versions` | Number | Minimum version count | `?min_versions=3` |
| `max_versions` | Number | Maximum version count | `?max_versions=10` |
| `created_by` | Number | Creator user ID | `?created_by=5` |
| `created_by_username` | String | Creator username | `?created_by_username=john` |
| `created_after` | DateTime | Created after | `?created_after=2025-01-01` |
| `created_before` | DateTime | Created before | `?created_before=2025-12-31` |
| `updated_after` | DateTime | Updated after | `?updated_after=2025-01-01` |
| `updated_before` | DateTime | Updated before | `?updated_before=2025-12-31` |

**Ordering Fields**: part_number, created_at, updated_at, status

**Examples**:

```bash
# Find all released ITAR parts
GET /api/series/?status=RELEASED&requires_itar_compliance=true

# Parts with multiple versions
GET /api/series/?min_versions=5

# Search for bracket parts
GET /api/series/?search=bracket

# Recently updated parts
GET /api/series/?updated_after=2025-12-01&ordering=-updated_at

# Parts without any versions yet
GET /api/series/?has_versions=false
```

---

### Design Assets (CAD Files)

**Endpoint**: `/api/designs/`

**Search Fields**: filename, series__part_number, series__name, revision

**Filters**:

| Filter | Type | Description | Example |
|--------|------|-------------|---------|
| `filename` | String | Filename (case-insensitive) | `?filename=bracket.step` |
| `revision` | String | Revision/version | `?revision=A` |
| `part_number` | String | Parent series part number | `?part_number=PN-001` |
| `series_name` | String | Parent series name | `?series_name=bracket` |
| `file_format` | String | File format | `?file_format=step` |
| `file_formats` | Multi-Choice | Multiple formats | `?file_formats=step,iges` |
| `upload_status` | Choice | Status (PENDING, PROCESSING, COMPLETED, FAILED) | `?upload_status=COMPLETED` |
| `min_file_size` | Number | Minimum size (bytes) | `?min_file_size=1000000` |
| `max_file_size` | Number | Maximum size (bytes) | `?max_file_size=100000000` |
| `min_file_size_mb` | Number | Minimum size (MB) | `?min_file_size_mb=10` |
| `max_file_size_mb` | Number | Maximum size (MB) | `?max_file_size_mb=100` |
| `has_geometry` | Boolean | Has geometry metadata | `?has_geometry=true` |
| `has_bom` | Boolean | Has BOM data | `?has_bom=true` |
| `is_assembly` | Boolean | Is assembly file | `?is_assembly=true` |
| `min_volume` | Number | Minimum volume (mm³) | `?min_volume=1000` |
| `max_volume` | Number | Maximum volume (mm³) | `?max_volume=1000000` |
| `min_surface_area` | Number | Minimum surface area (mm²) | `?min_surface_area=5000` |
| `max_surface_area` | Number | Maximum surface area (mm²) | `?max_surface_area=50000` |
| `min_mass` | Number | Minimum mass (kg) | `?min_mass=0.5` |
| `max_mass` | Number | Maximum mass (kg) | `?max_mass=10` |
| `uploaded_by` | Number | Uploader user ID | `?uploaded_by=5` |
| `uploaded_by_username` | String | Uploader username | `?uploaded_by_username=john` |
| `series_id` | UUID | Series ID | `?series_id=<uuid>` |
| `uploaded_after` | DateTime | Uploaded after | `?uploaded_after=2025-01-01` |
| `uploaded_before` | DateTime | Uploaded before | `?uploaded_before=2025-12-31` |
| `modified_after` | DateTime | Modified after | `?modified_after=2025-01-01` |
| `modified_before` | DateTime | Modified before | `?modified_before=2025-12-31` |

**Ordering Fields**: created_at, version_number, file_size, volume_mm3, mass_kg

**Examples**:

```bash
# Find all STEP files over 50MB
GET /api/designs/?file_format=step&min_file_size_mb=50

# Assemblies with BOM data
GET /api/designs/?is_assembly=true&has_bom=true

# Large volume parts (> 1 liter)
GET /api/designs/?min_volume=1000000

# Heavy parts (> 5kg)
GET /api/designs/?min_mass=5

# Recently uploaded STEP or IGES files
GET /api/designs/?file_formats=step,iges&uploaded_after=2025-12-01&ordering=-created_at

# Failed uploads
GET /api/designs/?upload_status=FAILED

# Files with geometry but no BOM
GET /api/designs/?has_geometry=true&has_bom=false

# Search for specific part
GET /api/designs/?search=bracket&file_format=step
```

---

### Assembly Nodes (BOM)

**Endpoint**: `/api/bom/`

**Search Fields**: part_name, part_number, material, description

**Filters**:

| Filter | Type | Description | Example |
|--------|------|-------------|---------|
| `part_name` | String | Part name (case-insensitive) | `?part_name=bracket` |
| `part_number` | String | Part number | `?part_number=PN-001` |
| `material` | String | Material | `?material=aluminum` |
| `description` | String | Description | `?description=mounting` |
| `node_type` | Choice | Node type (COMPONENT, ASSEMBLY, REFERENCE, VIRTUAL) | `?node_type=COMPONENT` |
| `has_children` | Boolean | Has child nodes | `?has_children=true` |
| `is_root` | Boolean | Root-level node | `?is_root=true` |
| `depth_level` | Number | Exact depth | `?depth_level=2` |
| `min_depth` | Number | Minimum depth | `?min_depth=2` |
| `max_depth` | Number | Maximum depth | `?max_depth=5` |
| `quantity` | Number | Exact quantity | `?quantity=4` |
| `min_quantity` | Number | Minimum quantity | `?min_quantity=10` |
| `max_quantity` | Number | Maximum quantity | `?max_quantity=100` |
| `design_asset` | UUID | Parent design | `?design_asset=<uuid>` |

**Ordering Fields**: depth, part_number, quantity

**Examples**:

```bash
# Find all aluminum components
GET /api/bom/?material=aluminum&node_type=COMPONENT

# Root-level assemblies
GET /api/bom/?is_root=true&node_type=ASSEMBLY

# High-quantity parts (>= 50)
GET /api/bom/?min_quantity=50

# Deep hierarchy nodes (level 3+)
GET /api/bom/?min_depth=3

# Search for fasteners
GET /api/bom/?search=bolt

# BOM for specific design
GET /api/bom/?design_asset=<uuid>&ordering=depth,part_number
```

---

### Analysis Jobs (Celery Tasks)

**Endpoint**: `/api/jobs/`

**Search Fields**: task_name, celery_task_id

**Filters**:

| Filter | Type | Description | Example |
|--------|------|-------------|---------|
| `task_name` | String | Task type | `?task_name=process_design_asset` |
| `celery_task_id` | String | Celery task ID | `?celery_task_id=<id>` |
| `status` | Choice | Status (PENDING, RUNNING, COMPLETED, FAILED) | `?status=COMPLETED` |
| `design_asset` | UUID | Related design | `?design_asset=<uuid>` |
| `initiated_by` | Number | User ID | `?initiated_by=5` |
| `started_after` | DateTime | Started after | `?started_after=2025-01-01` |
| `started_before` | DateTime | Started before | `?started_before=2025-12-31` |
| `completed_after` | DateTime | Completed after | `?completed_after=2025-01-01` |
| `completed_before` | DateTime | Completed before | `?completed_before=2025-12-31` |
| `min_duration` | Number | Minimum duration (seconds) | `?min_duration=30` |
| `max_duration` | Number | Maximum duration (seconds) | `?max_duration=300` |

**Ordering Fields**: created_at, completed_at, status

**Examples**:

```bash
# Failed tasks
GET /api/jobs/?status=FAILED

# Long-running tasks (> 5 minutes)
GET /api/jobs/?min_duration=300

# Recent tasks
GET /api/jobs/?started_after=2025-12-15&ordering=-created_at

# Tasks for specific design
GET /api/jobs/?design_asset=<uuid>
```

---

### Review Sessions

**Endpoint**: `/api/reviews/`

**Search Fields**: title, description

**Filters**:

| Filter | Type | Description | Example |
|--------|------|-------------|---------|
| `title` | String | Session title | `?title=design review` |
| `description` | String | Description text | `?description=final` |
| `status` | Choice | Status (OPEN, IN_PROGRESS, COMPLETED, CANCELLED) | `?status=OPEN` |
| `design_asset` | UUID | Reviewed design | `?design_asset=<uuid>` |
| `created_by` | Number | Creator user ID | `?created_by=5` |
| `has_reviewer` | Number | Specific reviewer | `?has_reviewer=7` |
| `created_after` | DateTime | Created after | `?created_after=2025-01-01` |
| `created_before` | DateTime | Created before | `?created_before=2025-12-31` |
| `completed_after` | DateTime | Completed after | `?completed_after=2025-01-01` |
| `completed_before` | DateTime | Completed before | `?completed_before=2025-12-31` |

**Ordering Fields**: created_at, completed_at, status

**Examples**:

```bash
# Open reviews
GET /api/reviews/?status=OPEN

# Reviews for specific design
GET /api/reviews/?design_asset=<uuid>

# Reviews with specific reviewer
GET /api/reviews/?has_reviewer=7

# Recently completed reviews
GET /api/reviews/?status=COMPLETED&completed_after=2025-12-01
```

---

### Markups (3D Annotations)

**Endpoint**: `/api/markups/`

**Search Fields**: title, comment

**Filters**:

| Filter | Type | Description | Example |
|--------|------|-------------|---------|
| `title` | String | Markup title | `?title=issue` |
| `comment` | String | Comment text | `?comment=dimension` |
| `is_resolved` | Boolean | Resolved status | `?is_resolved=false` |
| `priority` | Choice | Priority (LOW, MEDIUM, HIGH, CRITICAL) | `?priority=HIGH` |
| `review_session` | UUID | Parent review | `?review_session=<uuid>` |
| `author` | Number | Author user ID | `?author=5` |
| `author_username` | String | Author username | `?author_username=john` |
| `created_after` | DateTime | Created after | `?created_after=2025-01-01` |
| `created_before` | DateTime | Created before | `?created_before=2025-12-31` |
| `resolved_after` | DateTime | Resolved after | `?resolved_after=2025-01-01` |
| `resolved_before` | DateTime | Resolved before | `?resolved_before=2025-12-31` |

**Ordering Fields**: created_at, resolved_at, priority, is_resolved

**Examples**:

```bash
# Unresolved high-priority issues
GET /api/markups/?is_resolved=false&priority=HIGH

# Markups by specific reviewer
GET /api/markups/?author_username=john

# Recently resolved markups
GET /api/markups/?is_resolved=true&resolved_after=2025-12-01

# Critical unresolved issues
GET /api/markups/?is_resolved=false&priority=CRITICAL&ordering=-created_at
```

---

### Audit Logs

**Endpoint**: `/api/audit/`

**Search Fields**: action, resource_type, actor_username, ip_address

**Filters**:

| Filter | Type | Description | Example |
|--------|------|-------------|---------|
| `action` | String | Action type | `?action=CREATE` |
| `actions` | Multi-Choice | Multiple actions | `?actions=CREATE,UPDATE` |
| `resource_type` | String | Resource type | `?resource_type=DesignAsset` |
| `resource_id` | String | Resource UUID | `?resource_id=<uuid>` |
| `actor_id` | Number | Actor user ID | `?actor_id=5` |
| `actor_username` | String | Actor username | `?actor_username=john` |
| `ip_address` | String | Exact IP address | `?ip_address=192.168.1.100` |
| `ip_range` | String | IP range (CIDR) | `?ip_range=192.168.1.0/24` |
| `organization` | UUID | Organization ID | `?organization=<uuid>` |
| `success` | Boolean | Successful action | `?success=true` |
| `timestamp_after` | DateTime | After timestamp | `?timestamp_after=2025-01-01` |
| `timestamp_before` | DateTime | Before timestamp | `?timestamp_before=2025-12-31` |
| `last_hour` | Boolean | Last hour | `?last_hour=true` |
| `last_day` | Boolean | Last 24 hours | `?last_day=true` |
| `last_week` | Boolean | Last 7 days | `?last_week=true` |

**Ordering Fields**: timestamp, action, resource_type

**Examples**:

```bash
# Recent activity (last hour)
GET /api/audit/?last_hour=true

# Failed actions
GET /api/audit/?success=false

# All CREATE operations
GET /api/audit/?action=CREATE&ordering=-timestamp

# User activity
GET /api/audit/?actor_username=john&last_day=true

# Design downloads
GET /api/audit/?action=DOWNLOAD&resource_type=DesignAsset

# Activity from specific IP range
GET /api/audit/?ip_range=192.168.1.0/24

# ITAR-sensitive operations
GET /api/audit/?actions=VIEW,DOWNLOAD&resource_type=DesignAsset&last_week=true
```

## Advanced Patterns

### Complex Queries

Combine multiple filters for precise queries:

```bash
# Large STEP assemblies with BOM, uploaded this month
GET /api/designs/?file_format=step&is_assembly=true&has_bom=true&min_file_size_mb=50&uploaded_after=2025-12-01&ordering=-file_size

# ITAR parts created by specific user
GET /api/series/?requires_itar_compliance=true&created_by_username=john&status=RELEASED

# Recent failures for specific task type
GET /api/jobs/?task_name=process_design_asset&status=FAILED&started_after=2025-12-01
```

### Date Range Queries

Use before/after filters for ranges:

```bash
# Designs uploaded in December 2025
GET /api/designs/?uploaded_after=2025-12-01&uploaded_before=2025-12-31

# Reviews completed last week
GET /api/reviews/?status=COMPLETED&completed_after=2025-12-09&completed_before=2025-12-16
```

### Numeric Range Queries

Filter by numeric ranges:

```bash
# Medium-sized files (10-100MB)
GET /api/designs/?min_file_size_mb=10&max_file_size_mb=100

# Parts with 10-50 child components
GET /api/bom/?min_quantity=10&max_quantity=50
```

### Search + Sort

Combine text search with ordering:

```bash
# Search brackets, newest first
GET /api/series/?search=bracket&ordering=-created_at

# Search aluminum parts, sort by volume
GET /api/bom/?search=aluminum&ordering=-quantity
```

### Pagination

Control page size and navigate results:

```bash
# First page, 100 items
GET /api/designs/?page_size=100&page=1

# Second page, default size (50)
GET /api/designs/?page=2

# Get all audit logs in small batches
GET /api/audit/?page_size=10&page=1
```

## Performance Optimization

### Database Indexes

Key indexes for fast filtering:

- Organizations: `slug`, `is_active`
- Users: `username`, `email`, `is_active`
- DesignSeries: `part_number`, `status`, `organization`
- DesignAsset: `series`, `file_format`, `upload_status`, `created_at`
- AssemblyNode: `design_asset`, `depth`, `part_number`
- AuditLog: `timestamp`, `action`, `resource_type`, `actor_id`

### Query Optimization

1. **Use specific filters** instead of broad searches when possible
2. **Limit page size** for large result sets
3. **Order by indexed fields** for faster sorting
4. **Combine filters** to narrow results early

```bash
# SLOW: Broad search
GET /api/designs/?search=part

# FAST: Specific filters
GET /api/designs/?part_number=PN-001&file_format=step
```

### Select Related

ViewSets use `select_related` and `prefetch_related` to minimize queries:

- DesignAsset: Loads `series` and `uploaded_by` automatically
- DesignSeries: Loads `created_by` and `organization`
- ReviewSession: Prefetches `reviewers` and `markups`

## Error Handling

### Invalid Filters

Invalid filter names are silently ignored:

```bash
# 'invalid_field' is ignored, other filters applied
GET /api/designs/?file_format=step&invalid_field=value
```

### Type Errors

Invalid filter values return 400 Bad Request:

```bash
# Error: min_file_size must be numeric
GET /api/designs/?min_file_size=abc
```

### Date Format

Use ISO 8601 format for dates:

```bash
# Correct
?uploaded_after=2025-01-01
?uploaded_after=2025-01-01T10:30:00Z

# Incorrect
?uploaded_after=01/01/2025
```

## Testing

### cURL Examples

```bash
# Basic search
curl "http://localhost:8000/api/designs/?search=bracket"

# Multiple filters
curl "http://localhost:8000/api/designs/?file_format=step&min_file_size_mb=10&has_geometry=true"

# With authentication
curl -u username:password "http://localhost:8000/api/audit/?last_day=true"

# JSON output with jq
curl -s "http://localhost:8000/api/series/?status=RELEASED" | jq '.'
```

### Python Examples

```python
import requests

# Search for designs
response = requests.get(
    'http://localhost:8000/api/designs/',
    params={
        'search': 'bracket',
        'file_format': 'step',
        'has_geometry': 'true',
        'ordering': '-created_at'
    },
    auth=('username', 'password')
)

designs = response.json()['results']

# Filter audit logs
response = requests.get(
    'http://localhost:8000/api/audit/',
    params={
        'action': 'DOWNLOAD',
        'resource_type': 'DesignAsset',
        'last_week': 'true'
    },
    auth=('username', 'password')
)

logs = response.json()['results']
```

## Revision History

- **v1.0** (2025-12-16): Initial search & filtering implementation
  - django-filter integration for 8 models
  - 100+ filter parameters across all endpoints
  - Full-text search on key fields
  - Multi-field ordering
  - Date range and numeric range filters
  - ITAR compliance filtering
  - BOM hierarchy filtering
  - Audit log time-based shortcuts
