"""Geometry models for Fusion 360 MCP Server.

Defines fundamental 3D geometry types used throughout the system.
"""

from pydantic import BaseModel, Field, field_validator, computed_field
from typing import Optional, List, Tuple
import math


class Point3D(BaseModel):
    """3D point in space (coordinates in mm)."""

    x: float = Field(default=0.0, description="X coordinate in mm")
    y: float = Field(default=0.0, description="Y coordinate in mm")
    z: float = Field(default=0.0, description="Z coordinate in mm")

    def to_tuple(self) -> Tuple[float, float, float]:
        """Convert to tuple."""
        return (self.x, self.y, self.z)

    def distance_to(self, other: "Point3D") -> float:
        """Calculate Euclidean distance to another point."""
        return math.sqrt(
            (self.x - other.x) ** 2 +
            (self.y - other.y) ** 2 +
            (self.z - other.z) ** 2
        )

    def __add__(self, other: "Vector3D") -> "Point3D":
        """Add a vector to this point."""
        return Point3D(x=self.x + other.x, y=self.y + other.y, z=self.z + other.z)

    def __sub__(self, other: "Point3D") -> "Vector3D":
        """Subtract another point to get a vector."""
        return Vector3D(x=self.x - other.x, y=self.y - other.y, z=self.z - other.z)

    model_config = {
        "json_schema_extra": {
            "example": {"x": 50.0, "y": 25.0, "z": 10.0}
        }
    }


class Vector3D(BaseModel):
    """3D vector (direction and magnitude)."""

    x: float = Field(default=0.0, description="X component")
    y: float = Field(default=0.0, description="Y component")
    z: float = Field(default=0.0, description="Z component")

    @computed_field
    @property
    def magnitude(self) -> float:
        """Calculate vector magnitude/length."""
        return math.sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2)

    def normalize(self) -> "Vector3D":
        """Return normalized (unit) vector."""
        mag = self.magnitude
        if mag == 0:
            return Vector3D(x=0, y=0, z=0)
        return Vector3D(x=self.x / mag, y=self.y / mag, z=self.z / mag)

    def dot(self, other: "Vector3D") -> float:
        """Dot product with another vector."""
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: "Vector3D") -> "Vector3D":
        """Cross product with another vector."""
        return Vector3D(
            x=self.y * other.z - self.z * other.y,
            y=self.z * other.x - self.x * other.z,
            z=self.x * other.y - self.y * other.x
        )

    def __mul__(self, scalar: float) -> "Vector3D":
        """Multiply by scalar."""
        return Vector3D(x=self.x * scalar, y=self.y * scalar, z=self.z * scalar)

    def __rmul__(self, scalar: float) -> "Vector3D":
        """Right multiply by scalar."""
        return self.__mul__(scalar)

    def __add__(self, other: "Vector3D") -> "Vector3D":
        """Add another vector."""
        return Vector3D(x=self.x + other.x, y=self.y + other.y, z=self.z + other.z)

    def __neg__(self) -> "Vector3D":
        """Negate the vector."""
        return Vector3D(x=-self.x, y=-self.y, z=-self.z)

    model_config = {
        "json_schema_extra": {
            "example": {"x": 1.0, "y": 0.0, "z": 0.0}
        }
    }


class BoundingBox(BaseModel):
    """Axis-aligned bounding box."""

    min_point: Point3D = Field(description="Minimum corner point")
    max_point: Point3D = Field(description="Maximum corner point")

    @computed_field
    @property
    def dimensions(self) -> Vector3D:
        """Get dimensions (width, depth, height)."""
        return Vector3D(
            x=self.max_point.x - self.min_point.x,
            y=self.max_point.y - self.min_point.y,
            z=self.max_point.z - self.min_point.z
        )

    @computed_field
    @property
    def center(self) -> Point3D:
        """Get center point of bounding box."""
        return Point3D(
            x=(self.min_point.x + self.max_point.x) / 2,
            y=(self.min_point.y + self.max_point.y) / 2,
            z=(self.min_point.z + self.max_point.z) / 2
        )

    @computed_field
    @property
    def volume(self) -> float:
        """Calculate bounding box volume."""
        dims = self.dimensions
        return abs(dims.x * dims.y * dims.z)

    def contains(self, point: Point3D) -> bool:
        """Check if point is inside bounding box."""
        return (
            self.min_point.x <= point.x <= self.max_point.x and
            self.min_point.y <= point.y <= self.max_point.y and
            self.min_point.z <= point.z <= self.max_point.z
        )

    def intersects(self, other: "BoundingBox") -> bool:
        """Check if this bounding box intersects another."""
        return not (
            self.max_point.x < other.min_point.x or
            self.min_point.x > other.max_point.x or
            self.max_point.y < other.min_point.y or
            self.min_point.y > other.max_point.y or
            self.max_point.z < other.min_point.z or
            self.min_point.z > other.max_point.z
        )

    model_config = {
        "json_schema_extra": {
            "example": {
                "min_point": {"x": 0, "y": 0, "z": 0},
                "max_point": {"x": 100, "y": 50, "z": 10}
            }
        }
    }


class Matrix3D(BaseModel):
    """4x4 transformation matrix for 3D transformations."""

    elements: List[List[float]] = Field(
        default_factory=lambda: [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0]
        ],
        description="4x4 matrix elements in row-major order"
    )

    @field_validator("elements")
    @classmethod
    def validate_matrix_size(cls, v: List[List[float]]) -> List[List[float]]:
        """Validate matrix is 4x4."""
        if len(v) != 4 or any(len(row) != 4 for row in v):
            raise ValueError("Matrix must be 4x4")
        return v

    @classmethod
    def identity(cls) -> "Matrix3D":
        """Create identity matrix."""
        return cls()

    @classmethod
    def translation(cls, x: float, y: float, z: float) -> "Matrix3D":
        """Create translation matrix."""
        return cls(elements=[
            [1.0, 0.0, 0.0, x],
            [0.0, 1.0, 0.0, y],
            [0.0, 0.0, 1.0, z],
            [0.0, 0.0, 0.0, 1.0]
        ])

    @classmethod
    def rotation_x(cls, angle_rad: float) -> "Matrix3D":
        """Create rotation matrix around X axis."""
        c, s = math.cos(angle_rad), math.sin(angle_rad)
        return cls(elements=[
            [1.0, 0.0, 0.0, 0.0],
            [0.0, c, -s, 0.0],
            [0.0, s, c, 0.0],
            [0.0, 0.0, 0.0, 1.0]
        ])

    @classmethod
    def rotation_y(cls, angle_rad: float) -> "Matrix3D":
        """Create rotation matrix around Y axis."""
        c, s = math.cos(angle_rad), math.sin(angle_rad)
        return cls(elements=[
            [c, 0.0, s, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [-s, 0.0, c, 0.0],
            [0.0, 0.0, 0.0, 1.0]
        ])

    @classmethod
    def rotation_z(cls, angle_rad: float) -> "Matrix3D":
        """Create rotation matrix around Z axis."""
        c, s = math.cos(angle_rad), math.sin(angle_rad)
        return cls(elements=[
            [c, -s, 0.0, 0.0],
            [s, c, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0]
        ])

    @classmethod
    def scaling(cls, sx: float, sy: float, sz: float) -> "Matrix3D":
        """Create scaling matrix."""
        return cls(elements=[
            [sx, 0.0, 0.0, 0.0],
            [0.0, sy, 0.0, 0.0],
            [0.0, 0.0, sz, 0.0],
            [0.0, 0.0, 0.0, 1.0]
        ])

    def transform_point(self, point: Point3D) -> Point3D:
        """Apply transformation to a point."""
        e = self.elements
        x = e[0][0] * point.x + e[0][1] * point.y + e[0][2] * point.z + e[0][3]
        y = e[1][0] * point.x + e[1][1] * point.y + e[1][2] * point.z + e[1][3]
        z = e[2][0] * point.x + e[2][1] * point.y + e[2][2] * point.z + e[2][3]
        return Point3D(x=x, y=y, z=z)

    def transform_vector(self, vector: Vector3D) -> Vector3D:
        """Apply transformation to a vector (ignoring translation)."""
        e = self.elements
        x = e[0][0] * vector.x + e[0][1] * vector.y + e[0][2] * vector.z
        y = e[1][0] * vector.x + e[1][1] * vector.y + e[1][2] * vector.z
        z = e[2][0] * vector.x + e[2][1] * vector.y + e[2][2] * vector.z
        return Vector3D(x=x, y=y, z=z)


class PlaneSpec(BaseModel):
    """Specification for a construction plane."""

    plane_type: str = Field(
        default="XY",
        description="Plane type: XY, YZ, XZ, or face_id reference"
    )
    offset: float = Field(default=0.0, description="Offset from plane in mm")
    origin: Optional[Point3D] = Field(default=None, description="Custom origin point")
    normal: Optional[Vector3D] = Field(default=None, description="Plane normal vector")

    @field_validator("plane_type")
    @classmethod
    def validate_plane_type(cls, v: str) -> str:
        """Validate plane type."""
        valid_types = {"XY", "YZ", "XZ"}
        if v not in valid_types and not v.startswith("face_"):
            raise ValueError(f"plane_type must be one of {valid_types} or a face_id reference (e.g., 'face_001')")
        return v

    def get_normal(self) -> Vector3D:
        """Get the normal vector for this plane."""
        if self.normal:
            return self.normal
        normals = {
            "XY": Vector3D(x=0, y=0, z=1),
            "YZ": Vector3D(x=1, y=0, z=0),
            "XZ": Vector3D(x=0, y=1, z=0),
        }
        return normals.get(self.plane_type, Vector3D(x=0, y=0, z=1))

    model_config = {
        "json_schema_extra": {
            "example": {"plane_type": "XY", "offset": 10.0}
        }
    }
