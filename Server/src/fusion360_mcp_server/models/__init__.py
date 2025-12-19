"""Pydantic models for Fusion 360 MCP Server."""

from .geometry import (
    Point3D,
    Vector3D,
    BoundingBox,
    Matrix3D,
    PlaneSpec,
)
from .body import (
    EntityType,
    FaceType,
    EdgeType,
    Vertex,
    Edge,
    Face,
    Body,
    BodySummary,
)
from .sketch import (
    SketchCurveType,
    ConstraintType,
    DimensionType,
    SketchPoint,
    SketchCurve,
    SketchConstraint,
    SketchDimension,
    Profile,
    Sketch,
    SketchSummary,
)
from .feature import (
    FeatureType,
    FeatureOperation,
    ExtentType,
    Parameter,
    FeatureInput,
    FeatureOutput,
    Feature,
    TimelineEntry,
    Timeline,
)
from .design_state import (
    UnitsType,
    JointType,
    Component,
    Occurrence,
    Joint,
    DesignInfo,
    DesignState,
)

__all__ = [
    # Geometry
    "Point3D", "Vector3D", "BoundingBox", "Matrix3D", "PlaneSpec",
    # Body
    "EntityType", "FaceType", "EdgeType", "Vertex", "Edge", "Face", "Body", "BodySummary",
    # Sketch
    "SketchCurveType", "ConstraintType", "DimensionType",
    "SketchPoint", "SketchCurve", "SketchConstraint", "SketchDimension",
    "Profile", "Sketch", "SketchSummary",
    # Feature
    "FeatureType", "FeatureOperation", "ExtentType",
    "Parameter", "FeatureInput", "FeatureOutput", "Feature", "TimelineEntry", "Timeline",
    # Design State
    "UnitsType", "JointType", "Component", "Occurrence", "Joint", "DesignInfo", "DesignState",
]
