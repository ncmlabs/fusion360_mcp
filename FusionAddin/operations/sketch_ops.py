"""Sketch operations for Fusion 360 MCP Add-in.

These operations create and modify sketches in Fusion 360,
returning structured results with entity IDs.
"""

from typing import Dict, Any, Optional, List
import math

# Fusion 360 API imports
try:
    import adsk.core
    import adsk.fusion
    FUSION_AVAILABLE = True
except ImportError:
    FUSION_AVAILABLE = False

from core.entity_registry import get_registry
from serializers.sketch_serializer import SketchSerializer
from shared.exceptions import (
    DesignStateError,
    FeatureError,
    InvalidParameterError,
    EntityNotFoundError,
)


def _get_active_design() -> Any:
    """Get the active Fusion 360 design."""
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
) -> Any:
    """Resolve a plane specification to a Fusion plane object.

    Args:
        component: Fusion Component object
        plane_spec: Plane specification (XY, YZ, XZ, or face_id)
        offset: Offset from the plane in mm

    Returns:
        Fusion plane or face object
    """
    plane_map = {
        "XY": component.xYConstructionPlane,
        "YZ": component.yZConstructionPlane,
        "XZ": component.xZConstructionPlane,
    }

    plane_upper = plane_spec.upper()

    if plane_upper in plane_map:
        base_plane = plane_map[plane_upper]

        if abs(offset) > 0.0001:
            planes = component.constructionPlanes
            plane_input = planes.createInput()
            offset_value = adsk.core.ValueInput.createByReal(offset / 10.0)
            plane_input.setByOffset(base_plane, offset_value)
            return planes.add(plane_input)

        return base_plane

    # Handle face_id reference
    if plane_spec.startswith("face_"):
        registry = get_registry()
        face = registry.get_sub_entity(plane_spec)
        if not face:
            raise InvalidParameterError(
                "plane",
                plane_spec,
                reason=f"Face '{plane_spec}' not found."
            )
        return face

    raise InvalidParameterError(
        "plane",
        plane_spec,
        valid_values=["XY", "YZ", "XZ", "face_<id>"]
    )


def _get_sketch(sketch_id: str) -> Any:
    """Get a sketch by ID.

    Args:
        sketch_id: Sketch ID

    Returns:
        Fusion Sketch object

    Raises:
        EntityNotFoundError: If sketch not found
    """
    design = _get_active_design()
    registry = get_registry()

    sketch = registry.get_sketch(sketch_id)

    if not sketch:
        # Try to find by name
        root = design.rootComponent
        for sk in root.sketches:
            if sk.name == sketch_id:
                sketch = sk
                registry.register_sketch(sketch)
                break

        # Search in all components
        if not sketch:
            for occurrence in root.allOccurrences:
                for sk in occurrence.component.sketches:
                    if sk.name == sketch_id:
                        sketch = sk
                        registry.register_sketch(sketch)
                        break
                if sketch:
                    break

    if not sketch:
        available = registry.get_available_sketch_ids()
        raise EntityNotFoundError("Sketch", sketch_id, available)

    return sketch


def create_sketch(
    plane: str = "XY",
    name: Optional[str] = None,
    offset: float = 0.0,
    component_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new sketch on a construction plane.

    Args:
        plane: Construction plane (XY, YZ, XZ) or face_id reference
        name: Optional name for the sketch
        offset: Offset from the plane in mm
        component_id: Optional component ID (uses root if not specified)

    Returns:
        Dict with sketch_id and sketch information

    Raises:
        InvalidParameterError: If plane is invalid
        FeatureError: If sketch creation fails
    """
    design = _get_active_design()
    registry = get_registry()

    # Get target component
    if component_id:
        component = registry.get_component(component_id)
        if not component:
            component = design.rootComponent
    else:
        component = design.rootComponent

    try:
        # Resolve construction plane
        plane_obj = _resolve_plane(component, plane, offset)

        # Create sketch
        sketches = component.sketches
        sketch = sketches.add(plane_obj)

        if not sketch:
            raise FeatureError("sketch", "Failed to create sketch")

        # Set name if provided
        if name:
            sketch.name = name

        # Register sketch
        sketch_id = registry.register_sketch(sketch)

        # Serialize result
        serializer = SketchSerializer(registry)
        sketch_data = serializer.serialize_summary(sketch)

        return {
            "success": True,
            "sketch": sketch_data,
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, FeatureError, DesignStateError)):
            raise
        raise FeatureError(
            "sketch",
            f"Failed to create sketch: {str(e)}",
            fusion_error=str(e)
        )


def draw_line(
    sketch_id: str,
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
) -> Dict[str, Any]:
    """Draw a line in a sketch.

    Args:
        sketch_id: ID of the sketch to draw in
        start_x: Start X coordinate in mm
        start_y: Start Y coordinate in mm
        end_x: End X coordinate in mm
        end_y: End Y coordinate in mm

    Returns:
        Dict with curve_id and line information

    Raises:
        EntityNotFoundError: If sketch not found
        FeatureError: If line creation fails
    """
    registry = get_registry()
    sketch = _get_sketch(sketch_id)

    try:
        # Convert mm to cm
        x1_cm = start_x / 10.0
        y1_cm = start_y / 10.0
        x2_cm = end_x / 10.0
        y2_cm = end_y / 10.0

        # Create points
        start_point = adsk.core.Point3D.create(x1_cm, y1_cm, 0)
        end_point = adsk.core.Point3D.create(x2_cm, y2_cm, 0)

        # Draw line
        lines = sketch.sketchCurves.sketchLines
        line = lines.addByTwoPoints(start_point, end_point)

        if not line:
            raise FeatureError("line", "Failed to create line")

        # Register and get ID
        curve_index = sketch.sketchCurves.count - 1
        curve_id = registry.register_sub_entity(
            sketch_id, "curve", curve_index, line
        )

        # Calculate length
        length_cm = start_point.distanceTo(end_point)
        length_mm = length_cm * 10.0

        return {
            "success": True,
            "curve": {
                "id": curve_id,
                "type": "line",
                "start_point": {"x": start_x, "y": start_y, "z": 0},
                "end_point": {"x": end_x, "y": end_y, "z": 0},
                "length": length_mm,
            },
            "sketch_id": sketch_id,
        }

    except Exception as e:
        if isinstance(e, (EntityNotFoundError, FeatureError, DesignStateError)):
            raise
        raise FeatureError(
            "line",
            f"Failed to draw line: {str(e)}",
            fusion_error=str(e)
        )


def draw_circle(
    sketch_id: str,
    center_x: float,
    center_y: float,
    radius: float,
) -> Dict[str, Any]:
    """Draw a circle in a sketch.

    Args:
        sketch_id: ID of the sketch to draw in
        center_x: Center X coordinate in mm
        center_y: Center Y coordinate in mm
        radius: Circle radius in mm

    Returns:
        Dict with curve_id and circle information

    Raises:
        InvalidParameterError: If radius is invalid
        EntityNotFoundError: If sketch not found
        FeatureError: If circle creation fails
    """
    if radius <= 0:
        raise InvalidParameterError("radius", radius, min_value=0.001)

    registry = get_registry()
    sketch = _get_sketch(sketch_id)

    try:
        # Convert mm to cm
        cx_cm = center_x / 10.0
        cy_cm = center_y / 10.0
        r_cm = radius / 10.0

        # Create center point
        center = adsk.core.Point3D.create(cx_cm, cy_cm, 0)

        # Draw circle
        circles = sketch.sketchCurves.sketchCircles
        circle = circles.addByCenterRadius(center, r_cm)

        if not circle:
            raise FeatureError("circle", "Failed to create circle")

        # Register and get ID
        curve_index = sketch.sketchCurves.count - 1
        curve_id = registry.register_sub_entity(
            sketch_id, "curve", curve_index, circle
        )

        # Calculate circumference
        circumference = 2 * math.pi * radius

        return {
            "success": True,
            "curve": {
                "id": curve_id,
                "type": "circle",
                "center": {"x": center_x, "y": center_y, "z": 0},
                "radius": radius,
                "circumference": circumference,
            },
            "sketch_id": sketch_id,
            "profiles_count": sketch.profiles.count,
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError(
            "circle",
            f"Failed to draw circle: {str(e)}",
            fusion_error=str(e)
        )


def draw_rectangle(
    sketch_id: str,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> Dict[str, Any]:
    """Draw a rectangle in a sketch using two corner points.

    Args:
        sketch_id: ID of the sketch to draw in
        x1: First corner X coordinate in mm
        y1: First corner Y coordinate in mm
        x2: Opposite corner X coordinate in mm
        y2: Opposite corner Y coordinate in mm

    Returns:
        Dict with curve_ids and rectangle information

    Raises:
        InvalidParameterError: If corners are the same
        EntityNotFoundError: If sketch not found
        FeatureError: If rectangle creation fails
    """
    if abs(x2 - x1) < 0.001 or abs(y2 - y1) < 0.001:
        raise InvalidParameterError(
            "corners",
            f"({x1},{y1}) to ({x2},{y2})",
            reason="Rectangle corners must be different"
        )

    registry = get_registry()
    sketch = _get_sketch(sketch_id)

    try:
        # Convert mm to cm
        x1_cm = x1 / 10.0
        y1_cm = y1 / 10.0
        x2_cm = x2 / 10.0
        y2_cm = y2 / 10.0

        # Create corner points
        corner1 = adsk.core.Point3D.create(x1_cm, y1_cm, 0)
        corner2 = adsk.core.Point3D.create(x2_cm, y2_cm, 0)

        # Draw rectangle
        lines = sketch.sketchCurves.sketchLines
        rect_lines = lines.addTwoPointRectangle(corner1, corner2)

        if not rect_lines or rect_lines.count == 0:
            raise FeatureError("rectangle", "Failed to create rectangle")

        # Register curves and collect IDs
        curve_ids = []
        base_index = sketch.sketchCurves.count - 4  # Rectangle creates 4 lines

        for i, line in enumerate(rect_lines):
            curve_id = registry.register_sub_entity(
                sketch_id, "curve", base_index + i, line
            )
            curve_ids.append(curve_id)

        # Calculate dimensions
        width = abs(x2 - x1)
        height = abs(y2 - y1)

        return {
            "success": True,
            "curves": curve_ids,
            "rectangle": {
                "corner1": {"x": min(x1, x2), "y": min(y1, y2), "z": 0},
                "corner2": {"x": max(x1, x2), "y": max(y1, y2), "z": 0},
                "width": width,
                "height": height,
            },
            "sketch_id": sketch_id,
            "profiles_count": sketch.profiles.count,
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError(
            "rectangle",
            f"Failed to draw rectangle: {str(e)}",
            fusion_error=str(e)
        )


def draw_arc(
    sketch_id: str,
    center_x: float,
    center_y: float,
    radius: float,
    start_angle: float,
    end_angle: float,
) -> Dict[str, Any]:
    """Draw an arc in a sketch.

    Args:
        sketch_id: ID of the sketch to draw in
        center_x: Center X coordinate in mm
        center_y: Center Y coordinate in mm
        radius: Arc radius in mm
        start_angle: Start angle in degrees (0 = positive X axis)
        end_angle: End angle in degrees (counterclockwise from start)

    Returns:
        Dict with curve_id and arc information

    Raises:
        InvalidParameterError: If parameters are invalid
        EntityNotFoundError: If sketch not found
        FeatureError: If arc creation fails
    """
    if radius <= 0:
        raise InvalidParameterError("radius", radius, min_value=0.001)

    registry = get_registry()
    sketch = _get_sketch(sketch_id)

    try:
        # Convert mm to cm
        cx_cm = center_x / 10.0
        cy_cm = center_y / 10.0
        r_cm = radius / 10.0

        # Convert angles to radians
        start_rad = math.radians(start_angle)
        end_rad = math.radians(end_angle)

        # Calculate start and end points
        start_x = cx_cm + r_cm * math.cos(start_rad)
        start_y = cy_cm + r_cm * math.sin(start_rad)
        end_x = cx_cm + r_cm * math.cos(end_rad)
        end_y = cy_cm + r_cm * math.sin(end_rad)

        # Create points
        center = adsk.core.Point3D.create(cx_cm, cy_cm, 0)
        start_point = adsk.core.Point3D.create(start_x, start_y, 0)
        end_point = adsk.core.Point3D.create(end_x, end_y, 0)

        # Draw arc
        arcs = sketch.sketchCurves.sketchArcs
        arc = arcs.addByCenterStartEnd(center, start_point, end_point)

        if not arc:
            raise FeatureError("arc", "Failed to create arc")

        # Register and get ID
        curve_index = sketch.sketchCurves.count - 1
        curve_id = registry.register_sub_entity(
            sketch_id, "curve", curve_index, arc
        )

        # Calculate arc length
        angle_span = abs(end_angle - start_angle)
        if angle_span > 360:
            angle_span = angle_span % 360
        arc_length = 2 * math.pi * radius * (angle_span / 360.0)

        return {
            "success": True,
            "curve": {
                "id": curve_id,
                "type": "arc",
                "center": {"x": center_x, "y": center_y, "z": 0},
                "radius": radius,
                "start_angle": start_angle,
                "end_angle": end_angle,
                "arc_length": arc_length,
            },
            "sketch_id": sketch_id,
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError(
            "arc",
            f"Failed to draw arc: {str(e)}",
            fusion_error=str(e)
        )
