"""Plane serializer for Fusion 360 construction planes.

Converts Fusion 360 ConstructionPlane objects to JSON-serializable dictionaries.

All coordinates are returned in millimeters (mm).
"""

from typing import Dict, Any, TYPE_CHECKING
from .base import BaseSerializer, FusionObject

if TYPE_CHECKING:
    from core.entity_registry import EntityRegistry


class PlaneSerializer(BaseSerializer):
    """Serializer for construction plane entities.

    Handles serialization of ConstructionPlane objects from Fusion 360.
    """

    def serialize_construction_plane(self, plane: FusionObject) -> Dict[str, Any]:
        """Serialize a construction plane to dict.

        Args:
            plane: Fusion 360 ConstructionPlane object

        Returns:
            Dict with id, name, origin, normal, and visibility info
        """
        plane_id = self.registry.register_construction_plane(plane)

        # Get plane geometry (adsk.core.Plane)
        geometry = self.safe_get(plane, 'geometry')

        origin = {"x": 0.0, "y": 0.0, "z": 0.0}
        normal = {"x": 0.0, "y": 0.0, "z": 1.0}

        if geometry:
            # Get origin point
            origin_point = self.safe_get(geometry, 'origin')
            if origin_point:
                origin = self.serialize_point3d(origin_point)

            # Get normal vector
            normal_vector = self.safe_get(geometry, 'normal')
            if normal_vector:
                normal = self.serialize_vector3d(normal_vector)

        return {
            "id": plane_id,
            "name": self.safe_get(plane, 'name', plane_id),
            "origin": origin,
            "normal": normal,
            "is_visible": self.safe_get(plane, 'isVisible', True),
            "is_parametric": self.safe_get(plane, 'isParametric', True),
        }

    def serialize_plane_feature(self, plane: FusionObject) -> Dict[str, Any]:
        """Serialize a construction plane as a feature for timeline reference.

        Args:
            plane: Fusion 360 ConstructionPlane object

        Returns:
            Dict with id, type, and name for timeline reference
        """
        # Construction planes are features in the timeline
        # We register them in the feature registry as well
        plane_id = self.registry.register_construction_plane(plane)

        return {
            "id": plane_id,
            "type": "construction_plane",
            "name": self.safe_get(plane, 'name', plane_id),
        }
