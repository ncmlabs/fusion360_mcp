"""Sketch models for Fusion 360 MCP Server.

Defines 2D sketch entities and constraints.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from .geometry import Point3D, Vector3D, PlaneSpec


class SketchCurveType(str, Enum):
    """Types of sketch curves."""
    LINE = "line"
    CIRCLE = "circle"
    ARC = "arc"
    ELLIPSE = "ellipse"
    SPLINE = "spline"
    FITTED_SPLINE = "fitted_spline"
    CONIC = "conic"


class ConstraintType(str, Enum):
    """Types of sketch constraints."""
    COINCIDENT = "coincident"
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    PERPENDICULAR = "perpendicular"
    PARALLEL = "parallel"
    TANGENT = "tangent"
    EQUAL = "equal"
    CONCENTRIC = "concentric"
    MIDPOINT = "midpoint"
    FIX = "fix"
    COLLINEAR = "collinear"
    SYMMETRIC = "symmetric"


class DimensionType(str, Enum):
    """Types of sketch dimensions."""
    DISTANCE = "distance"
    DIAMETER = "diameter"
    RADIUS = "radius"
    ANGLE = "angle"
    OFFSET = "offset"


class SketchPoint(BaseModel):
    """A point in a sketch."""

    id: str = Field(description="Unique point identifier")
    position: Point3D = Field(description="Point position (z typically 0 in sketch plane)")
    is_construction: bool = Field(default=False, description="Whether point is construction geometry")
    is_fixed: bool = Field(default=False, description="Whether point is fully constrained")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "point_001",
                "position": {"x": 0, "y": 0, "z": 0},
                "is_construction": False,
                "is_fixed": False
            }
        }
    }


class SketchCurve(BaseModel):
    """A curve in a sketch."""

    id: str = Field(description="Unique curve identifier")
    curve_type: SketchCurveType = Field(description="Type of curve")
    is_construction: bool = Field(default=False, description="Whether curve is construction geometry")
    is_fixed: bool = Field(default=False, description="Whether curve is fully constrained")
    length: float = Field(default=0.0, description="Curve length in mm")

    # Common endpoints
    start_point: Optional[Point3D] = Field(default=None, description="Start point")
    end_point: Optional[Point3D] = Field(default=None, description="End point")

    # Circle/Arc specific
    center: Optional[Point3D] = Field(default=None, description="Center for circles/arcs")
    radius: Optional[float] = Field(default=None, description="Radius for circles/arcs")
    start_angle: Optional[float] = Field(default=None, description="Start angle for arcs (radians)")
    end_angle: Optional[float] = Field(default=None, description="End angle for arcs (radians)")

    # Ellipse specific
    major_axis_length: Optional[float] = Field(default=None, description="Major axis length for ellipses")
    minor_axis_length: Optional[float] = Field(default=None, description="Minor axis length for ellipses")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "curve_001",
                "curve_type": "line",
                "is_construction": False,
                "is_fixed": False,
                "length": 100.0,
                "start_point": {"x": 0, "y": 0, "z": 0},
                "end_point": {"x": 100, "y": 0, "z": 0}
            }
        }
    }


class SketchConstraint(BaseModel):
    """A geometric constraint in a sketch."""

    id: str = Field(description="Unique constraint identifier")
    constraint_type: ConstraintType = Field(description="Type of constraint")
    entity_ids: List[str] = Field(description="IDs of constrained entities")
    is_driven: bool = Field(default=False, description="Whether constraint is driven (reference)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "constraint_001",
                "constraint_type": "horizontal",
                "entity_ids": ["curve_001"],
                "is_driven": False
            }
        }
    }


class SketchDimension(BaseModel):
    """A dimension constraint in a sketch."""

    id: str = Field(description="Unique dimension identifier")
    dimension_type: DimensionType = Field(description="Type of dimension")
    value: float = Field(description="Dimension value in mm or degrees")
    expression: Optional[str] = Field(default=None, description="Parameter expression")
    entity_ids: List[str] = Field(description="IDs of dimensioned entities")
    is_driven: bool = Field(default=False, description="Whether dimension is driven (reference)")
    parameter_name: Optional[str] = Field(default=None, description="Associated parameter name")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "dim_001",
                "dimension_type": "distance",
                "value": 100.0,
                "expression": "100 mm",
                "entity_ids": ["curve_001"],
                "is_driven": False,
                "parameter_name": "d1"
            }
        }
    }


class Profile(BaseModel):
    """A closed profile in a sketch (can be extruded)."""

    id: str = Field(description="Unique profile identifier")
    index: int = Field(description="Profile index in sketch")
    area: float = Field(description="Profile area in mm^2")
    curve_ids: List[str] = Field(description="IDs of curves forming the profile boundary")
    is_outer: bool = Field(default=True, description="Whether this is an outer boundary")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "profile_001",
                "index": 0,
                "area": 5000.0,
                "curve_ids": ["curve_001", "curve_002", "curve_003", "curve_004"],
                "is_outer": True
            }
        }
    }


class Sketch(BaseModel):
    """A 2D sketch in the design."""

    id: str = Field(description="Unique sketch identifier")
    name: str = Field(description="Sketch display name")

    # Sketch plane
    plane: PlaneSpec = Field(description="Plane the sketch is on")
    origin: Point3D = Field(default_factory=lambda: Point3D(), description="Sketch origin in 3D space")
    x_direction: Vector3D = Field(default_factory=lambda: Vector3D(x=1, y=0, z=0))
    y_direction: Vector3D = Field(default_factory=lambda: Vector3D(x=0, y=1, z=0))

    # Constraint status
    is_fully_constrained: bool = Field(default=False, description="Whether sketch is fully constrained")
    is_valid: bool = Field(default=True, description="Whether sketch is valid")

    # Content counts
    curves_count: int = Field(default=0, description="Number of curves")
    points_count: int = Field(default=0, description="Number of points")
    profiles_count: int = Field(default=0, description="Number of closed profiles")
    constraints_count: int = Field(default=0, description="Number of constraints")
    dimensions_count: int = Field(default=0, description="Number of dimensions")

    # Detailed content (optional, loaded on demand)
    curves: Optional[List[SketchCurve]] = Field(default=None, description="Sketch curves")
    points: Optional[List[SketchPoint]] = Field(default=None, description="Sketch points")
    profiles: Optional[List[Profile]] = Field(default=None, description="Closed profiles")
    constraints: Optional[List[SketchConstraint]] = Field(default=None, description="Constraints")
    dimensions: Optional[List[SketchDimension]] = Field(default=None, description="Dimensions")

    # Parent reference
    component_id: Optional[str] = Field(default=None, description="Parent component ID")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "sketch_001",
                "name": "Sketch1",
                "plane": {"plane_type": "XY", "offset": 0},
                "origin": {"x": 0, "y": 0, "z": 0},
                "is_fully_constrained": True,
                "curves_count": 4,
                "profiles_count": 1
            }
        }
    }


class SketchSummary(BaseModel):
    """Lightweight sketch summary for list operations."""

    id: str = Field(description="Unique sketch identifier")
    name: str = Field(description="Sketch display name")
    plane: PlaneSpec = Field(description="Plane the sketch is on")
    is_fully_constrained: bool = Field(default=False, description="Whether fully constrained")
    profiles_count: int = Field(default=0, description="Number of closed profiles")
    curves_count: int = Field(default=0, description="Number of curves")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "sketch_001",
                "name": "Sketch1",
                "plane": {"plane_type": "XY", "offset": 0},
                "is_fully_constrained": True,
                "profiles_count": 1,
                "curves_count": 4
            }
        }
    }
