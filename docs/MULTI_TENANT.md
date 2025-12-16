# Multi-Tenant Organization Support

This document describes the multi-tenant organization system in Enginel, which enables complete data isolation between companies, teams, and customer organizations.

## Overview

The multi-tenant system provides:

1. **Complete Data Isolation**: Each organization's design data is completely isolated from other organizations
2. **Role-Based Access Control**: Organization members have specific roles (OWNER, ADMIN, MEMBER, VIEWER, GUEST)
3. **Resource Quotas**: Per-organization limits on users and storage
4. **Subscription Tiers**: Different feature sets based on subscription level
5. **Flexible Membership**: Users can belong to multiple organizations with different roles

## Architecture

### Core Models

#### Organization

Represents a company, team, or customer organization. All design data is scoped to an organization.

**Key Fields:**
- `name`: Organization name (e.g., "Acme Engineering")
- `slug`: URL-safe unique identifier (e.g., "acme-engineering")
- `subscription_tier`: FREE, STARTER, PROFESSIONAL, ENTERPRISE
- `max_users`: Maximum allowed members
- `max_storage_gb`: Storage quota in GB
- `is_us_organization`: ITAR compliance flag
- `is_active`: Enable/disable without deletion

#### OrganizationMembership

Links users to organizations with specific roles.

**Roles:**
- **OWNER**: Full admin access, can delete organization
- **ADMIN**: Can manage users and settings
- **MEMBER**: Can create and edit designs
- **VIEWER**: Read-only access
- **GUEST**: Limited read access

**Key Fields:**
- `organization`: Foreign key to Organization
- `user`: Foreign key to CustomUser
- `role`: User's role in this organization
- `joined_at`: Membership timestamp

### Model Changes

**DesignSeries** now includes:
- `organization`: Foreign key (required, nullable during migration)
- `unique_together`: `['organization', 'part_number']` (part numbers unique per org)

**Other Models** inherit organization context:
- `DesignAsset` → via `series.organization`
- `ReviewSession` → via `design_asset.series.organization`
- `AssemblyNode` → via `design_asset.series.organization`
- `Markup` → via `design_asset.series.organization`

## API Endpoints

### Organizations

#### List Organizations

Get all organizations user is a member of:

```http
GET /api/organizations/
Authorization: Bearer <token>
```

**Response:**
```json
[
    {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Acme Engineering",
        "slug": "acme-engineering",
        "description": "Leading CAD engineering firm",
        "is_active": true,
        "is_us_organization": true,
        "subscription_tier": "PROFESSIONAL",
        "max_users": 50,
        "max_storage_gb": 500,
        "member_count": 12,
        "storage_used_gb": 127.45,
        "contact_email": "admin@acme.com",
        "contact_phone": "+1-555-0123",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-15T10:30:00Z"
    }
]
```

#### Get Organization Details

```http
GET /api/organizations/{slug}/
Authorization: Bearer <token>
```

#### Create Organization

```http
POST /api/organizations/
Authorization: Bearer <token>
Content-Type: application/json

{
    "name": "New Engineering Co",
    "slug": "new-engineering",
    "description": "Startup CAD firm",
    "subscription_tier": "STARTER",
    "contact_email": "admin@neweng.com"
}
```

#### Get Organization Members

```http
GET /api/organizations/{slug}/members/
Authorization: Bearer <token>
```

**Response:**
```json
[
    {
        "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
        "organization": "550e8400-e29b-41d4-a716-446655440000",
        "organization_name": "Acme Engineering",
        "user": 1,
        "username": "john.smith",
        "email": "john@acme.com",
        "role": "OWNER",
        "joined_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z"
    },
    {
        "id": "8d1e7780-8536-51fe-a55c-f18fd2g01bf8",
        "organization": "550e8400-e29b-41d4-a716-446655440000",
        "organization_name": "Acme Engineering",
        "user": 2,
        "username": "jane.doe",
        "email": "jane@acme.com",
        "role": "ADMIN",
        "joined_at": "2025-01-05T14:20:00Z",
        "updated_at": "2025-01-05T14:20:00Z"
    }
]
```

#### Add Member to Organization

Requires OWNER or ADMIN role:

```http
POST /api/organizations/{slug}/add_member/
Authorization: Bearer <token>
Content-Type: application/json

{
    "user_id": 3,
    "role": "MEMBER"
}
```

**Response:**
```json
{
    "id": "9e2f8891-9647-62gf-b66d-g29ge3h12cg9",
    "organization": "550e8400-e29b-41d4-a716-446655440000",
    "organization_name": "Acme Engineering",
    "user": 3,
    "username": "bob.engineer",
    "email": "bob@acme.com",
    "role": "MEMBER",
    "joined_at": "2025-01-16T08:00:00Z",
    "updated_at": "2025-01-16T08:00:00Z"
}
```

#### Remove Member from Organization

Requires OWNER or ADMIN role:

```http
DELETE /api/organizations/{slug}/members/{user_id}/
Authorization: Bearer <token>
```

**Note:** Cannot remove the last OWNER from an organization.

### Design Series (with Organization Filtering)

#### List Design Series

Automatically filtered to user's organizations:

```http
GET /api/series/
Authorization: Bearer <token>
```

Filter by specific organization:

```http
GET /api/series/?organization=acme-engineering
Authorization: Bearer <token>
```

#### Create Design Series

Must specify organization and have MEMBER role or higher:

```http
POST /api/series/
Authorization: Bearer <token>
Content-Type: application/json

{
    "organization": "550e8400-e29b-41d4-a716-446655440000",
    "part_number": "TB-001",
    "name": "Turbine Blade",
    "description": "High-performance turbine blade design"
}
```

**Validation:**
- User must be a member of the specified organization
- User must have MEMBER role or higher
- Part number must be unique within the organization

### Current User Organizations

Get authenticated user's organization memberships:

```http
GET /api/users/me/
Authorization: Bearer <token>
```

**Response:**
```json
{
    "id": 1,
    "username": "john.smith",
    "email": "john@acme.com",
    "first_name": "John",
    "last_name": "Smith",
    "is_us_person": true,
    "security_clearance_level": "SECRET",
    "organization": "Acme Engineering",
    "phone_number": "+1-555-0123",
    "date_joined": "2025-01-01T00:00:00Z",
    "organizations": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "Acme Engineering",
            "slug": "acme-engineering",
            "role": "OWNER"
        },
        {
            "id": "661f9511-f3ab-52e5-b827-557766551111",
            "name": "Customer Org",
            "slug": "customer-org",
            "role": "VIEWER"
        }
    ]
}
```

## Permissions

### Organization Permissions

#### IsOrganizationMember

Enforces multi-tenant isolation. User must belong to the organization that owns the resource.

```python
# Applied automatically to Design Series and Design Assets
# Checks membership via:
# - obj.organization (for DesignSeries)
# - obj.series.organization (for DesignAsset)
# - obj.design_asset.series.organization (for nested resources)
```

#### CanManageOrganization

User must have OWNER or ADMIN role to manage organization settings and members.

```python
# Required for:
# - Adding/removing members
# - Updating organization settings
# - Changing subscription tier
```

#### CanCreateInOrganization

User must have MEMBER role or higher to create designs.

```python
# Required for:
# - Creating DesignSeries
# - Uploading DesignAssets
# - Creating ReviewSessions
```

### Role Capabilities

| Action | GUEST | VIEWER | MEMBER | ADMIN | OWNER |
|--------|-------|--------|--------|-------|-------|
| View designs | ✅ (limited) | ✅ | ✅ | ✅ | ✅ |
| Create designs | ❌ | ❌ | ✅ | ✅ | ✅ |
| Edit own designs | ❌ | ❌ | ✅ | ✅ | ✅ |
| Delete own designs | ❌ | ❌ | ✅ | ✅ | ✅ |
| Manage users | ❌ | ❌ | ❌ | ✅ | ✅ |
| Change settings | ❌ | ❌ | ❌ | ✅ | ✅ |
| Delete organization | ❌ | ❌ | ❌ | ❌ | ✅ |

## Data Migration

### Default Organization

During migration, a default organization is automatically created:

- **Name**: Default Organization
- **Slug**: `default`
- **Tier**: ENTERPRISE
- **Max Users**: 100
- **Max Storage**: 1000 GB

All existing:
- Design series are assigned to the default organization
- Users become ADMIN members of the default organization

### Multi-Tenant Migration Steps

1. **Create Organization and OrganizationMembership models**
2. **Add organization FK to DesignSeries** (nullable initially)
3. **Run data migration** to create default org and assign data
4. **Update QuerySets** in ViewSets to filter by user's organizations
5. **Update Serializers** to include organization fields
6. **Add Permissions** for organization-based access control

## Usage Examples

### Creating a New Organization

```bash
curl -X POST http://localhost:8000/api/organizations/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Defense Contractor Inc",
    "slug": "defense-contractor",
    "is_us_organization": true,
    "subscription_tier": "ENTERPRISE",
    "contact_email": "admin@defense.com"
  }'
```

### Adding Team Members

```bash
# Add as MEMBER
curl -X POST http://localhost:8000/api/organizations/defense-contractor/add_member/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 5,
    "role": "MEMBER"
  }'

# Add as ADMIN
curl -X POST http://localhost:8000/api/organizations/defense-contractor/add_member/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 6,
    "role": "ADMIN"
  }'
```

### Creating Organization-Scoped Design

```bash
# Get organization ID
ORG_ID=$(curl http://localhost:8000/api/organizations/defense-contractor/ \
  -H "Authorization: Bearer $TOKEN" | jq -r '.id')

# Create design series
curl -X POST http://localhost:8000/api/series/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"organization\": \"$ORG_ID\",
    \"part_number\": \"CLASSIFIED-001\",
    \"name\": \"Classified Component\"
  }"
```

### Listing Organization Designs

```bash
# All designs in user's organizations
curl http://localhost:8000/api/series/ \
  -H "Authorization: Bearer $TOKEN"

# Designs in specific organization
curl http://localhost:8000/api/series/?organization=defense-contractor \
  -H "Authorization: Bearer $TOKEN"
```

## Resource Quotas

### User Limit

```python
# Check if at limit
org = Organization.objects.get(slug='acme-engineering')
if org.is_at_user_limit():
    print("Cannot add more users")

# Current usage
print(f"Members: {org.get_member_count()} / {org.max_users}")
```

### Storage Limit

```python
# Check storage usage
storage_gb = org.get_storage_used_gb()
if org.is_at_storage_limit():
    print(f"Storage limit reached: {storage_gb} / {org.max_storage_gb} GB")
```

## Subscription Tiers

### FREE
- Max 5 users
- 10 GB storage
- Basic features

### STARTER
- Max 20 users
- 100 GB storage
- Standard features

### PROFESSIONAL
- Max 50 users
- 500 GB storage
- Advanced features
- Priority support

### ENTERPRISE
- Unlimited users
- Custom storage
- All features
- Dedicated support
- SLA guarantees

## Security Considerations

### Multi-Tenant Isolation

1. **QuerySet Filtering**: All ViewSets automatically filter by user's organizations
2. **Permission Checks**: Object-level permissions verify organization membership
3. **Unique Constraints**: Part numbers unique per organization (not globally)
4. **Audit Logging**: All organization changes are logged

### ITAR Compliance

Organizations have `is_us_organization` flag. Combined with user's `is_us_person` flag and design's `classification`, this ensures:

- US organizations can have ITAR designs
- Non-US users cannot access ITAR designs
- Audit trail tracks all access attempts

## Testing Multi-Tenant Isolation

Create two organizations and verify isolation:

```bash
# Create Org A
ORG_A=$(curl -X POST http://localhost:8000/api/organizations/ \
  -H "Authorization: Bearer $TOKEN_USER1" \
  -H "Content-Type: application/json" \
  -d '{"name": "Org A", "slug": "org-a"}' | jq -r '.id')

# Create Org B
ORG_B=$(curl -X POST http://localhost:8000/api/organizations/ \
  -H "Authorization: Bearer $TOKEN_USER2" \
  -H "Content-Type: application/json" \
  -d '{"name": "Org B", "slug": "org-b"}' | jq -r '.id')

# User 1 creates design in Org A
curl -X POST http://localhost:8000/api/series/ \
  -H "Authorization: Bearer $TOKEN_USER1" \
  -H "Content-Type: application/json" \
  -d "{\"organization\": \"$ORG_A\", \"part_number\": \"A-001\", \"name\": \"Org A Design\"}"

# User 2 tries to list designs (should NOT see Org A's design)
curl http://localhost:8000/api/series/ \
  -H "Authorization: Bearer $TOKEN_USER2"
```

## Migration Guide

### For Existing Single-Tenant Installations

1. **Backup database** before migration
2. **Run migrations**:
   ```bash
   docker-compose exec web python manage.py migrate designs
   ```
3. **Verify default organization** was created
4. **Verify all users** are members of default org
5. **Verify all designs** are assigned to default org
6. **Create additional organizations** as needed
7. **Reassign designs** if moving from default org

### Moving Designs Between Organizations

Currently not supported via API. Would require admin script:

```python
# Admin script (not via API)
from designs.models import DesignSeries, Organization

new_org = Organization.objects.get(slug='target-org')
series = DesignSeries.objects.get(part_number='TB-001')

# Verify no part_number conflict
if DesignSeries.objects.filter(organization=new_org, part_number=series.part_number).exists():
    raise ValueError("Part number already exists in target organization")

series.organization = new_org
series.save()
```

## Admin Interface

Organizations can be managed via Django Admin:

```
http://localhost:8000/admin/designs/organization/
http://localhost:8000/admin/designs/organizationmembership/
```

Admin users can:
- View all organizations
- Edit organization settings
- Manage memberships
- View resource usage stats

## Future Enhancements

- [ ] Organization-level API keys for automation
- [ ] Billing integration per organization
- [ ] Custom branding per organization
- [ ] Organization-level audit logs
- [ ] Resource usage analytics dashboard
- [ ] Automated storage quota enforcement
- [ ] Organization data export (GDPR compliance)
- [ ] Cross-organization sharing with permissions

## References

- `designs/models.py`: Organization and OrganizationMembership models
- `designs/serializers.py`: Organization serializers
- `designs/views.py`: OrganizationViewSet
- `designs/permissions.py`: Multi-tenant permissions
- `designs/migrations/0005_add_multi_tenant_organizations.py`: Schema migration
- `designs/migrations/0006_populate_default_organization.py`: Data migration

## Revision History

- **v1.0** (2025-12-16): Initial multi-tenant implementation
  - Organization and OrganizationMembership models
  - 5 roles (OWNER, ADMIN, MEMBER, VIEWER, GUEST)
  - Complete data isolation via QuerySet filtering
  - Resource quotas and subscription tiers
  - Default organization for existing data
