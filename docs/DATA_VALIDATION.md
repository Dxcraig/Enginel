# Data Validation System

## Overview

The Enginel Data Validation System provides a comprehensive, flexible framework for validating data integrity, enforcing business rules, and maintaining data quality across the platform. The system supports custom validation rules with multiple severity levels, automatic validation on model operations, detailed validation reporting with override capabilities, and complete audit trails for compliance.

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Validation Models](#validation-models)
- [Custom Validators](#custom-validators)
- [Validation Service](#validation-service)
- [API Endpoints](#api-endpoints)
- [Usage Examples](#usage-examples)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Features

### Core Capabilities

- **Custom Validation Rules**: Define reusable validation rules with flexible configuration
- **Multiple Rule Types**: Regex, range, length, format, file validation, business rules, and custom expressions
- **Severity Levels**: INFO, WARNING, ERROR, CRITICAL
- **Automatic Validation**: Apply rules automatically on create/update operations
- **Conditional Application**: Rules can have conditions for when they apply
- **Multi-Tenant Support**: Organization-specific and global rules
- **Validation Results Tracking**: Complete audit trail of all validations
- **Override Capability**: Admin users can override validation failures with reasons
- **Statistics & Reporting**: Track validation success rates and failure patterns
- **Field-Level Validation**: Validate specific field values before saving
- **Batch Validation**: Validate multiple items efficiently

### Built-in Validators

1. **File Validators**
   - File extension validation
   - File size limits (min/max)
   - MIME type validation
   - CAD file format validation (STEP, IGES, STL)

2. **String Validators**
   - Part number format
   - Revision format
   - URL-safe slugs
   - Alphanumeric validation

3. **Numeric Validators**
   - Positive numbers
   - Non-negative numbers
   - Range validation (with inclusive/exclusive options)

4. **Business Rule Validators**
   - ITAR compliance checking
   - Organization quota validation
   - Unique version validation
   - Geometry validation

5. **Collection Validators**
   - Maximum list length
   - Minimum list length

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Validation System                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐ │
│  │ ValidationRule │  │ValidationResult│  │  Validators  │ │
│  │     Model      │  │     Model      │  │   (Custom)   │ │
│  └────────────────┘  └────────────────┘  └──────────────┘ │
│           │                   │                   │         │
│           └───────────────────┴───────────────────┘         │
│                           │                                 │
│                  ┌────────▼──────────┐                     │
│                  │ ValidationService │                     │
│                  │   (Core Logic)    │                     │
│                  └────────┬──────────┘                     │
│                           │                                 │
│           ┌───────────────┼───────────────┐               │
│           │               │               │               │
│  ┌────────▼────────┐ ┌───▼────┐ ┌────────▼───────┐      │
│  │  API Endpoints  │ │ Signals│ │  Decorators    │      │
│  │  (REST Views)   │ │        │ │  (@validate_*) │      │
│  └─────────────────┘ └────────┘ └────────────────┘      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Rule Definition**: Admin creates validation rules via API or Django admin
2. **Rule Storage**: Rules stored in `ValidationRule` model with configuration
3. **Validation Trigger**: Validation triggered by:
   - Model save operations
   - Explicit API calls
   - Serializer validation
   - Custom service calls
4. **Rule Application**: ValidationService applies applicable rules
5. **Result Recording**: ValidationResult records created for audit trail
6. **Action Taken**: Based on severity:
   - INFO/WARNING: Log and proceed
   - ERROR/CRITICAL: Block operation
   - Override: Admin can override with reason

## Validation Models

### ValidationRule

Defines a reusable validation rule.

**Fields:**
- `id` (UUID): Unique identifier
- `name` (str): Unique name for the rule
- `description` (str): What the rule validates
- `rule_type` (choice): Type of validation (REGEX, RANGE, LENGTH, etc.)
- `target_model` (choice): Model to validate (DesignAsset, Organization, etc.)
- `target_field` (str): Specific field to validate (optional for model-level rules)
- `rule_config` (JSON): Configuration specific to rule type
- `error_message` (str): Message displayed on validation failure
- `severity` (choice): INFO, WARNING, ERROR, CRITICAL
- `is_active` (bool): Whether rule is currently active
- `apply_on_create` (bool): Apply when creating records
- `apply_on_update` (bool): Apply when updating records
- `conditions` (JSON): Conditional logic for when to apply
- `organization` (FK): If set, rule only applies to this organization
- `created_by` (FK): User who created the rule
- `total_checks` (int): Total validation checks performed
- `total_failures` (int): Total validation failures

**Methods:**
- `get_failure_rate()`: Calculate failure percentage
- `increment_checks()`: Increment check counter
- `increment_failures()`: Increment failure counter

### ValidationResult

Records the outcome of a validation check.

**Fields:**
- `id` (UUID): Unique identifier
- `rule` (FK): Validation rule that was applied
- `target_model` (str): Model that was validated
- `target_id` (UUID): ID of the record validated
- `target_field` (str): Field that was validated
- `status` (choice): PASSED, FAILED, SKIPPED, ERROR
- `error_message` (str): Error message if failed
- `details` (JSON): Detailed validation context
- `validated_by` (FK): User who triggered validation
- `validated_at` (datetime): When validation occurred
- `was_blocked` (bool): Whether operation was blocked
- `was_overridden` (bool): Whether failure was overridden
- `override_reason` (str): Reason for override
- `override_by` (FK): User who overrode
- `override_at` (datetime): When overridden

**Methods:**
- `override(user, reason)`: Override a failed validation

## Custom Validators

### File Validators

#### FileExtensionValidator

```python
from designs.validators import FileExtensionValidator

validator = FileExtensionValidator(
    allowed_extensions=['.step', '.stp', '.iges', '.igs'],
    case_sensitive=False
)
validator(file_field)
```

#### FileSizeValidator

```python
from designs.validators import FileSizeValidator

validator = FileSizeValidator(
    min_size=1024,           # 1 KB minimum
    max_size=500 * 1024 * 1024  # 500 MB maximum
)
validator(file_field)
```

#### CADFileValidator

```python
from designs.validators import CADFileValidator

validator = CADFileValidator(formats=['step', 'iges', 'stl'])
validator(cad_file)
```

### String Validators

#### PartNumberValidator

```python
from designs.validators import PartNumberValidator

validator = PartNumberValidator()
validator('ABC-123-XYZ')  # Valid
validator('abc-123')      # Invalid (must be uppercase)
```

#### RevisionValidator

```python
from designs.validators import RevisionValidator

validator = RevisionValidator()
validator('A')      # Valid
validator('REV01')  # Valid
validator('abc')    # Invalid (must be uppercase)
```

### Numeric Validators

#### RangeValidator

```python
from designs.validators import RangeValidator

validator = RangeValidator(
    min_value=0,
    max_value=100,
    inclusive=True
)
validator(50)   # Valid
validator(101)  # Invalid
```

### Business Rule Validators

#### ITARComplianceValidator

```python
from designs.validators import ITARComplianceValidator

validator = ITARComplianceValidator()
validator({
    'classification': 'ITAR',
    'uploaded_by': user  # Must have is_us_person=True
})
```

#### OrganizationQuotaValidator

```python
from designs.validators import OrganizationQuotaValidator

validator = OrganizationQuotaValidator(quota_type='storage')
validator(organization)  # Checks if at storage limit
```

## Validation Service

### ValidationService Class

Central service for applying validation rules.

#### Methods

##### validate_model_instance()

```python
from designs.validation_service import ValidationService

service = ValidationService()
is_valid, results = service.validate_model_instance(
    instance=design_asset,
    operation='create',
    user=request.user,
    organization=org
)

if not is_valid:
    # Handle validation failures
    for result in results:
        if result.status == 'FAILED':
            print(f"Error: {result.error_message}")
```

##### validate_field_value()

```python
is_valid, results = service.validate_field_value(
    model_name='DesignAsset',
    field_name='filename',
    value='bracket.step',
    user=request.user,
    organization=org
)
```

##### validate_batch()

```python
report = service.validate_batch(
    instances=[asset1, asset2, asset3],
    operation='create',
    user=request.user,
    organization=org
)

print(f"Valid: {report['valid']}, Invalid: {report['invalid']}")
```

##### get_validation_report()

```python
from datetime import datetime, timedelta

report = service.get_validation_report(
    model_name='DesignAsset',
    start_date=datetime.now() - timedelta(days=7),
    end_date=datetime.now(),
    organization=org
)

print(f"Pass rate: {report['pass_rate']}%")
print(f"Total checks: {report['stats']['total']}")
```

### Decorators

#### @validate_on_save

```python
from designs.validation_service import validate_on_save
from django.db import models

@validate_on_save
class MyModel(models.Model):
    name = models.CharField(max_length=100)
    # ... fields ...
```

Automatically validates model before saving. Raises `ValidationError` if validation fails.

## API Endpoints

### Validation Rules Management

#### List Validation Rules

```http
GET /api/validation/rules/
Authorization: Token <your-token>
```

**Query Parameters:**
- `rule_type`: Filter by rule type
- `target_model`: Filter by target model
- `severity`: Filter by severity
- `is_active`: Filter by active status
- `search`: Search in name, description, target_field
- `ordering`: Order by created_at, name, total_checks, total_failures

**Response:**
```json
{
  "count": 10,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "name": "Valid Part Number",
      "description": "Ensure part numbers follow naming convention",
      "rule_type": "REGEX",
      "target_model": "DesignAsset",
      "target_field": "filename",
      "rule_config": {
        "pattern": "^[A-Z0-9][A-Z0-9_-]*[A-Z0-9]$"
      },
      "error_message": "Invalid part number format",
      "severity": "ERROR",
      "is_active": true,
      "apply_on_create": true,
      "apply_on_update": true,
      "total_checks": 150,
      "total_failures": 5,
      "failure_rate": 3.33
    }
  ]
}
```

#### Create Validation Rule

```http
POST /api/validation/rules/
Authorization: Token <your-token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "File Size Limit",
  "description": "Ensure files don't exceed 500MB",
  "rule_type": "FILE_SIZE",
  "target_model": "DesignAsset",
  "target_field": "file",
  "rule_config": {
    "max_size": 524288000
  },
  "error_message": "File size must not exceed 500MB",
  "severity": "ERROR",
  "is_active": true,
  "apply_on_create": true,
  "apply_on_update": false
}
```

#### Update Validation Rule

```http
PATCH /api/validation/rules/{id}/
Authorization: Token <your-token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "is_active": false
}
```

#### Delete Validation Rule

```http
DELETE /api/validation/rules/{id}/
Authorization: Token <your-token>
```

#### Activate/Deactivate Rule

```http
POST /api/validation/rules/{id}/activate/
POST /api/validation/rules/{id}/deactivate/
Authorization: Token <your-token>
```

#### Get Rule Statistics

```http
GET /api/validation/rules/{id}/statistics/
Authorization: Token <your-token>
```

**Response:**
```json
{
  "rule": { /* rule details */ },
  "statistics": {
    "total_checks": 1000,
    "total_failures": 50,
    "failure_rate": 5.0,
    "recent_100": {
      "total": 100,
      "passed": 95,
      "failed": 5,
      "pass_rate": 95.0
    }
  }
}
```

### Validation Results

#### List Validation Results

```http
GET /api/validation/results/
Authorization: Token <your-token>
```

**Query Parameters:**
- `status`: Filter by PASSED, FAILED, SKIPPED, ERROR
- `target_model`: Filter by model name
- `was_blocked`: Filter blocked operations
- `was_overridden`: Filter overridden results
- `search`: Search in rule name, error message, target_id

**Response:**
```json
{
  "count": 100,
  "results": [
    {
      "id": "uuid",
      "rule_name": "File Size Limit",
      "rule_type": "FILE_SIZE",
      "rule_severity": "ERROR",
      "target_model": "DesignAsset",
      "target_id": "asset-uuid",
      "target_field": "file",
      "status": "FAILED",
      "error_message": "File size must not exceed 500MB",
      "validated_by_username": "john_doe",
      "validated_at": "2025-12-16T10:30:00Z",
      "was_blocked": true,
      "was_overridden": false
    }
  ]
}
```

#### Override Validation Failure

```http
POST /api/validation/results/{id}/override/
Authorization: Token <your-token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "reason": "Approved by engineering director. File is necessary for customer requirement."
}
```

**Response:**
```json
{
  "message": "Validation overridden successfully",
  "result": { /* updated result */ }
}
```

### Field Validation

#### Validate Field Value

```http
POST /api/validation/validate-field/
Authorization: Token <your-token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "model_name": "DesignAsset",
  "field_name": "filename",
  "value": "BRACKET_V2.step",
  "organization_id": "org-uuid"
}
```

**Response:**
```json
{
  "is_valid": true,
  "field_name": "filename",
  "value": "BRACKET_V2.step",
  "results": [
    {
      "id": "result-uuid",
      "rule_name": "Valid Filename Format",
      "status": "PASSED",
      "validated_at": "2025-12-16T10:30:00Z"
    }
  ]
}
```

### Validation Reports

#### Get Validation Report

```http
GET /api/validation/report/
Authorization: Token <your-token>
```

**Query Parameters:**
- `model_name`: Filter by model
- `start_date`: Report start date (ISO 8601)
- `end_date`: Report end date (ISO 8601)
- `organization_id`: Filter by organization

**Response:**
```json
{
  "period": {
    "start": "2025-12-09T00:00:00Z",
    "end": "2025-12-16T00:00:00Z"
  },
  "stats": {
    "total": 1000,
    "passed": 950,
    "failed": 40,
    "blocked": 35,
    "overridden": 5
  },
  "by_severity": {
    "ERROR": 30,
    "WARNING": 10
  },
  "by_type": {
    "REGEX": 20,
    "FILE_SIZE": 15,
    "RANGE": 5
  },
  "top_failing_rules": [
    {
      "rule__name": "File Size Limit",
      "rule__id": "uuid",
      "count": 15
    }
  ],
  "pass_rate": 95.0
}
```

#### Get Validation Statistics

```http
GET /api/validation/statistics/
Authorization: Token <your-token>
```

**Response:**
```json
{
  "rules": {
    "total_active": 25,
    "by_type": {
      "REGEX": 10,
      "RANGE": 5,
      "FILE_SIZE": 4,
      "BUSINESS_RULE": 6
    }
  },
  "last_7_days": {
    "total_checks": 5000,
    "passed": 4750,
    "failed": 200,
    "blocked": 180,
    "pass_rate": 95.0
  }
}
```

## Usage Examples

### Example 1: Create a Part Number Validation Rule

```python
import requests

# Create validation rule
response = requests.post(
    'http://localhost:8000/api/validation/rules/',
    headers={'Authorization': f'Token {token}'},
    json={
        'name': 'Part Number Format',
        'description': 'Ensure part numbers are uppercase alphanumeric with hyphens',
        'rule_type': 'REGEX',
        'target_model': 'DesignSeries',
        'target_field': 'part_number',
        'rule_config': {
            'pattern': '^[A-Z0-9][A-Z0-9_-]*[A-Z0-9]$'
        },
        'error_message': 'Part number must be uppercase alphanumeric (A-Z, 0-9, -, _)',
        'severity': 'ERROR',
        'is_active': True,
        'apply_on_create': True,
        'apply_on_update': True
    }
)

rule = response.json()
print(f"Created rule: {rule['id']}")
```

### Example 2: Validate File Before Upload

```python
# Validate filename before creating design asset
response = requests.post(
    'http://localhost:8000/api/validation/validate-field/',
    headers={'Authorization': f'Token {token}'},
    json={
        'model_name': 'DesignAsset',
        'field_name': 'filename',
        'value': 'bracket_assembly.step'
    }
)

validation = response.json()
if validation['is_valid']:
    # Proceed with upload
    print("Filename is valid, proceeding with upload")
else:
    # Show errors
    for result in validation['results']:
        if result['status'] == 'FAILED':
            print(f"Error: {result['error_message']}")
```

### Example 3: Create File Size Limit Rule

```python
# Create rule to limit CAD file uploads to 500MB
response = requests.post(
    'http://localhost:8000/api/validation/rules/',
    headers={'Authorization': f'Token {token}'},
    json={
        'name': 'CAD File Size Limit',
        'description': 'Limit CAD files to 500MB',
        'rule_type': 'FILE_SIZE',
        'target_model': 'DesignAsset',
        'target_field': 'file',
        'rule_config': {
            'max_size': 524288000  # 500MB in bytes
        },
        'error_message': 'CAD file must not exceed 500MB. Please compress or simplify the model.',
        'severity': 'ERROR',
        'is_active': True,
        'apply_on_create': True,
        'apply_on_update': False
    }
)
```

### Example 4: Create ITAR Compliance Rule

```python
# Business rule to enforce ITAR compliance
response = requests.post(
    'http://localhost:8000/api/validation/rules/',
    headers={'Authorization': f'Token {token}'},
    json={
        'name': 'ITAR Access Control',
        'description': 'Only US persons can access ITAR-controlled designs',
        'rule_type': 'BUSINESS_RULE',
        'target_model': 'DesignAsset',
        'target_field': '',  # Model-level rule
        'rule_config': {
            'rule_name': 'itar_compliance'
        },
        'error_message': 'You do not have clearance to access ITAR-controlled designs',
        'severity': 'CRITICAL',
        'is_active': True,
        'apply_on_create': True,
        'apply_on_update': False,
        'conditions': {
            'classification': 'ITAR'
        }
    }
)
```

### Example 5: Get Validation Report

```python
from datetime import datetime, timedelta

# Get validation report for last 30 days
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

response = requests.get(
    'http://localhost:8000/api/validation/report/',
    headers={'Authorization': f'Token {token}'},
    params={
        'model_name': 'DesignAsset',
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat()
    }
)

report = response.json()
print(f"Validation Pass Rate: {report['pass_rate']}%")
print(f"Total Checks: {report['stats']['total']}")
print(f"Failures: {report['stats']['failed']}")
print(f"Blocked Operations: {report['stats']['blocked']}")

# Show top failing rules
print("\nTop Failing Rules:")
for rule in report['top_failing_rules']:
    print(f"  - {rule['rule__name']}: {rule['count']} failures")
```

### Example 6: Override Validation Failure

```python
# Admin overrides a validation failure
response = requests.post(
    f'http://localhost:8000/api/validation/results/{result_id}/override/',
    headers={'Authorization': f'Token {admin_token}'},
    json={
        'reason': 'Customer has provided special authorization for this file size. See ticket #12345.'
    }
)

if response.status_code == 200:
    print("Validation overridden successfully")
else:
    print(f"Error: {response.json()}")
```

### Example 7: Programmatic Validation in Code

```python
from designs.validation_service import ValidationService
from designs.models import DesignAsset

# Validate design asset before saving
design_asset = DesignAsset(
    series=series,
    version_number=2,
    filename='bracket.step',
    # ... other fields
)

service = ValidationService()
is_valid, results = service.validate_model_instance(
    instance=design_asset,
    operation='create',
    user=request.user
)

if is_valid:
    design_asset.save()
    print("Design asset saved successfully")
else:
    # Collect error messages
    errors = [r.error_message for r in results if r.status == 'FAILED']
    print(f"Validation failed: {', '.join(errors)}")
```

## Best Practices

### Rule Design

1. **Clear Error Messages**: Write descriptive error messages that guide users
   ```python
   # Good
   error_message="Part number must be uppercase (A-Z), numbers (0-9), and hyphens (-). Example: ABC-123-XYZ"
   
   # Bad
   error_message="Invalid format"
   ```

2. **Appropriate Severity**: Use severity levels correctly
   - `INFO`: Informational messages, doesn't block
   - `WARNING`: Potential issues, doesn't block
   - `ERROR`: Validation failure, blocks operation
   - `CRITICAL`: Serious violation, blocks and flags for review

3. **Specific Targeting**: Target specific fields when possible
   ```python
   # Good - Field-specific
   target_model='DesignAsset'
   target_field='filename'
   
   # Use model-level only when needed
   target_model='DesignAsset'
   target_field=''  # Validates entire model
   ```

4. **Conditional Application**: Use conditions to apply rules selectively
   ```python
   rule_config={...},
   conditions={
       'classification': 'ITAR',  # Only apply to ITAR designs
       'is_active': True
   }
   ```

### Performance

1. **Rule Efficiency**: Keep validation logic simple and fast
2. **Batch Validation**: Use batch validation for multiple items
3. **Cache Results**: Validation results are stored for audit, not re-run
4. **Index Queries**: Use appropriate filters when querying results

### Security

1. **Custom Expressions**: Be cautious with CUSTOM rule type
2. **Override Permission**: Only admins should override critical validations
3. **Audit Trail**: Never delete validation results
4. **Organization Isolation**: Use organization field for multi-tenant rules

### Maintenance

1. **Monitor Failure Rates**: Regularly review rules with high failure rates
2. **Update Rules**: Keep validation rules current with business requirements
3. **Clean Up**: Deactivate obsolete rules rather than deleting
4. **Document Rules**: Use clear descriptions for all rules

## Troubleshooting

### Common Issues

#### Validation Not Running

**Problem**: Rules exist but validations aren't being applied

**Solutions**:
1. Check if rule is active: `is_active=True`
2. Verify `apply_on_create` or `apply_on_update` is True
3. Check if conditions are met
4. Confirm target_model matches model name exactly
5. Verify organization matches (if set)

#### False Failures

**Problem**: Validation failing incorrectly

**Solutions**:
1. Review rule_config for typos
2. Test regex patterns in a regex tester
3. Check field value type matches validator expectations
4. Verify conditions aren't too restrictive

#### Performance Issues

**Problem**: Validation slowing down operations

**Solutions**:
1. Profile which rules are slow
2. Simplify complex custom expressions
3. Use field-level instead of model-level validation
4. Batch validate when possible
5. Consider async validation for non-critical rules

#### Override Not Working

**Problem**: Can't override validation failures

**Solutions**:
1. Verify user has admin permissions
2. Check if result status is 'FAILED'
3. Ensure result hasn't been overridden already
4. Provide reason (minimum 10 characters)

### Error Messages

#### "No active rules found"
- No validation rules are defined or active for the target model
- Create rules or activate existing ones

#### "Rule configuration invalid"
- `rule_config` JSON doesn't match expected format for rule type
- See rule type documentation for required config fields

#### "Permission denied to override"
- User doesn't have admin privileges
- Only staff or organization admins can override validations

#### "Validation result not found"
- Invalid result ID provided
- Result may have been from different organization

## Configuration

### Settings

Add to `settings.py`:

```python
# Validation settings
VALIDATION_ENABLED = True
VALIDATION_BATCH_SIZE = 100
VALIDATION_CACHE_TIMEOUT = 300  # seconds
```

### Signals

Validation can be triggered by Django signals:

```python
from django.db.models.signals import pre_save
from designs.validation_service import ValidationService

@receiver(pre_save, sender=DesignAsset)
def validate_design_asset(sender, instance, **kwargs):
    service = ValidationService()
    is_valid, results = service.validate_model_instance(
        instance=instance,
        operation='update' if instance.pk else 'create'
    )
    
    if not is_valid:
        from django.core.exceptions import ValidationError
        errors = [r.error_message for r in results if r.status == 'FAILED']
        raise ValidationError('; '.join(errors))
```

## Admin Interface

The Django admin interface provides full management of validation rules and results:

### Features

- **Color-coded Badges**: Status and severity displayed with visual indicators
- **Bulk Actions**: Activate/deactivate rules, reset statistics
- **Filtering**: Filter by type, model, severity, status
- **Search**: Search rules and results
- **Statistics**: View failure rates and check counts
- **Override Management**: Review and manage overrides

### Accessing Admin

1. Navigate to `/admin/`
2. Login with admin credentials
3. Find "Validation Rules" and "Validation Results" sections

## API Authentication

All validation endpoints require authentication:

```python
# Token Authentication
headers = {
    'Authorization': f'Token {your_token}'
}

# Session Authentication (for web interface)
# Handled automatically by browser cookies
```

## Rate Limiting

Validation API endpoints have rate limits:

- Standard users: 100 requests/minute
- Admin users: 1000 requests/minute
- Field validation: 200 requests/minute

## Support

For issues or questions:

1. Check this documentation
2. Review validation results for error details
3. Examine rule configuration
4. Check Django logs
5. Contact system administrator

## Version History

### v1.0.0 (2025-12-16)

- Initial release
- Core validation framework
- 10+ built-in validators
- Complete API endpoints
- Admin interface
- Validation reporting

## Appendix

### Rule Type Reference

| Rule Type | Description | Required Config |
|-----------|-------------|-----------------|
| REGEX | Regular expression pattern matching | `pattern` |
| RANGE | Numeric value range | `min`, `max` |
| LENGTH | String/list length | `min`, `max` |
| FORMAT | Specific format (email, url, phone, date) | `type` |
| CUSTOM | Custom Python expression | `expression` |
| FILE_TYPE | File extension validation | `allowed_types` |
| FILE_SIZE | File size limits | `min_size`, `max_size` |
| UNIQUENESS | Unique field value | (auto) |
| RELATIONSHIP | Foreign key validation | `related_model` |
| BUSINESS_RULE | Custom business logic | `rule_name` |

### Example Rule Configurations

#### REGEX Rule
```json
{
  "pattern": "^[A-Z0-9-]+$"
}
```

#### RANGE Rule
```json
{
  "min": 0,
  "max": 100
}
```

#### LENGTH Rule
```json
{
  "min": 3,
  "max": 50
}
```

#### FORMAT Rule
```json
{
  "type": "email"
}
```

#### CUSTOM Rule
```json
{
  "expression": "len(value) > 0 and value.isupper()"
}
```

#### FILE_TYPE Rule
```json
{
  "allowed_types": [".step", ".stp", ".iges", ".igs"]
}
```

#### FILE_SIZE Rule
```json
{
  "max_size": 524288000
}
```

#### BUSINESS_RULE Rule
```json
{
  "rule_name": "itar_compliance"
}
```
