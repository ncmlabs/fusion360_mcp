"""Body creation operations for Fusion 360 MCP Add-in.

These operations create solid bodies in Fusion 360 and return
structured results with entity IDs and geometric information.
"""

from typing import Dict, Any, Optional, Tuple
import math

# Fusion 360 API imports
try:
    import adsk.core
    import adsk.fusion
    FUSION_AVAILABLE = True
except ImportError:
    FUSION_AVAILABLE = False

from core.entity_registry import get_registry
from serializers.body_serializer import BodySerializer
from serializers.feature_serializer import FeatureSerializer
from shared.exceptions import (
    DesignStateError,
    FeatureError,
    InvalidParameterError,
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


def _resolve_plane(
    component: Any,
    plane_spec: str,
    offset: float = 0.0
) -> Tuple[Any, Optional[Any]]:
    """Resolve a plane specification to a Fusion construction plane.

    Args:
        component: Fusion Component object
        plane_spec: Plane specification (XY, YZ, XZ, or face_id)
        offset: Offset from the plane in mm

    Returns:
        Tuple of (plane_or_face, construction_plane_if_created)

    Raises:
        InvalidParameterError: If plane specification is invalid
    """
    # Map standard plane names to component planes
    plane_map = {
        "XY": component.xYConstructionPlane,
        "YZ": component.yZConstructionPlane,
        "XZ": component.xZConstructionPlane,
    }

    plane_upper = plane_spec.upper()

    if plane_upper in plane_map:
        base_plane = plane_map[plane_upper]

        # If offset, create offset construction plane
        if abs(offset) > 0.0001:
            planes = component.constructionPlanes
            plane_input = planes.createInput()

            # Create offset plane
            offset_value = adsk.core.ValueInput.createByReal(offset / 10.0)  # Convert mm to cm
            plane_input.setByOffset(base_plane, offset_value)

            offset_plane = planes.add(plane_input)
            return offset_plane, offset_plane

        return base_plane, None

    # Handle face_id reference
    if plane_spec.startswith("face_"):
        registry = get_registry()
        face = registry.get_sub_entity(plane_spec)
        if not face:
            raise InvalidParameterError(
                "plane",
                plane_spec,
                reason=f"Face '{plane_spec}' not found. Use get_body_by_id with include_faces=True to see available faces."
            )
        return face, None

    raise InvalidParameterError(
        "plane",
        plane_spec,
        valid_values=["XY", "YZ", "XZ", "face_<id>"],
        reason=f"Invalid plane specification: {plane_spec}"
    )


def _serialize_body_result(
    body: Any,
    feature: Any,
    registry: Any
) -> Dict[str, Any]:
    """Serialize body creation result.

    Args:
        body: Created Fusion BRepBody
        feature: Feature that created the body
        registry: Entity registry

    Returns:
        Dict with body and feature information
    """
    body_serializer = BodySerializer(registry)
    feature_serializer = FeatureSerializer(registry)

    body_data = body_serializer.serialize_summary(body)
    feature_data = feature_serializer.serialize_feature(feature)

    return {
        "body": body_data,
        "feature": feature_data,
    }


def create_box(
    width: float,
    depth: float,
    height: float,
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
    name: Optional[str] = None,
    plane: str = "XY",
    component_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a box (rectangular prism) in the design.

    Creates a box by extruding a rectangular sketch profile.
    The box is centered at the specified (x, y) position on the
    construction plane, with the base at z (or offset by z for XY plane).

    Args:
        width: Box width in mm (X direction on XY plane)
        depth: Box depth in mm (Y direction on XY plane)
        height: Box height in mm (extrusion distance)
        x: X position of box center in mm
        y: Y position of box center in mm
        z: Z position (offset from plane) in mm
        name: Optional name for the body
        plane: Construction plane (XY, YZ, XZ)
        component_id: Optional component ID (uses root if not specified)

    Returns:
        Dict with body_id, feature_id, and bounding_box

    Raises:
        InvalidParameterError: If dimensions are invalid
        FeatureError: If box creation fails
    """
    # Validate parameters
    if width <= 0:
        raise InvalidParameterError("width", width, min_value=0.001, reason="Width must be positive")
    if depth <= 0:
        raise InvalidParameterError("depth", depth, min_value=0.001, reason="Depth must be positive")
    if height <= 0:
        raise InvalidParameterError("height", height, min_value=0.001, reason="Height must be positive")

    design = _get_active_design()
    registry = get_registry()

    # Get target component
    if component_id:
        component = registry.get_component(component_id)
        if not component:
            component = design.rootComponent
    else:
        component = design.rootComponent

    # Resolve construction plane
    base_plane, created_plane = _resolve_plane(component, plane, z)

    try:
        # Create sketch on the plane
        sketches = component.sketches
        sketch = sketches.add(base_plane)

        # Convert dimensions from mm to cm (Fusion internal units)
        w_cm = width / 10.0
        d_cm = depth / 10.0
        h_cm = height / 10.0
        x_cm = x / 10.0
        y_cm = y / 10.0

        # Calculate rectangle corners (centered at x, y)
        x1 = x_cm - w_cm / 2
        y1 = y_cm - d_cm / 2
        x2 = x_cm + w_cm / 2
        y2 = y_cm + d_cm / 2

        # Draw rectangle on sketch
        lines = sketch.sketchCurves.sketchLines
        rect_lines = lines.addTwoPointRectangle(
            adsk.core.Point3D.create(x1, y1, 0),
            adsk.core.Point3D.create(x2, y2, 0)
        )

        # Get the profile
        if sketch.profiles.count == 0:
            raise FeatureError(
                "box",
                "Failed to create closed profile for extrusion",
                affected_entities=[sketch.name]
            )

        profile = sketch.profiles.item(0)

        # Create extrusion
        extrudes = component.features.extrudeFeatures
        extrude_input = extrudes.createInput(
            profile,
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        )

        # Set extrusion distance
        distance = adsk.core.ValueInput.createByReal(h_cm)
        extrude_input.setDistanceExtent(False, distance)

        # Create the extrusion
        extrude_feature = extrudes.add(extrude_input)

        if not extrude_feature:
            raise FeatureError(
                "box",
                "Extrusion operation failed"
            )

        # Get the created body
        bodies = extrude_feature.bodies
        if bodies.count == 0:
            raise FeatureError(
                "box",
                "No body was created by the extrusion"
            )

        body = bodies.item(0)

        # Set name if provided
        if name:
            body.name = name

        # Register entities
        body_id = registry.register_body(body)
        feature_id = registry.register_feature(extrude_feature)
        registry.register_sketch(sketch)

        # Clean up offset plane if created
        if created_plane:
            # Keep it for now - could delete if not needed
            pass

        # Serialize and return result
        result = _serialize_body_result(body, extrude_feature, registry)
        result["success"] = True

        return result

    except Exception as e:
        # Re-raise our custom exceptions
        if isinstance(e, (InvalidParameterError, FeatureError, DesignStateError)):
            raise

        # Wrap other exceptions
        raise FeatureError(
            "box",
            f"Failed to create box: {str(e)}",
            fusion_error=str(e)
        )


def create_cylinder(
    radius: float,
    height: float,
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
    name: Optional[str] = None,
    plane: str = "XY",
    component_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a cylinder in the design.

    Creates a cylinder by extruding a circular sketch profile.
    The cylinder is centered at (x, y) on the construction plane.

    Args:
        radius: Cylinder radius in mm
        height: Cylinder height in mm (extrusion distance)
        x: X position of cylinder center in mm
        y: Y position of cylinder center in mm
        z: Z position (offset from plane) in mm
        name: Optional name for the body
        plane: Construction plane (XY, YZ, XZ)
        component_id: Optional component ID (uses root if not specified)

    Returns:
        Dict with body_id, feature_id, and bounding_box

    Raises:
        InvalidParameterError: If dimensions are invalid
        FeatureError: If cylinder creation fails
    """
    # Validate parameters
    if radius <= 0:
        raise InvalidParameterError("radius", radius, min_value=0.001, reason="Radius must be positive")
    if height <= 0:
        raise InvalidParameterError("height", height, min_value=0.001, reason="Height must be positive")

    design = _get_active_design()
    registry = get_registry()

    # Get target component
    if component_id:
        component = registry.get_component(component_id)
        if not component:
            component = design.rootComponent
    else:
        component = design.rootComponent

    # Resolve construction plane
    base_plane, created_plane = _resolve_plane(component, plane, z)

    try:
        # Create sketch on the plane
        sketches = component.sketches
        sketch = sketches.add(base_plane)

        # Convert dimensions from mm to cm
        r_cm = radius / 10.0
        h_cm = height / 10.0
        x_cm = x / 10.0
        y_cm = y / 10.0

        # Draw circle on sketch
        circles = sketch.sketchCurves.sketchCircles
        center = adsk.core.Point3D.create(x_cm, y_cm, 0)
        circle = circles.addByCenterRadius(center, r_cm)

        # Get the profile
        if sketch.profiles.count == 0:
            raise FeatureError(
                "cylinder",
                "Failed to create closed profile for extrusion",
                affected_entities=[sketch.name]
            )

        profile = sketch.profiles.item(0)

        # Create extrusion
        extrudes = component.features.extrudeFeatures
        extrude_input = extrudes.createInput(
            profile,
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        )

        # Set extrusion distance
        distance = adsk.core.ValueInput.createByReal(h_cm)
        extrude_input.setDistanceExtent(False, distance)

        # Create the extrusion
        extrude_feature = extrudes.add(extrude_input)

        if not extrude_feature:
            raise FeatureError(
                "cylinder",
                "Extrusion operation failed"
            )

        # Get the created body
        bodies = extrude_feature.bodies
        if bodies.count == 0:
            raise FeatureError(
                "cylinder",
                "No body was created by the extrusion"
            )

        body = bodies.item(0)

        # Set name if provided
        if name:
            body.name = name

        # Register entities
        body_id = registry.register_body(body)
        feature_id = registry.register_feature(extrude_feature)
        registry.register_sketch(sketch)

        # Serialize and return result
        result = _serialize_body_result(body, extrude_feature, registry)
        result["success"] = True

        return result

    except Exception as e:
        # Re-raise our custom exceptions
        if isinstance(e, (InvalidParameterError, FeatureError, DesignStateError)):
            raise

        # Wrap other exceptions
        raise FeatureError(
            "cylinder",
            f"Failed to create cylinder: {str(e)}",
            fusion_error=str(e)
        )
