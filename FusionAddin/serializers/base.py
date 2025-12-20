"""Base serializer for Fusion 360 API objects.

Provides common serialization methods for geometry primitives that are
shared across all entity serializers.

All coordinates and dimensions are returned in millimeters (mm).
"""

from typing import Dict, Any, Optional, TYPE_CHECKING

from utils.units import cm_to_mm

if TYPE_CHECKING:
    from core.entity_registry import EntityRegistry

# Type alias for Fusion API objects
FusionObject = Any


class BaseSerializer:
    """Base class for Fusion 360 object serialization.

    Provides common methods for serializing geometry primitives like
    points, vectors, and bounding boxes.

    Attributes:
        registry: EntityRegistry for ID tracking
    """

    def __init__(self, registry: "EntityRegistry") -> None:
        """Initialize serializer with entity registry.

        Args:
            registry: EntityRegistry instance for ID lookups
        """
        self.registry = registry

    def serialize_point3d(self, point: FusionObject) -> Dict[str, float]:
        """Serialize a Point3D to dict.

        Args:
            point: Fusion Point3D object (adsk.core.Point3D)

        Returns:
            Dict with x, y, z coordinates in millimeters (mm)
        """
        if point is None:
            return {"x": 0.0, "y": 0.0, "z": 0.0}

        return {
            "x": cm_to_mm(getattr(point, 'x', 0.0)),
            "y": cm_to_mm(getattr(point, 'y', 0.0)),
            "z": cm_to_mm(getattr(point, 'z', 0.0)),
        }

    def serialize_vector3d(self, vector: FusionObject) -> Dict[str, float]:
        """Serialize a Vector3D to dict.

        Args:
            vector: Fusion Vector3D object (adsk.core.Vector3D)

        Returns:
            Dict with x, y, z components
        """
        if vector is None:
            return {"x": 0.0, "y": 0.0, "z": 1.0}

        return {
            "x": getattr(vector, 'x', 0.0),
            "y": getattr(vector, 'y', 0.0),
            "z": getattr(vector, 'z', 0.0),
        }

    def serialize_bounding_box(self, bbox: FusionObject) -> Dict[str, Any]:
        """Serialize a BoundingBox3D to dict.

        Args:
            bbox: Fusion BoundingBox3D object (adsk.core.BoundingBox3D)

        Returns:
            Dict with min_point and max_point
        """
        if bbox is None:
            return {
                "min_point": {"x": 0.0, "y": 0.0, "z": 0.0},
                "max_point": {"x": 0.0, "y": 0.0, "z": 0.0},
            }

        min_point = getattr(bbox, 'minPoint', None)
        max_point = getattr(bbox, 'maxPoint', None)

        return {
            "min_point": self.serialize_point3d(min_point),
            "max_point": self.serialize_point3d(max_point),
        }

    def serialize_matrix3d(self, matrix: FusionObject) -> Dict[str, Any]:
        """Serialize a Matrix3D to dict.

        Args:
            matrix: Fusion Matrix3D object (adsk.core.Matrix3D)

        Returns:
            Dict with 4x4 matrix data and extracted transform components
        """
        if matrix is None:
            return {
                "data": [
                    [1.0, 0.0, 0.0, 0.0],
                    [0.0, 1.0, 0.0, 0.0],
                    [0.0, 0.0, 1.0, 0.0],
                    [0.0, 0.0, 0.0, 1.0],
                ],
                "translation": {"x": 0.0, "y": 0.0, "z": 0.0},
            }

        # Get matrix data as list
        data = []
        get_data = getattr(matrix, 'getAsCoordinateSystem', None)
        if get_data:
            # Extract as coordinate system for cleaner representation
            origin = None
            x_axis = None
            y_axis = None
            z_axis = None
            try:
                import adsk.core
                origin = adsk.core.Point3D.create(0, 0, 0)
                x_axis = adsk.core.Vector3D.create(1, 0, 0)
                y_axis = adsk.core.Vector3D.create(0, 1, 0)
                z_axis = adsk.core.Vector3D.create(0, 0, 1)
                matrix.getAsCoordinateSystem(origin, x_axis, y_axis, z_axis)
            except:
                pass

        # Get raw 16-element array
        as_array = getattr(matrix, 'asArray', None)
        if as_array:
            try:
                arr = matrix.asArray()
                data = [
                    list(arr[0:4]),
                    list(arr[4:8]),
                    list(arr[8:12]),
                    list(arr[12:16]),
                ]
            except:
                pass

        # Extract translation from matrix (convert cm to mm)
        translation = {"x": 0.0, "y": 0.0, "z": 0.0}
        get_translation = getattr(matrix, 'translation', None)
        if get_translation:
            try:
                trans = matrix.translation
                # Translation is a position offset, convert from cm to mm
                translation = {
                    "x": cm_to_mm(getattr(trans, 'x', 0.0)),
                    "y": cm_to_mm(getattr(trans, 'y', 0.0)),
                    "z": cm_to_mm(getattr(trans, 'z', 0.0)),
                }
            except:
                pass

        return {
            "data": data if data else [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
            "translation": translation,
        }

    def safe_get(
        self,
        obj: FusionObject,
        attr: str,
        default: Any = None,
        converter: Optional[callable] = None
    ) -> Any:
        """Safely get an attribute from a Fusion object.

        Args:
            obj: Fusion API object
            attr: Attribute name to get
            default: Default value if attribute is missing or fails
            converter: Optional function to convert the value

        Returns:
            The attribute value, converted value, or default
        """
        try:
            value = getattr(obj, attr, None)
            if value is None:
                return default
            if converter:
                return converter(value)
            return value
        except Exception:
            return default
