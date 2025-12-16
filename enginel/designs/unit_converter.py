"""
Unit conversion utilities for Enginel.

Handles conversion between different length units commonly used in CAD files.
All internal calculations use millimeters (mm) as the base unit.
"""

from typing import Dict, Union, Tuple
from decimal import Decimal


# Base unit: millimeters (mm)
BASE_UNIT = 'mm'

# Conversion factors to millimeters
UNIT_CONVERSIONS: Dict[str, float] = {
    # Metric
    'mm': 1.0,                    # millimeters (base)
    'cm': 10.0,                   # centimeters
    'm': 1000.0,                  # meters
    'km': 1_000_000.0,            # kilometers
    'um': 0.001,                  # micrometers (microns)
    'nm': 0.000001,               # nanometers
    
    # Imperial
    'in': 25.4,                   # inches
    'ft': 304.8,                  # feet
    'yd': 914.4,                  # yards
    'mi': 1_609_344.0,            # miles
}

# Display names for units
UNIT_NAMES: Dict[str, str] = {
    'mm': 'Millimeters',
    'cm': 'Centimeters',
    'm': 'Meters',
    'km': 'Kilometers',
    'um': 'Micrometers (µm)',
    'nm': 'Nanometers',
    'in': 'Inches',
    'ft': 'Feet',
    'yd': 'Yards',
    'mi': 'Miles',
}

# Common CAD file unit defaults
CAD_FORMAT_DEFAULTS: Dict[str, str] = {
    'STEP': 'mm',
    'STP': 'mm',
    'IGES': 'mm',
    'IGS': 'mm',
    'STL': 'mm',
    'OBJ': 'm',
    'FBX': 'cm',
}


def convert_length(value: Union[float, Decimal], from_unit: str, to_unit: str) -> float:
    """
    Convert a length value from one unit to another.
    
    Args:
        value: The numeric value to convert
        from_unit: Source unit (e.g., 'in', 'mm', 'm')
        to_unit: Target unit (e.g., 'in', 'mm', 'm')
    
    Returns:
        Converted value in target unit
    
    Raises:
        ValueError: If unit is not supported
    
    Example:
        >>> convert_length(1.0, 'in', 'mm')
        25.4
        >>> convert_length(1000.0, 'mm', 'm')
        1.0
    """
    if from_unit not in UNIT_CONVERSIONS:
        raise ValueError(f"Unsupported source unit: {from_unit}")
    if to_unit not in UNIT_CONVERSIONS:
        raise ValueError(f"Unsupported target unit: {to_unit}")
    
    # Convert to base unit (mm), then to target unit
    value_in_mm = float(value) * UNIT_CONVERSIONS[from_unit]
    result = value_in_mm / UNIT_CONVERSIONS[to_unit]
    
    return result


def convert_area(value: Union[float, Decimal], from_unit: str, to_unit: str) -> float:
    """
    Convert an area value from one unit to another.
    
    Area conversion uses squared conversion factors.
    
    Args:
        value: The numeric area value to convert
        from_unit: Source unit (e.g., 'in', 'mm', 'm')
        to_unit: Target unit (e.g., 'in', 'mm', 'm')
    
    Returns:
        Converted area in target unit squared
    
    Example:
        >>> convert_area(1.0, 'in', 'mm')  # 1 in² = 645.16 mm²
        645.16
    """
    if from_unit not in UNIT_CONVERSIONS:
        raise ValueError(f"Unsupported source unit: {from_unit}")
    if to_unit not in UNIT_CONVERSIONS:
        raise ValueError(f"Unsupported target unit: {to_unit}")
    
    # Square the linear conversion factors
    from_factor = UNIT_CONVERSIONS[from_unit] ** 2
    to_factor = UNIT_CONVERSIONS[to_unit] ** 2
    
    value_in_mm2 = float(value) * from_factor
    result = value_in_mm2 / to_factor
    
    return result


def convert_volume(value: Union[float, Decimal], from_unit: str, to_unit: str) -> float:
    """
    Convert a volume value from one unit to another.
    
    Volume conversion uses cubed conversion factors.
    
    Args:
        value: The numeric volume value to convert
        from_unit: Source unit (e.g., 'in', 'mm', 'm')
        to_unit: Target unit (e.g., 'in', 'mm', 'm')
    
    Returns:
        Converted volume in target unit cubed
    
    Example:
        >>> convert_volume(1.0, 'in', 'mm')  # 1 in³ = 16387.064 mm³
        16387.064
    """
    if from_unit not in UNIT_CONVERSIONS:
        raise ValueError(f"Unsupported source unit: {from_unit}")
    if to_unit not in UNIT_CONVERSIONS:
        raise ValueError(f"Unsupported target unit: {to_unit}")
    
    # Cube the linear conversion factors
    from_factor = UNIT_CONVERSIONS[from_unit] ** 3
    to_factor = UNIT_CONVERSIONS[to_unit] ** 3
    
    value_in_mm3 = float(value) * from_factor
    result = value_in_mm3 / to_factor
    
    return result


def convert_mass(value: Union[float, Decimal], from_unit: str, to_unit: str) -> float:
    """
    Convert a mass value between units.
    
    Args:
        value: The numeric mass value
        from_unit: Source unit ('kg', 'g', 'mg', 'lb', 'oz')
        to_unit: Target unit
    
    Returns:
        Converted mass
    
    Example:
        >>> convert_mass(1.0, 'lb', 'kg')
        0.453592
    """
    mass_conversions = {
        'kg': 1.0,          # kilograms (base)
        'g': 0.001,         # grams
        'mg': 0.000001,     # milligrams
        'lb': 0.453592,     # pounds
        'oz': 0.0283495,    # ounces
    }
    
    if from_unit not in mass_conversions:
        raise ValueError(f"Unsupported source mass unit: {from_unit}")
    if to_unit not in mass_conversions:
        raise ValueError(f"Unsupported target mass unit: {to_unit}")
    
    value_in_kg = float(value) * mass_conversions[from_unit]
    result = value_in_kg / mass_conversions[to_unit]
    
    return result


def normalize_to_base(value: Union[float, Decimal], unit: str, measurement_type: str = 'length') -> float:
    """
    Normalize a value to base units (mm for length, mm² for area, mm³ for volume, kg for mass).
    
    Args:
        value: Value to normalize
        unit: Current unit
        measurement_type: Type of measurement ('length', 'area', 'volume', 'mass')
    
    Returns:
        Value in base units
    """
    if measurement_type == 'length':
        return convert_length(value, unit, BASE_UNIT)
    elif measurement_type == 'area':
        return convert_area(value, unit, BASE_UNIT)
    elif measurement_type == 'volume':
        return convert_volume(value, unit, BASE_UNIT)
    elif measurement_type == 'mass':
        return convert_mass(value, unit, 'kg')
    else:
        raise ValueError(f"Unsupported measurement type: {measurement_type}")


def get_scale_factor(from_unit: str, to_unit: str) -> float:
    """
    Get the scale factor for converting from one unit to another.
    
    Useful for geometry transformations.
    
    Args:
        from_unit: Source unit
        to_unit: Target unit
    
    Returns:
        Scale factor (multiply source values by this)
    
    Example:
        >>> get_scale_factor('in', 'mm')
        25.4
    """
    return convert_length(1.0, from_unit, to_unit)


def detect_unit_from_filename(filename: str) -> str:
    """
    Attempt to detect unit from filename or file extension.
    
    Args:
        filename: Name of the CAD file
    
    Returns:
        Detected unit or default 'mm'
    
    Example:
        >>> detect_unit_from_filename('part_inches.step')
        'in'
        >>> detect_unit_from_filename('assembly.step')
        'mm'
    """
    filename_lower = filename.lower()
    
    # Check for unit hints in filename
    unit_hints = {
        'inch': 'in',
        'inches': 'in',
        'imperial': 'in',
        'metric': 'mm',
        'millimeter': 'mm',
        'centimeter': 'cm',
        'meter': 'm',
    }
    
    for hint, unit in unit_hints.items():
        if hint in filename_lower:
            return unit
    
    # Check file extension for default
    for ext, default_unit in CAD_FORMAT_DEFAULTS.items():
        if filename_lower.endswith(f'.{ext.lower()}'):
            return default_unit
    
    return BASE_UNIT


def format_dimension(value: float, unit: str, precision: int = 3) -> str:
    """
    Format a dimension value with unit for display.
    
    Args:
        value: Numeric value
        unit: Unit string
        precision: Decimal places
    
    Returns:
        Formatted string (e.g., "25.400 mm")
    """
    unit_name = UNIT_NAMES.get(unit, unit)
    return f"{value:.{precision}f} {unit}"


def get_conversion_matrix() -> Dict[Tuple[str, str], float]:
    """
    Generate a conversion matrix for all supported unit pairs.
    
    Returns:
        Dictionary with (from_unit, to_unit) keys and conversion factor values
    """
    matrix = {}
    units = list(UNIT_CONVERSIONS.keys())
    
    for from_unit in units:
        for to_unit in units:
            matrix[(from_unit, to_unit)] = get_scale_factor(from_unit, to_unit)
    
    return matrix


def validate_unit(unit: str) -> bool:
    """
    Check if a unit string is supported.
    
    Args:
        unit: Unit string to validate
    
    Returns:
        True if supported, False otherwise
    """
    return unit in UNIT_CONVERSIONS


def get_supported_units() -> list:
    """
    Get list of all supported units.
    
    Returns:
        List of unit strings
    """
    return list(UNIT_CONVERSIONS.keys())
