# Unit Conversion System

This document describes the unit conversion system in Enginel, which ensures consistent measurement units across all CAD files.

## Overview

CAD files from different sources may use different units (inches, millimeters, centimeters, etc.). The unit conversion system:

1. **Auto-detects** units from filenames (e.g., `bracket_inches.step` → inches)
2. **Normalizes** all measurements to millimeters (BASE_UNIT) for consistent comparisons
3. **Preserves** original units and conversion history in metadata
4. **Provides** API endpoints for unit queries and conversion calculations
5. **Supports** 10+ unit types (metric and imperial)

This prevents unit confusion errors and enables accurate comparisons between designs.

## Supported Units

| Unit | Symbol | Type | Conversion to mm |
|------|--------|------|------------------|
| Millimeter | mm | Metric | 1.0 |
| Centimeter | cm | Metric | 10.0 |
| Meter | m | Metric | 1000.0 |
| Kilometer | km | Metric | 1000000.0 |
| Micrometer | um | Metric | 0.001 |
| Nanometer | nm | Metric | 0.000001 |
| Inch | in | Imperial | 25.4 |
| Foot | ft | Imperial | 304.8 |
| Yard | yd | Imperial | 914.4 |
| Mile | mi | Imperial | 1609344.0 |

## Architecture

### Module: `unit_converter.py`

Core conversion utilities:

```python
from designs.unit_converter import (
    convert_length,      # Convert length values
    convert_area,        # Convert area values (unit²)
    convert_volume,      # Convert volume values (unit³)
    detect_unit_from_filename,  # Auto-detect from filename
    get_scale_factor,    # Get conversion factor
    validate_unit,       # Check if unit is valid
    format_dimension,    # Format value with unit
)
```

### Celery Task: `normalize_units`

Automatically normalizes measurements during file processing:

```python
# In tasks.py
@shared_task
def normalize_units(design_asset_id, unit_override=None):
    """
    Normalize physical units to standard (millimeters).
    
    Args:
        design_asset_id: UUID of the DesignAsset
        unit_override: Optional unit to use instead of auto-detection
    
    Returns:
        dict: Unit conversion results
    """
```

## Auto-Detection

The system detects units from filenames using common patterns:

```python
# Filename → Detected Unit
"bracket_inches.step"     → "in"
"housing_mm.iges"         → "mm"
"shaft_in.step"           → "in"
"plate_centimeters.step"  → "cm"
"assembly_metric.step"    → "mm" (default)
"part.step"               → "mm" (fallback)
```

Detection patterns:
- `_inches`, `_in`, `-in` → inches
- `_mm`, `-mm` → millimeters
- `_cm`, `-cm` → centimeters
- `_metric` → millimeters
- `_imperial` → inches
- No match → millimeters (default)

## API Endpoints

### 1. Convert Units

Convert a value between different units:

```http
GET /api/designs/convert-units/?value=10&from=in&to=mm&type=length
Authorization: Bearer <token>
```

**Parameters:**
- `value`: Numeric value to convert
- `from`: Source unit (e.g., "in", "mm", "cm")
- `to`: Target unit
- `type`: Conversion type (`length`, `area`, `volume`)

**Response:**
```json
{
    "original_value": 10,
    "original_unit": "in",
    "converted_value": 254.0,
    "converted_unit": "mm",
    "conversion_type": "length"
}
```

**Examples:**

```bash
# Length: 1 inch to mm
curl "http://localhost:8000/api/designs/convert-units/?value=1&from=in&to=mm&type=length" \
  -H "Authorization: Bearer $TOKEN"
# Response: {"converted_value": 25.4, ...}

# Area: 1 square inch to square mm
curl "http://localhost:8000/api/designs/convert-units/?value=1&from=in&to=mm&type=area" \
  -H "Authorization: Bearer $TOKEN"
# Response: {"converted_value": 645.16, ...}

# Volume: 1 cubic inch to cubic mm
curl "http://localhost:8000/api/designs/convert-units/?value=1&from=in&to=mm&type=volume" \
  -H "Authorization: Bearer $TOKEN"
# Response: {"converted_value": 16387.064, ...}
```

### 2. Normalize Units (Manual Trigger)

Manually trigger unit normalization for a design asset:

```http
POST /api/designs/{id}/normalize_units/
Authorization: Bearer <token>
Content-Type: application/json

{
    "unit": "in"  // Optional: override auto-detection
}
```

**Response:**
```json
{
    "message": "Unit normalization queued for bracket.step",
    "design_asset_id": "550e8400-e29b-41d4-a716-446655440000",
    "task_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "unit_override": "in"
}
```

## Processing Workflow

When a CAD file is uploaded, the system automatically:

1. **Upload** → Create `DesignAsset` record
2. **Process** → Extract geometry metadata (volume, area, bbox, mass)
3. **Normalize** → Detect original unit, convert to mm
4. **Store** → Save converted values + conversion history

```python
# In process_design_asset task
def process_design_asset(design_asset_id):
    # ... extract geometry ...
    
    # Step 5: Normalize units
    unit_result = normalize_units.delay(design_asset_id).get(timeout=30)
    logger.info(f"Unit normalization: {unit_result['original_unit']} → {unit_result['target_unit']}")
```

## Metadata Structure

After normalization, `DesignAsset.metadata` contains:

```json
{
    "volume": 16387.064,           // Original value in original unit
    "volume_mm3": 16387.064,       // Converted to mm³
    "surface_area": 645.16,        // Original in original unit
    "surface_area_mm2": 645.16,    // Converted to mm²
    "bounding_box": [25.4, 25.4, 25.4],  // Converted to mm
    "center_of_mass": [12.7, 12.7, 12.7], // Converted to mm
    "unit_conversion": {
        "original_unit": "in",
        "target_unit": "mm",
        "conversion_factor": 25.4,
        "timestamp": "2025-01-15T10:30:00Z",
        "conversions": {
            "volume": {"original": 1.0, "converted": 16387.064, "unit": "mm³"},
            "surface_area": {"original": 6.0, "converted": 3870.96, "unit": "mm²"},
            "bounding_box": {
                "original": [1.0, 1.0, 1.0],
                "converted": [25.4, 25.4, 25.4],
                "unit": "mm"
            }
        }
    }
}
```

## Code Examples

### Convert Individual Values

```python
from designs.unit_converter import convert_length, convert_area, convert_volume

# Length conversion
length_mm = convert_length(10, 'in', 'mm')  # 254.0 mm

# Area conversion
area_mm2 = convert_area(1, 'in', 'mm')  # 645.16 mm²

# Volume conversion
volume_mm3 = convert_volume(1, 'in', 'mm')  # 16387.064 mm³

# Metric to metric
length_cm = convert_length(100, 'mm', 'cm')  # 10.0 cm
```

### Auto-Detect Unit

```python
from designs.unit_converter import detect_unit_from_filename

unit = detect_unit_from_filename('bracket_inches.step')  # "in"
unit = detect_unit_from_filename('plate_mm.iges')        # "mm"
unit = detect_unit_from_filename('housing.step')          # "mm" (default)
```

### Get Scale Factor

```python
from designs.unit_converter import get_scale_factor

factor = get_scale_factor('in', 'mm')  # 25.4
factor = get_scale_factor('cm', 'mm')  # 10.0
factor = get_scale_factor('mm', 'mm')  # 1.0
```

### Format Dimensions

```python
from designs.unit_converter import format_dimension

formatted = format_dimension(25.4, 'mm')      # "25.4 mm"
formatted = format_dimension(1000, 'mm', 2)   # "1000.00 mm"
formatted = format_dimension(0.001, 'mm', 6)  # "0.001000 mm"
```

## Testing

Run the unit conversion test suite:

```bash
cd test_files
python test_units.py
```

Tests include:
1. ✅ API conversion endpoint (inches → mm)
2. ✅ Area conversion (in² → mm²)
3. ✅ Volume conversion (in³ → mm³)
4. ✅ Metric to metric (cm → mm)
5. ✅ Invalid unit handling
6. ✅ Manual normalization trigger

**Expected Output:**

```
============================================================
UNIT CONVERSION TEST SUITE
============================================================
✅ Logged in successfully

============================================================
TEST: Unit Conversion API
============================================================

1. Convert 1 inch to mm:
   1 in = 25.4 mm
   Expected: 25.4 mm, Got: 25.4 mm
   ✅ PASS

2. Convert 1 in² to mm²:
   1 in² = 645.16 mm²
   Expected: 645.16 mm², Got: 645.16 mm²
   ✅ PASS

3. Convert 1 in³ to mm³:
   1 in³ = 16387.064 mm³
   Expected: 16387.064 mm³, Got: 16387.064 mm³
   ✅ PASS

4. Convert 10 cm to mm:
   10 cm = 100 mm
   Expected: 100 mm, Got: 100 mm
   ✅ PASS

5. Test invalid unit (should return error):
   ✅ PASS - Correctly rejected invalid unit: Invalid unit: invalid
```

## Common Unit Conversions

| From | To | Multiply By |
|------|----|----|
| in → mm | 25.4 |
| mm → in | 0.03937 |
| cm → mm | 10.0 |
| mm → cm | 0.1 |
| m → mm | 1000.0 |
| mm → m | 0.001 |
| ft → mm | 304.8 |
| mm → ft | 0.003281 |

### Area (squared)
| From | To | Multiply By |
|------|----|----|
| in² → mm² | 645.16 |
| mm² → in² | 0.00155 |
| cm² → mm² | 100.0 |

### Volume (cubed)
| From | To | Multiply By |
|------|----|----|
| in³ → mm³ | 16387.064 |
| mm³ → in³ | 0.000061 |
| cm³ → mm³ | 1000.0 |

## Error Handling

The system gracefully handles:

1. **Invalid units**: Returns 400 error with descriptive message
2. **Missing units**: Falls back to mm (BASE_UNIT)
3. **Same unit conversion**: Returns original value (no conversion)
4. **Non-numeric values**: Returns 400 error

```python
# Invalid unit
try:
    convert_length(10, 'invalid', 'mm')
except ValueError as e:
    print(e)  # "Invalid unit: invalid"

# Same unit (no-op)
result = convert_length(10, 'mm', 'mm')  # Returns 10.0
```

## Integration Points

Unit conversion integrates with:

1. **File Upload**: Auto-normalizes after geometry extraction
2. **BOM Extraction**: Ensures consistent units in assembly trees
3. **API Endpoints**: Provides on-demand conversions
4. **Design Comparison**: Enables accurate cross-design comparisons

## Future Enhancements

- [ ] Support for custom units (e.g., `mil`, `thou`)
- [ ] Mass/density conversions (kg, lb, g/cm³)
- [ ] Temperature units (°C, °F, K)
- [ ] Angle units (degrees, radians)
- [ ] Unit preferences per user/organization
- [ ] Bulk conversion of existing designs

## References

- `designs/unit_converter.py`: Core conversion utilities (350 lines)
- `designs/tasks.py`: `normalize_units()` Celery task (110 lines)
- `designs/views.py`: API endpoints (normalize_units, convert_units)
- `test_files/test_units.py`: Test suite (180 lines)

## Revision History

- **v1.0** (2025-01-15): Initial implementation
  - 10 supported units (6 metric, 4 imperial)
  - Auto-detection from filename
  - API endpoints for conversion queries
  - Automatic normalization during file processing
