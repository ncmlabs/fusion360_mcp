"""Body models for Fusion 360 MCP Server.

Defines B-Rep (Boundary Representation) topology types.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from .geometry import Point3D, Vector3D, BoundingBox


class EntityType(str, Enum):
    """Types of geometric entities."""
    BODY = "body"
    FACE = "face"
    EDGE = "edge"
    VERTEX = "vertex"


class FaceType(str, Enum):
    """Types of faces in B-Rep."""
    PLANAR = "planar"
    CYLINDRICAL = "cylindrical"
    CONICAL = "conical"
    SPHERICAL = "spherical"
    TOROIDAL = "toroidal"
    SPLINE = "spline"


class EdgeType(str, Enum):
    """Types of edges in B-Rep."""
    LINE = "line"
    CIRCLE = "circle"
    ARC = "arc"
    ELLIPSE = "ellipse"
    SPLINE = "spline"


class Vertex(BaseModel):
    """A vertex in B-Rep topology."""

    id: str = Field(description="Unique vertex identifier")
    position: Point3D = Field(description="Vertex position in space")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "vertex_001",
                "position": {"x": 0, "y": 0, "z": 0}
            }
        }
    }


class Edge(BaseModel):
    """An edge in B-Rep topology."""

    id: str = Field(description="Unique edge identifier")
    edge_type: EdgeType = Field(description="Type of edge geometry")
    start_vertex_id: str = Field(description="Start vertex ID")
    end_vertex_id: str = Field(description="End vertex ID")
    length: float = Field(description="Edge length in mm")
    is_closed: bool = Field(default=False, description="Whether edge forms a closed loop")

    # Optional detailed geometry
    center: Optional[Point3D] = Field(default=None, description="Center for arc/circle edges")
    radius: Optional[float] = Field(default=None, description="Radius for arc/circle edges")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "edge_001",
                "edge_type": "line",
                "start_vertex_id": "vertex_001",
                "end_vertex_id": "vertex_002",
                "length": 100.0,
                "is_closed": False
            }
        }
    }


class Face(BaseModel):
    """A face in B-Rep topology."""

    id: str = Field(description="Unique face identifier")
    face_type: FaceType = Field(description="Type of face geometry")
    area: float = Field(description="Face area in mm^2")
    normal: Vector3D = Field(description="Face normal vector (at centroid)")
    centroid: Point3D = Field(description="Face centroid position")
    edge_ids: List[str] = Field(default_factory=list, description="IDs of bounding edges")

    # Type-specific properties
    is_planar: bool = Field(default=False, description="Whether face is planar")

    # For cylindrical/conical faces
    axis: Optional[Vector3D] = Field(default=None, description="Axis direction for cylindrical/conical faces")
    radius: Optional[float] = Field(default=None, description="Radius for cylindrical faces")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "face_001",
                "face_type": "planar",
                "area": 5000.0,
                "normal": {"x": 0, "y": 0, "z": 1},
                "centroid": {"x": 50, "y": 25, "z": 10},
                "edge_ids": ["edge_001", "edge_002", "edge_003", "edge_004"],
                "is_planar": True
            }
        }
    }


class Body(BaseModel):
    """A solid or surface body in the design."""

    id: str = Field(description="Unique body identifier")
    name: str = Field(description="Body display name")
    is_solid: bool = Field(default=True, description="Whether body is solid (vs surface)")
    is_visible: bool = Field(default=True, description="Whether body is visible")

    # Geometric properties
    bounding_box: BoundingBox = Field(description="Axis-aligned bounding box")
    volume: float = Field(default=0.0, description="Body volume in mm^3")
    area: float = Field(default=0.0, description="Total surface area in mm^2")
    center_of_mass: Optional[Point3D] = Field(default=None, description="Center of mass")

    # Topology counts
    faces_count: int = Field(default=0, description="Number of faces")
    edges_count: int = Field(default=0, description="Number of edges")
    vertices_count: int = Field(default=0, description="Number of vertices")

    # Detailed topology (optional, loaded on demand)
    faces: Optional[List[Face]] = Field(default=None, description="Face details")
    edges: Optional[List[Edge]] = Field(default=None, description="Edge details")
    vertices: Optional[List[Vertex]] = Field(default=None, description="Vertex details")

    # Parent reference
    component_id: Optional[str] = Field(default=None, description="Parent component ID")
    feature_id: Optional[str] = Field(default=None, description="Creating feature ID")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "body_001",
                "name": "base_plate",
                "is_solid": True,
                "is_visible": True,
                "bounding_box": {
                    "min_point": {"x": 0, "y": 0, "z": 0},
                    "max_point": {"x": 100, "y": 50, "z": 10}
                },
                "volume": 50000.0,
                "area": 13000.0,
                "center_of_mass": {"x": 50, "y": 25, "z": 5},
                "faces_count": 6,
                "edges_count": 12,
                "vertices_count": 8
            }
        }
    }


class BodySummary(BaseModel):
    """Lightweight body summary for list operations."""

    id: str = Field(description="Unique body identifier")
    name: str = Field(description="Body display name")
    is_solid: bool = Field(default=True, description="Whether body is solid")
    bounding_box: BoundingBox = Field(description="Axis-aligned bounding box")
    volume: float = Field(default=0.0, description="Body volume in mm^3")
    faces_count: int = Field(default=0, description="Number of faces")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "body_001",
                "name": "base_plate",
                "is_solid": True,
                "bounding_box": {
                    "min_point": {"x": 0, "y": 0, "z": 0},
                    "max_point": {"x": 100, "y": 50, "z": 10}
                },
                "volume": 50000.0,
                "faces_count": 6
            }
        }
    }
