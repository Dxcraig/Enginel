# Validation Rules Manager

Comprehensive validation system for enforcing data quality and business rules across Enginel designs.

## Features

### Validation Rules Management
- **Create/Edit Rules**: Define custom validation rules with flexible configuration
- **Rule Types**: 10 different validation types
  - Regular Expression (REGEX)
  - Numeric Range (RANGE)
  - String Length (LENGTH)
  - Format Validation (FORMAT)
  - Custom Expression (CUSTOM)
  - File Type (FILE_TYPE)
  - File Size (FILE_SIZE)
  - Uniqueness Check (UNIQUENESS)
  - Relationship Validation (RELATIONSHIP)
  - Business Rule (BUSINESS_RULE)

### Severity Levels
- **INFO**: Informational only
- **WARNING**: Important but non-blocking
- **ERROR**: Must be resolved
- **CRITICAL**: Blocks all operations

### Target Models
- Design Asset
- Design Series
- User (CustomUser)
- Review Session
- Markup
- Assembly Node
- All Models (*)

### Rule Statistics
- Total checks performed
- Total failures
- Failure rate percentage
- Recent 100 checks pass rate
- Historical trend analysis

### Validation Results
- Real-time validation tracking
- Status: PASSED, FAILED, SKIPPED, ERROR
- Detailed error messages
- Timestamp and user tracking
- Override capability

## Pages

### Validation Rules List (`/validation`)
- View all validation rules
- Filter by:
  - Status (Active/Inactive)
  - Severity level
  - Target model
- Quick actions:
  - View details
  - Edit rule
  - Activate/Deactivate
  - Delete rule
- Statistics at a glance

### Create Rule (`/validation/create`)
- Form-based rule creation
- Guided configuration with examples
- JSON configuration editor
- Application settings:
  - Apply on create
  - Apply on update
  - Active status

### Rule Detail (`/validation/[id]`)
- Comprehensive statistics dashboard
- Rule configuration display
- Recent validation results table
- Quick activate/deactivate toggle
- Edit rule button

### Design Validation Results
- Integrated into design detail page
- Validation tab shows all results for the design
- Status indicators
- Field-level validation display

## Integration

### Design Detail Page
The validation tab on [/designs/[id]/page.tsx](app/designs/[id]/page.tsx) shows:
- All validation results for the design
- Status (PASSED/FAILED/SKIPPED/ERROR)
- Rule name
- Field validated
- Error messages
- Validation timestamp

### Navbar
Validation link added to main navigation for quick access.

## Usage

### Creating a Validation Rule

1. Navigate to `/validation`
2. Click "+ Create Rule"
3. Fill in basic information:
   - Name
   - Description
4. Configure rule:
   - Select rule type
   - Choose target model
   - Specify target field (optional)
   - Define rule configuration (JSON)
5. Set error handling:
   - Error message
   - Severity level
6. Configure activation settings:
   - Active/Inactive
   - Apply on create
   - Apply on update
7. Click "Create Rule"

### Rule Configuration Examples

**Regex Pattern (Part Number Format)**:
```json
{
  "pattern": "^[A-Z]{2}-\\d{4}$"
}
```

**Numeric Range (File Size)**:
```json
{
  "min": 0,
  "max": 104857600
}
```

**String Length**:
```json
{
  "min_length": 5,
  "max_length": 255
}
```

**File Type Validation**:
```json
{
  "allowed_types": ["STEP", "STL", "IGES", "OBJ"]
}
```

**File Size Limit**:
```json
{
  "max_size_mb": 100
}
```

**Custom Expression**:
```json
{
  "expression": "value > 0 and value < 100"
}
```

### Viewing Validation Results

**From Design Detail**:
1. Go to any design: `/designs/{id}`
2. Click "Validation" tab
3. View all validation results

**From Rule Detail**:
1. Go to `/validation`
2. Click "View" on any rule
3. See statistics and recent results

## Backend Integration

### Models
- `ValidationRule`: Defines validation rules
- `ValidationResult`: Stores validation outcomes

### API Endpoints
- `GET /validation-rules/`: List all rules
- `POST /validation-rules/`: Create new rule
- `GET /validation-rules/{id}/`: Get rule details
- `PUT/PATCH /validation-rules/{id}/`: Update rule
- `DELETE /validation-rules/{id}/`: Delete rule
- `POST /validation-rules/{id}/activate/`: Activate rule
- `POST /validation-rules/{id}/deactivate/`: Deactivate rule
- `GET /validation-rules/{id}/statistics/`: Get rule statistics
- `GET /validation-results/`: List validation results (filterable)

### Filters
- `is_active`: true/false
- `severity`: INFO/WARNING/ERROR/CRITICAL
- `target_model`: DesignAsset/DesignSeries/etc
- `rule_type`: REGEX/RANGE/etc
- `status`: PASSED/FAILED/SKIPPED/ERROR (for results)
- `target_id`: Filter results by specific record

## UI Components

### Rule Card
Displays:
- Rule name with severity badge
- Active/Inactive status
- Description
- Rule type and target
- Statistics (checks, failures)
- Action buttons

### Statistics Dashboard
Shows:
- Total checks
- Total failures
- Failure rate
- Recent pass rate

### Results Table
Columns:
- Status indicator
- Rule name
- Target field
- Error message
- Validation timestamp

## Security

- Rules require authentication
- Edit/delete restricted by permissions
- Validation results tracked by user
- Audit trail for all operations

## Future Enhancements

- [ ] Bulk rule operations
- [ ] Rule templates/presets
- [ ] Visual rule builder (no JSON)
- [ ] Scheduled validation runs
- [ ] Validation reports/exports
- [ ] Rule testing/dry-run mode
- [ ] Dependency between rules
- [ ] Rule groups/categories
- [ ] Email notifications on failures
- [ ] Dashboard widget for critical failures

---

**Created**: December 17, 2025  
**Version**: 1.0.0  
**Status**: Production Ready ✅
