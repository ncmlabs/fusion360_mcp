"""Construction plane operations for Fusion 360 MCP Add-in.

These operations create construction planes in Fusion 360 and return
structured results with entity IDs and geometric information.

All dimensions are in millimeters (mm), angles in degrees.
"""

from typing import Dict, Any, Optional
import math

# Fusion 360 API imports
try:
    import adsk.core
    import adsk.fusion
    FUSION_AVAILABLE = True
except ImportError:
    FUSION_AVAILABLE = False

from core.entity_registry import get_registry
from serializers.plane_serializer import PlaneSerializer
from shared.exceptions import (
    DesignStateError,
    FeatureError,
    InvalidParameterError,
    EntityNotFoundError,
)


def _get_active_design() -> Any:
    """Get the active Fusion 360 design.

    Returns:
        Fusion Design object

    Raises:
        DesignStateError: If no design is active
    """
    if not FUSION_AVAILABLE:
        raise DesignStateError(
            "not_available",
            "Fusion 360 API not available. Running outside of Fusion 360."
        )

    app = adsk.core.Application.get()
    if not app:
        raise DesignStateError(
            "no_application",
            "Cannot get Fusion 360 application instance."
        )

    product = app.activeProduct
    if not product:
        raise DesignStateError(
            "no_product",
            "No active product. Please open a design."
        )

    design = adsk.fusion.Design.cast(product)
    if not design:
        raise DesignStateError(
            "not_design",
            "Active product is not a Design. Open a Fusion 360 design file."
        )

    return design


def _get_component(design: Any, component_id: Optional[str]) -> Any:
    """Get component by ID or return root component.

    Args:
        design: Fusion Design object
        component_id: Optional component ID

    Returns:
        Fusion Component object
    """
    if component_id:
        registry = get_registry()
        component = registry.get_component(component_id)
        if component:
            return component

    return design.rootComponent


def _resolve_base_plane(component: Any, plane_spec: str) -> Any:
    """Resolve a plane specification to a Fusion plane or face object.

    Args:
        component: Fusion Component object
        plane_spec: Plane specification - "XY", "YZ", "XZ", face_id, or plane_id

    Returns:
        Fusion ConstructionPlane or BRepFace object

    Raises:
        EntityNotFoundError: If plane/face not found
        InvalidParameterError: If plane specification is invalid
    """
    # Check standard construction planes
    plane_map = {
        "XY": component.xYConstructionPlane,
        "YZ": component.yZConstructionPlane,
        "XZ": component.xZConstructionPlane,
    }

    plane_upper = plane_spec.upper()
    if plane_upper in plane_map:
        return plane_map[plane_upper]

    # Check registry for plane_id or face_id
    registry = get_registry()

    # Try as construction plane
    plane = registry.get_construction_plane(plane_spec)
    if plane:
        return plane

    # Try as sub-entity (face)
    face = registry.get_sub_entity(plane_spec)
    if face:
        return face

    # Try resolving via general resolve
    entity = registry.resolve_id(plane_spec)
    if entity:
        return entity

    raise EntityNotFoundError(
        "plane/face",
        plane_spec,
        available_entities=["XY", "YZ", "XZ"] + registry.get_available_construction_plane_ids()
    )


def _serialize_plane_result(plane: Any, registry: Any) -> Dict[str, Any]:
    """Serialize plane creation result.

    Args:
        plane: Created Fusion ConstructionPlane
        registry: Entity registry

    Returns:
        Dict with plane and feature information
    """
    serializer = PlaneSerializer(registry)

    return {
        "success": True,
        "plane": serializer.serialize_construction_plane(plane),
        "feature": serializer.serialize_plane_feature(plane),
    }


def create_offset_plane(
    base_plane: str,
    offset: float,
    name: Optional[str] = None,
    component_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a construction plane offset from an existing plane or face.

    Args:
        base_plane: Base plane reference ("XY", "YZ", "XZ", face_id, or plane_id)
        offset: Offset distance in mm (positive or negative)
        name: Optional name for the new plane
        component_id: Optional component ID to create plane in

    Returns:
        Dict with plane info including id, origin, normal

    Raises:
        EntityNotFoundError: If base plane not found
        FeatureError: If plane creation fails
    """
    design = _get_active_design()
    registry = get_registry()
    component = _get_component(design, component_id)

    # Resolve base plane
    base = _resolve_base_plane(component, base_plane)

    # Create offset plane
    planes = component.constructionPlanes
    plane_input = planes.createInput()

    # Convert mm to cm for Fusion API
    offset_value = adsk.core.ValueInput.createByReal(offset / 10.0)

    success = plane_input.setByOffset(base, offset_value)
    if not success:
        raise FeatureError(
            "construction_plane",
            "Failed to set offset plane definition",
            affected_entities=[base_plane]
        )

    new_plane = planes.add(plane_input)
    if not new_plane:
        raise FeatureError(
            "construction_plane",
            "Failed to create offset plane"
        )

    # Set name if provided
    if name:
        new_plane.name = name

    return _serialize_plane_result(new_plane, registry)


def create_angle_plane(
    base_plane: str,
    edge_id: str,
    angle: float,
    name: Optional[str] = None,
    component_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a construction plane at an angle from a plane along an edge.

    Args:
        base_plane: Base plane reference ("XY", "YZ", "XZ", face_id, or plane_id)
        edge_id: ID of the linear edge to rotate around
        angle: Rotation angle in degrees
        name: Optional name for the new plane
        component_id: Optional component ID to create plane in

    Returns:
        Dict with plane info including id, origin, normal

    Raises:
        EntityNotFoundError: If base plane or edge not found
        FeatureError: If plane creation fails
    """
    design = _get_active_design()
    registry = get_registry()
    component = _get_component(design, component_id)

    # Resolve base plane
    base = _resolve_base_plane(component, base_plane)

    # Resolve edge
    edge = registry.get_sub_entity(edge_id)
    if not edge:
        edge = registry.resolve_id(edge_id)

    if not edge:
        raise EntityNotFoundError(
            "edge",
            edge_id,
            suggestion="Use get_body_by_id with include_edges=True to see available edges."
        )

    # Create angled plane
    planes = component.constructionPlanes
    plane_input = planes.createInput()

    # Convert degrees to radians for Fusion API
    angle_value = adsk.core.ValueInput.createByReal(math.radians(angle))

    success = plane_input.setByAngle(edge, angle_value, base)
    if not success:
        raise FeatureError(
            "construction_plane",
            "Failed to set angle plane definition. Ensure the edge lies on or is parallel to the base plane.",
            affected_entities=[base_plane, edge_id]
        )

    new_plane = planes.add(plane_input)
    if not new_plane:
        raise FeatureError(
            "construction_plane",
            "Failed to create angle plane"
        )

    # Set name if provided
    if name:
        new_plane.name = name

    return _serialize_plane_result(new_plane, registry)


def create_three_point_plane(
    point1: Dict[str, float],
    point2: Dict[str, float],
    point3: Dict[str, float],
    name: Optional[str] = None,
    component_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a construction plane through three points.

    Points can be specified as:
    - Coordinates: {x, y, z} in mm
    - Entity ID: {id: "vertex_id"} referencing a body vertex

    Args:
        point1: First point - {x, y, z} in mm OR {id: "vertex_id"}
        point2: Second point - {x, y, z} in mm OR {id: "vertex_id"}
        point3: Third point - {x, y, z} in mm OR {id: "vertex_id"}
        name: Optional name for the new plane
        component_id: Optional component ID to create plane in

    Returns:
        Dict with plane info including id, origin, normal

    Raises:
        InvalidParameterError: If points are collinear
        EntityNotFoundError: If vertex ID not found
        FeatureError: If plane creation fails
    """
    design = _get_active_design()
    registry = get_registry()
    component = _get_component(design, component_id)

    def resolve_point(point_spec, point_name):
        """Resolve point specification to a Fusion entity or Point3D."""
        if isinstance(point_spec, dict):
            # Check if it's an entity ID reference
            if 'id' in point_spec:
                entity = registry.get_sub_entity(point_spec['id'])
                if not entity:
                    entity = registry.resolve_id(point_spec['id'])
                if not entity:
                    raise EntityNotFoundError(
                        "vertex/point",
                        point_spec['id'],
                        suggestion="Use get_body_by_id with include_edges=True to find vertex IDs."
                    )
                return entity
            # Otherwise treat as coordinates
            elif all(k in point_spec for k in ['x', 'y', 'z']):
                # Return Point3D for coordinate-based points
                return adsk.core.Point3D.create(
                    point_spec["x"] / 10.0,
                    point_spec["y"] / 10.0,
                    point_spec["z"] / 10.0
                )
        raise InvalidParameterError(
            point_name,
            point_spec,
            reason=f"Point must be {{x, y, z}} coordinates or {{id: 'vertex_id'}}. Got: {point_spec}"
        )

    # Resolve all three points
    pt1 = resolve_point(point1, "point1")
    pt2 = resolve_point(point2, "point2")
    pt3 = resolve_point(point3, "point3")

    # Check if all points are entity references (use setByThreePoints)
    # or if any are coordinates (need workaround)
    all_entities = all(not isinstance(p, adsk.core.Point3D) for p in [pt1, pt2, pt3])

    planes = component.constructionPlanes
    plane_input = planes.createInput()

    if all_entities:
        # All points are entity references - use native API
        success = plane_input.setByThreePoints(pt1, pt2, pt3)
        if not success:
            raise FeatureError(
                "construction_plane",
                "Failed to create plane through three points. Points may be collinear.",
                suggestion="Ensure the three points are not on the same line."
            )
    else:
        # At least one point is coordinates - need workaround
        # Get Point3D from each (entities have .geometry property)
        def get_point3d(pt):
            if isinstance(pt, adsk.core.Point3D):
                return pt
            # For vertices/sketch points, get the geometry
            if hasattr(pt, 'geometry'):
                return pt.geometry
            raise FeatureError(
                "construction_plane",
                f"Cannot get Point3D from entity type: {type(pt)}"
            )

        p1 = get_point3d(pt1)
        p2 = get_point3d(pt2)
        p3 = get_point3d(pt3)

        # Calculate plane normal from three points using cross product
        v1_x = p2.x - p1.x
        v1_y = p2.y - p1.y
        v1_z = p2.z - p1.z

        v2_x = p3.x - p1.x
        v2_y = p3.y - p1.y
        v2_z = p3.z - p1.z

        # Cross product: normal = v1 x v2
        normal_x = v1_y * v2_z - v1_z * v2_y
        normal_y = v1_z * v2_x - v1_x * v2_z
        normal_z = v1_x * v2_y - v1_y * v2_x

        normal_length = math.sqrt(normal_x**2 + normal_y**2 + normal_z**2)
        if normal_length < 1e-10:
            raise InvalidParameterError(
                "points",
                [point1, point2, point3],
                reason="The three points are collinear (on the same line)."
            )

        # For coordinate-based planes, we need to use a workaround:
        # Find the closest standard plane and create offset + angle
        # For now, raise an informative error
        raise FeatureError(
            "construction_plane",
            "Creating planes from arbitrary coordinates is not supported in parametric design mode.",
            suggestion="Use vertex IDs from existing bodies instead: {id: 'Body1_vertex_0'}. "
                       "Get vertex IDs with get_body_by_id(body_id, include_edges=True)."
        )

    # Create the plane (only reached if all_entities path succeeded)
    new_plane = planes.add(plane_input)
    if not new_plane:
        raise FeatureError(
            "construction_plane",
            "Failed to create three-point plane"
        )

    # Set name if provided
    if name:
        new_plane.name = name

    return _serialize_plane_result(new_plane, registry)


def create_midplane(
    plane1: str,
    plane2: str,
    name: Optional[str] = None,
    component_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a construction plane midway between two planes or faces.

    Args:
        plane1: First plane reference ("XY", "YZ", "XZ", face_id, or plane_id)
        plane2: Second plane reference (must be parallel to plane1)
        name: Optional name for the new plane
        component_id: Optional component ID to create plane in

    Returns:
        Dict with plane info including id, origin, normal

    Raises:
        EntityNotFoundError: If planes not found
        FeatureError: If planes are not parallel or creation fails
    """
    design = _get_active_design()
    registry = get_registry()
    component = _get_component(design, component_id)

    # Resolve both planes
    p1 = _resolve_base_plane(component, plane1)
    p2 = _resolve_base_plane(component, plane2)

    # Create midplane
    planes = component.constructionPlanes
    plane_input = planes.createInput()

    success = plane_input.setByTwoPlanes(p1, p2)
    if not success:
        raise FeatureError(
            "construction_plane",
            "Failed to create midplane. The two planes must be parallel.",
            affected_entities=[plane1, plane2],
            suggestion="Ensure both planes are parallel to each other."
        )

    new_plane = planes.add(plane_input)
    if not new_plane:
        raise FeatureError(
            "construction_plane",
            "Failed to create midplane"
        )

    # Set name if provided
    if name:
        new_plane.name = name

    return _serialize_plane_result(new_plane, registry)
