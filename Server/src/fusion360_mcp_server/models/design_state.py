"""Design state models for Fusion 360 MCP Server.

Defines the complete design state representation including components and assemblies.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from .geometry import Matrix3D
from .body import BodySummary
from .sketch import SketchSummary
from .feature import Parameter, Timeline


class UnitsType(str, Enum):
    """Design unit types."""
    MM = "mm"
    CM = "cm"
    M = "m"
    INCH = "in"
    FT = "ft"


class JointType(str, Enum):
    """Types of assembly joints."""
    RIGID = "rigid"
    REVOLUTE = "revolute"
    SLIDER = "slider"
    CYLINDRICAL = "cylindrical"
    PIN_SLOT = "pin_slot"
    PLANAR = "planar"
    BALL = "ball"


class Component(BaseModel):
    """A component in the design (can be nested)."""

    id: str = Field(description="Unique component identifier")
    name: str = Field(description="Component display name")
    is_root: bool = Field(default=False, description="Whether this is the root component")
    is_active: bool = Field(default=False, description="Whether this is the active component")

    # Content counts
    bodies_count: int = Field(default=0, description="Number of bodies")
    sketches_count: int = Field(default=0, description="Number of sketches")
    occurrences_count: int = Field(default=0, description="Number of sub-occurrences")
    features_count: int = Field(default=0, description="Number of features")

    # Content summaries
    body_ids: List[str] = Field(default_factory=list, description="IDs of contained bodies")
    sketch_ids: List[str] = Field(default_factory=list, description="IDs of contained sketches")

    # Parent reference
    parent_id: Optional[str] = Field(default=None, description="Parent component ID")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "comp_001",
                "name": "RootComponent",
                "is_root": True,
                "is_active": True,
                "bodies_count": 3,
                "sketches_count": 2,
                "body_ids": ["body_001", "body_002", "body_003"]
            }
        }
    }


class Occurrence(BaseModel):
    """An occurrence (instance) of a component."""

    id: str = Field(description="Unique occurrence identifier")
    name: str = Field(description="Occurrence name")
    component_id: str = Field(description="ID of the referenced component")
    transform: Matrix3D = Field(
        default_factory=Matrix3D.identity,
        description="Transform from component to parent space"
    )
    is_visible: bool = Field(default=True, description="Whether occurrence is visible")
    is_grounded: bool = Field(default=False, description="Whether occurrence is grounded")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "occ_001",
                "name": "Bracket:1",
                "component_id": "comp_002",
                "is_visible": True,
                "is_grounded": False
            }
        }
    }


class Joint(BaseModel):
    """A joint between components."""

    id: str = Field(description="Unique joint identifier")
    name: str = Field(description="Joint display name")
    joint_type: JointType = Field(description="Type of joint")
    occurrence1_id: str = Field(description="First occurrence ID")
    occurrence2_id: str = Field(description="Second occurrence ID")
    is_suppressed: bool = Field(default=False, description="Whether joint is suppressed")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "joint_001",
                "name": "Rigid1",
                "joint_type": "rigid",
                "occurrence1_id": "occ_001",
                "occurrence2_id": "occ_002",
                "is_suppressed": False
            }
        }
    }


class DesignInfo(BaseModel):
    """Basic design information."""

    name: str = Field(description="Design name")
    units: UnitsType = Field(default=UnitsType.MM, description="Design units")
    version: Optional[str] = Field(default=None, description="Design version")

    # Content counts
    bodies_count: int = Field(default=0, description="Total bodies in design")
    sketches_count: int = Field(default=0, description="Total sketches in design")
    components_count: int = Field(default=0, description="Total components (including root)")
    features_count: int = Field(default=0, description="Total features in timeline")
    parameters_count: int = Field(default=0, description="Total parameters")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "MyDesign",
                "units": "mm",
                "bodies_count": 3,
                "sketches_count": 2,
                "components_count": 1,
                "features_count": 5,
                "parameters_count": 10
            }
        }
    }


class DesignState(BaseModel):
    """Complete snapshot of the design state."""

    # Basic info
    design: DesignInfo = Field(description="Design information")

    # Root component
    root_component: Component = Field(description="Root component")

    # All components (flat list)
    components: List[Component] = Field(default_factory=list, description="All components")

    # Bodies (in root component or filtered)
    bodies: List[BodySummary] = Field(default_factory=list, description="Body summaries")

    # Sketches (in root component or filtered)
    sketches: List[SketchSummary] = Field(default_factory=list, description="Sketch summaries")

    # Timeline
    timeline: Optional[Timeline] = Field(default=None, description="Design timeline")

    # Parameters
    user_parameters: List[Parameter] = Field(
        default_factory=list,
        description="User-defined parameters"
    )

    # Occurrences (for assemblies)
    occurrences: List[Occurrence] = Field(
        default_factory=list,
        description="Component occurrences"
    )

    # Joints (for assemblies)
    joints: List[Joint] = Field(
        default_factory=list,
        description="Assembly joints"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "design": {
                    "name": "MyDesign",
                    "units": "mm",
                    "bodies_count": 3,
                    "sketches_count": 2,
                    "components_count": 1
                },
                "root_component": {
                    "id": "root",
                    "name": "RootComponent",
                    "is_root": True,
                    "bodies_count": 3
                },
                "bodies": [
                    {
                        "id": "body_001",
                        "name": "base_plate",
                        "is_solid": True,
                        "volume": 50000.0
                    }
                ]
            }
        }
    }
