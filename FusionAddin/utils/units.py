"""Unit conversion utilities for Fusion 360 API.

Fusion 360 internally uses centimeters (cm) for all linear dimensions.
This module provides conversion functions to/from millimeters (mm)
for the external MCP API which exposes all dimensions in mm.

Conversion factors:
    - Linear (length, position): 1 cm = 10 mm
    - Area: 1 cm² = 100 mm²
    - Volume: 1 cm³ = 1000 mm³
"""

from typing import Set


# Length unit strings that require conversion (case-insensitive)
LENGTH_UNITS: Set[str] = {'mm', 'cm', 'm', 'in', 'ft'}


def cm_to_mm(value: float) -> float:
    """Convert centimeters to millimeters.

    Args:
        value: Value in centimeters

    Returns:
        Value in millimeters, rounded to 6 decimal places
    """
    return round(value * 10.0, 6)


def mm_to_cm(value: float) -> float:
    """Convert millimeters to centimeters.

    Args:
        value: Value in millimeters

    Returns:
        Value in centimeters
    """
    return value / 10.0


def cm2_to_mm2(value: float) -> float:
    """Convert square centimeters to square millimeters.

    Args:
        value: Value in cm²

    Returns:
        Value in mm², rounded to 6 decimal places
    """
    return round(value * 100.0, 6)


def cm3_to_mm3(value: float) -> float:
    """Convert cubic centimeters to cubic millimeters.

    Args:
        value: Value in cm³

    Returns:
        Value in mm³, rounded to 6 decimal places
    """
    return round(value * 1000.0, 6)


def is_length_unit(unit: str) -> bool:
    """Check if a unit string represents a length unit.

    Length units require conversion from cm to mm.
    Angular units (deg, rad) do NOT require conversion.

    Args:
        unit: Unit string from Fusion 360 parameter (e.g., 'mm', 'cm', 'deg')

    Returns:
        True if unit is a length unit, False otherwise
    """
    if not unit:
        return False
    return unit.lower() in LENGTH_UNITS
