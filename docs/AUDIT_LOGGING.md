# Enginel Audit Logging System

## Overview
Comprehensive audit logging system for CMMC and ITAR compliance, tracking all critical operations on design assets, reviews, and markups with immutable, tamper-evident logs.

## Features

### 1. **Immutable Audit Trail**
- All audit logs are read-only after creation
- Actor information preserved even after user deletion (no FK constraints)
- Indexed by timestamp, actor, resource, and action for efficient querying

### 2. **Tracked Operations**
- **CREATE**: Design asset uploads, review creation, markup creation
- **READ**: File downloads (automatically logged)
- **UPDATE**: Design asset modifications, review updates, markup edits
- **DELETE**: Resource deletions with full snapshot preservation
- **DOWNLOAD**: File access tracking with IP and user agent
- **UPLOAD**: File upload events

### 3. **Audit Log Fields**
- `actor_id`: User ID (integer, preserved after deletion)
- `actor_username`: Username at time of action
- `action`: Operation type (CREATE/READ/UPDATE/DELETE/DOWNLOAD/UPLOAD)
- `resource_type`: Model name (e.g., 'DesignAsset', 'ReviewSession')
- `resource_id`: UUID of affected resource
- `ip_address`: Client IP (from X-Forwarded-For or REMOTE_ADDR)
- `user_agent`: Browser/client identification
- `changes`: JSON field with before/after values for updates
- `timestamp`: ISO-8601 timestamp with timezone

## API Endpoints

### List All Audit Logs
```http
GET /api/audit-logs/
```

**Query Parameters:**
- `actor_id`: Filter by user ID
- `resource_type`: Filter by model (e.g., 'DesignAsset')
- `resource_id`: Filter by specific resource UUID
- `action`: Filter by action type (CREATE/READ/UPDATE/DELETE/DOWNLOAD/UPLOAD)
- `start_date`: ISO-8601 date for range start
- `end_date`: ISO-8601 date for range end
- `ordering`: Sort by field (e.g., '-timestamp', 'action')

**Example:**
```bash
# Get all downloads from last 7 days
curl -H "Authorization: Token abc123" \
  "http://localhost:8000/api/audit-logs/?action=DOWNLOAD&start_date=2025-12-09"
```

### My Audit Logs
```http
GET /api/audit-logs/my_actions/
```
Returns all audit logs for the authenticated user.

### All Downloads
```http
GET /api/audit-logs/downloads/
```
Returns all DOWNLOAD audit logs across all users.

### Get Specific Log Entry
```http
GET /api/audit-logs/{id}/
```

## Automatic Logging

### ViewSet Integration
Three ViewSets use `AuditLogMixin` for automatic CREATE/UPDATE/DELETE logging:
- `DesignAssetViewSet`
- `ReviewSessionViewSet`
- `MarkupViewSet`

**Example logged operations:**
- Creating design asset → logs CREATE with field list
- Updating design revision → logs UPDATE with before/after values
- Deleting design → logs DELETE with full snapshot

### Decorator Usage
Custom actions use `@audit_action` decorator:

```python
@action(detail=True, methods=['get'])
@audit_action('DOWNLOAD')
def download(self, request, pk=None):
    design_asset = self.get_object()
    # ... download logic
    return response
```

## Manual Logging

### Direct Function Call
```python
from designs.audit import log_audit_event

log_audit_event(
    user=request.user,
    action='DOWNLOAD',
    resource_type='DesignAsset',
    resource_id=design_asset.id,
    request=request
)
```

### Track Model Changes
```python
from designs.audit import track_model_changes

old_values = {'revision': 'A', 'status': 'DRAFT'}
new_values = {'revision': 'B', 'status': 'COMPLETED'}

track_model_changes(
    instance=design_asset,
    old_values=old_values,
    new_values=new_values,
    user=request.user,
    request=request
)
```

## Compliance Features

### CMMC Requirements Met
✅ **Access Control (AC)**: IP address and user tracking  
✅ **Audit and Accountability (AU)**: Immutable timestamp records  
✅ **Identification and Authentication (IA)**: Actor ID preservation  
✅ **System and Information Integrity (SI)**: Change tracking with diffs  

### ITAR Considerations
- Tracks access to ITAR-classified designs
- Logs downloads for export control compliance
- Preserves actor information for accountability

### Data Retention
- No automatic deletion of audit logs
- Actor information persists after user deletion
- Full snapshot preservation for DELETE operations

## Testing

### Test Script
```bash
# Run comprehensive audit logging tests
python test_files/test_audit.py admin admin123 1 test_files/test_box.step
```

**Tests performed:**
1. CREATE: Upload design file
2. View audit logs for current user
3. UPDATE: Modify design properties
4. DOWNLOAD: Access file (logs IP + user agent)
5. View all download logs
6. Filter logs by resource ID
7. DELETE: Remove design (logs snapshot)

### Expected Output
```
✅ Created design asset: <uuid>
✅ Found X audit log entries
✅ Updated design asset: <uuid>
✅ Download initiated
✅ Total downloads logged: X
✅ Audit logs for design <uuid>:
   - CREATE by admin at 2025-12-16T...
   - UPDATE by admin at 2025-12-16T...
   - DOWNLOAD by admin at 2025-12-16T...
   - DELETE by admin at 2025-12-16T...
```

## Database Schema

### Indexes
- `(actor_id, timestamp)` - User activity timeline
- `(resource_type, resource_id)` - Resource history
- `(action, timestamp)` - Action type filtering

### Example Record
```json
{
  "id": "uuid",
  "actor_id": 1,
  "actor_username": "john.doe",
  "action": "UPDATE",
  "action_display": "Update",
  "resource_type": "DesignAsset",
  "resource_id": "design-uuid",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "changes": {
    "before": {"revision": "A", "status": "DRAFT"},
    "after": {"revision": "B", "status": "COMPLETED"},
    "changed_fields": ["revision", "status"]
  },
  "timestamp": "2025-12-16T10:30:45.123456Z"
}
```

## Security

### Read-Only API
- All endpoints are GET only (ReadOnlyModelViewSet)
- No CREATE/UPDATE/DELETE operations via API
- Audit logs created only through internal functions

### Permission Requirements
- Authenticated users can view their own logs
- Admin access required for viewing all logs (default DRF permissions)
- ITAR filtering respects user clearance levels

### IP Spoofing Protection
- Extracts IP from `X-Forwarded-For` header
- Falls back to `REMOTE_ADDR` if header absent
- Logs user agent for additional verification

## Future Enhancements

### Planned Features
- [ ] Audit log export (CSV/JSON)
- [ ] Anomaly detection (unusual download patterns)
- [ ] Scheduled compliance reports
- [ ] Integration with SIEM systems
- [ ] Long-term archival to S3 Glacier

### Integration Points
- S3 download URL generation (when implemented)
- Email notifications for critical actions
- Slack/Teams alerts for ITAR downloads
- Azure Monitor integration for production

## Troubleshooting

### Logs Not Appearing
1. Check ViewSet uses `AuditLogMixin` or `@audit_action` decorator
2. Verify operation returns 2xx status code
3. Check for exceptions in Django logs

### Missing IP Address
- Ensure reverse proxy forwards `X-Forwarded-For` header
- For local dev, IP may be 127.0.0.1

### Performance Issues
- Audit log table is indexed for fast queries
- Consider pagination for large result sets
- Use date range filters to limit query scope
