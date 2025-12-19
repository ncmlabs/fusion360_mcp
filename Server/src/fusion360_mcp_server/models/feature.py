"""Feature models for Fusion 360 MCP Server.

Defines feature types, parameters, and timeline entries.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum


class FeatureType(str, Enum):
    """Types of features in timeline."""
    SKETCH = "sketch"
    EXTRUDE = "extrude"
    REVOLVE = "revolve"
    SWEEP = "sweep"
    LOFT = "loft"
    HOLE = "hole"
    FILLET = "fillet"
    CHAMFER = "chamfer"
    SHELL = "shell"
    COMBINE = "combine"
    SPLIT = "split"
    MOVE = "move"
    PATTERN_RECTANGULAR = "rectangular_pattern"
    PATTERN_CIRCULAR = "circular_pattern"
    THREAD = "thread"
    COMPONENT = "component"
    JOINT = "joint"
    MIRROR = "mirror"
    OFFSET = "offset"
    RIB = "rib"
    WEB = "web"
    OTHER = "other"


class FeatureOperation(str, Enum):
    """Boolean operation types for features."""
    NEW_BODY = "new_body"
    JOIN = "join"
    CUT = "cut"
    INTERSECT = "intersect"
    NEW_COMPONENT = "new_component"


class ExtentType(str, Enum):
    """Types of feature extents."""
    DISTANCE = "distance"
    SYMMETRIC = "symmetric"
    TO_OBJECT = "to_object"
    ALL = "all"
    THROUGH_ALL = "through_all"


class Parameter(BaseModel):
    """A design parameter."""

    name: str = Field(description="Parameter name")
    expression: str = Field(description="Parameter expression (e.g., '100 mm' or 'width * 2')")
    value: float = Field(description="Evaluated numeric value")
    unit: str = Field(default="mm", description="Unit of measure")
    is_user_parameter: bool = Field(default=False, description="Whether user-defined parameter")
    comment: Optional[str] = Field(default=None, description="Parameter comment")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "plate_width",
                "expression": "100 mm",
                "value": 100.0,
                "unit": "mm",
                "is_user_parameter": True
            }
        }
    }


class FeatureInput(BaseModel):
    """Input references for a feature."""

    profiles: Optional[List[str]] = Field(default=None, description="Profile IDs used")
    bodies: Optional[List[str]] = Field(default=None, description="Body IDs used")
    faces: Optional[List[str]] = Field(default=None, description="Face IDs used")
    edges: Optional[List[str]] = Field(default=None, description="Edge IDs used")
    sketches: Optional[List[str]] = Field(default=None, description="Sketch IDs used")

    model_config = {
        "json_schema_extra": {
            "example": {
                "profiles": ["profile_001"],
                "sketches": ["sketch_001"]
            }
        }
    }


class FeatureOutput(BaseModel):
    """Output references from a feature."""

    bodies: List[str] = Field(default_factory=list, description="Created/modified body IDs")
    faces: List[str] = Field(default_factory=list, description="Created face IDs")
    edges: List[str] = Field(default_factory=list, description="Created edge IDs")

    model_config = {
        "json_schema_extra": {
            "example": {
                "bodies": ["body_001"],
                "faces": ["face_001", "face_002"],
                "edges": ["edge_001"]
            }
        }
    }


class Feature(BaseModel):
    """A feature in the design timeline."""

    id: str = Field(description="Unique feature identifier")
    name: str = Field(description="Feature display name")
    feature_type: FeatureType = Field(description="Type of feature")

    # Feature state
    is_suppressed: bool = Field(default=False, description="Whether feature is suppressed")
    is_healthy: bool = Field(default=True, description="Whether feature computed successfully")
    error_message: Optional[str] = Field(default=None, description="Error if not healthy")

    # Timeline position
    timeline_index: int = Field(description="Position in timeline")

    # Operation (for body-creating features)
    operation: Optional[FeatureOperation] = Field(default=None, description="Boolean operation")

    # Parameters
    parameters: Dict[str, Parameter] = Field(
        default_factory=dict,
        description="Feature parameters by name"
    )

    # References
    inputs: Optional[FeatureInput] = Field(default=None, description="Input references")
    outputs: Optional[FeatureOutput] = Field(default=None, description="Output references")

    # Parent reference
    component_id: Optional[str] = Field(default=None, description="Parent component ID")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "Extrude1",
                "name": "Extrude1",
                "feature_type": "extrude",
                "is_suppressed": False,
                "is_healthy": True,
                "timeline_index": 1,
                "operation": "new_body",
                "parameters": {
                    "distance": {
                        "name": "distance",
                        "expression": "10 mm",
                        "value": 10.0,
                        "unit": "mm",
                        "is_user_parameter": False
                    }
                }
            }
        }
    }


class TimelineEntry(BaseModel):
    """An entry in the design timeline."""

    index: int = Field(description="Timeline position (0-based)")
    feature_id: str = Field(description="Feature ID")
    name: str = Field(description="Feature name")
    feature_type: FeatureType = Field(description="Type of feature")
    is_suppressed: bool = Field(default=False, description="Whether suppressed")
    is_group: bool = Field(default=False, description="Whether this is a group")
    is_rolled_back: bool = Field(default=False, description="Whether timeline is rolled back past this")

    model_config = {
        "json_schema_extra": {
            "example": {
                "index": 0,
                "feature_id": "Sketch1",
                "name": "Sketch1",
                "feature_type": "sketch",
                "is_suppressed": False,
                "is_group": False,
                "is_rolled_back": False
            }
        }
    }


class Timeline(BaseModel):
    """The complete design timeline."""

    entries: List[TimelineEntry] = Field(default_factory=list, description="Timeline entries")
    current_position: int = Field(default=-1, description="Current rollback position (-1 = end)")
    total_count: int = Field(default=0, description="Total number of entries")

    model_config = {
        "json_schema_extra": {
            "example": {
                "entries": [
                    {
                        "index": 0,
                        "feature_id": "Sketch1",
                        "name": "Sketch1",
                        "feature_type": "sketch",
                        "is_suppressed": False
                    },
                    {
                        "index": 1,
                        "feature_id": "Extrude1",
                        "name": "Extrude1",
                        "feature_type": "extrude",
                        "is_suppressed": False
                    }
                ],
                "current_position": -1,
                "total_count": 2
            }
        }
    }
