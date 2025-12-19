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


def draw_polygon(
    sketch_id: str,
    center_x: float,
    center_y: float,
    radius: float,
    sides: int,
    rotation_angle: float = 0.0,
) -> Dict[str, Any]:
    """Draw a regular polygon in a sketch.

    Creates a regular polygon (triangle, hexagon, octagon, etc.) by calculating
    vertices on a circumscribed circle and connecting them with lines.

    Args:
        sketch_id: ID of the sketch to draw in
        center_x: Center X coordinate in mm
        center_y: Center Y coordinate in mm
        radius: Circumscribed circle radius in mm (distance from center to vertex)
        sides: Number of sides (3-64)
        rotation_angle: Rotation angle in degrees (default 0)

    Returns:
        Dict with curve_ids and polygon information

    Raises:
        InvalidParameterError: If parameters are invalid
        EntityNotFoundError: If sketch not found
        FeatureError: If polygon creation fails
    """
    if radius <= 0:
        raise InvalidParameterError("radius", radius, min_value=0.001)

    if sides < 3 or sides > 64:
        raise InvalidParameterError(
            "sides", sides,
            reason="Number of sides must be between 3 and 64"
        )

    registry = get_registry()
    sketch = _get_sketch(sketch_id)

    try:
        # Convert mm to cm
        cx_cm = center_x / 10.0
        cy_cm = center_y / 10.0
        r_cm = radius / 10.0

        # Convert rotation to radians
        rotation_rad = math.radians(rotation_angle)

        # Calculate angle between vertices
        angle_step = 2 * math.pi / sides

        # Calculate vertex positions
        vertices = []
        for i in range(sides):
            angle = rotation_rad + i * angle_step
            x = cx_cm + r_cm * math.cos(angle)
            y = cy_cm + r_cm * math.sin(angle)
            vertices.append(adsk.core.Point3D.create(x, y, 0))

        # Draw lines connecting vertices
        lines = sketch.sketchCurves.sketchLines
        curve_ids = []
        base_index = sketch.sketchCurves.count

        for i in range(sides):
            start_point = vertices[i]
            end_point = vertices[(i + 1) % sides]
            line = lines.addByTwoPoints(start_point, end_point)

            if not line:
                raise FeatureError("polygon", f"Failed to create polygon edge {i}")

            curve_id = registry.register_sub_entity(
                sketch_id, "curve", base_index + i, line
            )
            curve_ids.append(curve_id)

        # Calculate polygon properties
        # Apothem (distance from center to middle of side)
        apothem = radius * math.cos(math.pi / sides)
        # Side length
        side_length = 2 * radius * math.sin(math.pi / sides)
        # Perimeter
        perimeter = sides * side_length
        # Area
        area = 0.5 * perimeter * apothem

        return {
            "success": True,
            "curves": curve_ids,
            "polygon": {
                "center": {"x": center_x, "y": center_y, "z": 0},
                "radius": radius,
                "sides": sides,
                "rotation_angle": rotation_angle,
                "side_length": side_length,
                "apothem": apothem,
                "perimeter": perimeter,
                "area": area,
            },
            "sketch_id": sketch_id,
            "profiles_count": sketch.profiles.count,
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError(
            "polygon",
            f"Failed to draw polygon: {str(e)}",
            fusion_error=str(e)
        )


def draw_ellipse(
    sketch_id: str,
    center_x: float,
    center_y: float,
    major_radius: float,
    minor_radius: float,
    rotation_angle: float = 0.0,
) -> Dict[str, Any]:
    """Draw an ellipse in a sketch.

    Creates an ellipse with specified major and minor radii, optionally rotated.

    Args:
        sketch_id: ID of the sketch to draw in
        center_x: Center X coordinate in mm
        center_y: Center Y coordinate in mm
        major_radius: Major axis radius in mm (longest radius)
        minor_radius: Minor axis radius in mm (shortest radius)
        rotation_angle: Rotation of major axis in degrees (default 0)

    Returns:
        Dict with curve_id and ellipse information

    Raises:
        InvalidParameterError: If parameters are invalid
        EntityNotFoundError: If sketch not found
        FeatureError: If ellipse creation fails
    """
    if major_radius <= 0:
        raise InvalidParameterError("major_radius", major_radius, min_value=0.001)

    if minor_radius <= 0:
        raise InvalidParameterError("minor_radius", minor_radius, min_value=0.001)

    if minor_radius > major_radius:
        raise InvalidParameterError(
            "minor_radius", minor_radius,
            reason="Minor radius cannot be larger than major radius. Swap values if needed."
        )

    registry = get_registry()
    sketch = _get_sketch(sketch_id)

    try:
        # Convert mm to cm
        cx_cm = center_x / 10.0
        cy_cm = center_y / 10.0
        major_cm = major_radius / 10.0
        minor_cm = minor_radius / 10.0

        # Convert rotation to radians
        rotation_rad = math.radians(rotation_angle)

        # Create center point
        center = adsk.core.Point3D.create(cx_cm, cy_cm, 0)

        # Calculate major axis endpoint (point on the ellipse along major axis)
        major_x = cx_cm + major_cm * math.cos(rotation_rad)
        major_y = cy_cm + major_cm * math.sin(rotation_rad)
        major_point = adsk.core.Point3D.create(major_x, major_y, 0)

        # Calculate minor axis endpoint (point on the ellipse along minor axis)
        # Minor axis is perpendicular to major axis
        minor_x = cx_cm + minor_cm * math.cos(rotation_rad + math.pi / 2)
        minor_y = cy_cm + minor_cm * math.sin(rotation_rad + math.pi / 2)
        minor_point = adsk.core.Point3D.create(minor_x, minor_y, 0)

        # Draw ellipse
        ellipses = sketch.sketchCurves.sketchEllipses
        ellipse = ellipses.add(center, major_point, minor_point)

        if not ellipse:
            raise FeatureError("ellipse", "Failed to create ellipse")

        # Register and get ID
        curve_index = sketch.sketchCurves.count - 1
        curve_id = registry.register_sub_entity(
            sketch_id, "curve", curve_index, ellipse
        )

        # Calculate approximate perimeter (Ramanujan approximation)
        h = ((major_radius - minor_radius) ** 2) / ((major_radius + minor_radius) ** 2)
        perimeter = math.pi * (major_radius + minor_radius) * (1 + (3 * h) / (10 + math.sqrt(4 - 3 * h)))

        # Calculate area
        area = math.pi * major_radius * minor_radius

        return {
            "success": True,
            "curve": {
                "id": curve_id,
                "type": "ellipse",
                "center": {"x": center_x, "y": center_y, "z": 0},
                "major_radius": major_radius,
                "minor_radius": minor_radius,
                "rotation_angle": rotation_angle,
                "perimeter": perimeter,
                "area": area,
            },
            "sketch_id": sketch_id,
            "profiles_count": sketch.profiles.count,
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError(
            "ellipse",
            f"Failed to draw ellipse: {str(e)}",
            fusion_error=str(e)
        )


def draw_slot(
    sketch_id: str,
    center_x: float,
    center_y: float,
    length: float,
    width: float,
    slot_type: str = "overall",
    rotation_angle: float = 0.0,
) -> Dict[str, Any]:
    """Draw a slot shape (rounded rectangle/oblong) in a sketch.

    Creates a slot by drawing two parallel lines connected by two semicircular arcs.

    Args:
        sketch_id: ID of the sketch to draw in
        center_x: Center X coordinate in mm
        center_y: Center Y coordinate in mm
        length: Slot length in mm (see slot_type for interpretation)
        width: Slot width in mm (diameter of rounded ends)
        slot_type: Length interpretation:
            - "overall": length is total slot length (default)
            - "center_to_center": length is distance between arc centers
        rotation_angle: Rotation angle in degrees (default 0)

    Returns:
        Dict with curve_ids and slot information

    Raises:
        InvalidParameterError: If parameters are invalid
        EntityNotFoundError: If sketch not found
        FeatureError: If slot creation fails
    """
    if length <= 0:
        raise InvalidParameterError("length", length, min_value=0.001)

    if width <= 0:
        raise InvalidParameterError("width", width, min_value=0.001)

    if slot_type not in ["overall", "center_to_center"]:
        raise InvalidParameterError(
            "slot_type", slot_type,
            valid_values=["overall", "center_to_center"]
        )

    # Calculate center-to-center distance
    radius = width / 2.0
    if slot_type == "overall":
        if length < width:
            raise InvalidParameterError(
                "length", length,
                reason=f"Overall length ({length}) must be >= width ({width})"
            )
        center_distance = length - width
    else:
        center_distance = length

    # For very short slots (essentially a circle), just draw a circle
    if center_distance < 0.001:
        return draw_circle(sketch_id, center_x, center_y, radius)

    registry = get_registry()
    sketch = _get_sketch(sketch_id)

    try:
        # Convert mm to cm
        cx_cm = center_x / 10.0
        cy_cm = center_y / 10.0
        r_cm = radius / 10.0
        half_dist_cm = (center_distance / 2.0) / 10.0

        # Convert rotation to radians
        rotation_rad = math.radians(rotation_angle)
        cos_a = math.cos(rotation_rad)
        sin_a = math.sin(rotation_rad)

        # Calculate arc centers (along the slot axis)
        arc1_cx = cx_cm - half_dist_cm * cos_a
        arc1_cy = cy_cm - half_dist_cm * sin_a
        arc2_cx = cx_cm + half_dist_cm * cos_a
        arc2_cy = cy_cm + half_dist_cm * sin_a

        # Perpendicular direction (for line endpoints)
        perp_cos = math.cos(rotation_rad + math.pi / 2)
        perp_sin = math.sin(rotation_rad + math.pi / 2)

        # Calculate the four corner points
        # Top-left (arc1, +perpendicular)
        p1 = adsk.core.Point3D.create(
            arc1_cx + r_cm * perp_cos,
            arc1_cy + r_cm * perp_sin,
            0
        )
        # Top-right (arc2, +perpendicular)
        p2 = adsk.core.Point3D.create(
            arc2_cx + r_cm * perp_cos,
            arc2_cy + r_cm * perp_sin,
            0
        )
        # Bottom-right (arc2, -perpendicular)
        p3 = adsk.core.Point3D.create(
            arc2_cx - r_cm * perp_cos,
            arc2_cy - r_cm * perp_sin,
            0
        )
        # Bottom-left (arc1, -perpendicular)
        p4 = adsk.core.Point3D.create(
            arc1_cx - r_cm * perp_cos,
            arc1_cy - r_cm * perp_sin,
            0
        )

        # Arc centers
        arc1_center = adsk.core.Point3D.create(arc1_cx, arc1_cy, 0)
        arc2_center = adsk.core.Point3D.create(arc2_cx, arc2_cy, 0)

        curve_ids = []
        base_index = sketch.sketchCurves.count

        # Draw top line (p1 to p2)
        lines = sketch.sketchCurves.sketchLines
        line1 = lines.addByTwoPoints(p1, p2)
        if not line1:
            raise FeatureError("slot", "Failed to create slot top line")

        # Draw right arc (from p2 to p3, around arc2_center)
        arcs = sketch.sketchCurves.sketchArcs
        arc1 = arcs.addByCenterStartEnd(arc2_center, p2, p3)
        if not arc1:
            raise FeatureError("slot", "Failed to create slot right arc")

        # Draw bottom line (p3 to p4)
        line2 = lines.addByTwoPoints(p3, p4)
        if not line2:
            raise FeatureError("slot", "Failed to create slot bottom line")

        # Draw left arc (from p4 to p1, around arc1_center)
        arc2 = arcs.addByCenterStartEnd(arc1_center, p4, p1)
        if not arc2:
            raise FeatureError("slot", "Failed to create slot left arc")

        # Register all curves
        for i, curve in enumerate([line1, arc1, line2, arc2]):
            curve_id = registry.register_sub_entity(
                sketch_id, "curve", base_index + i, curve
            )
            curve_ids.append(curve_id)

        # Calculate slot properties
        overall_length = center_distance + width
        perimeter = 2 * center_distance + math.pi * width
        area = center_distance * width + math.pi * radius * radius

        return {
            "success": True,
            "curves": curve_ids,
            "slot": {
                "center": {"x": center_x, "y": center_y, "z": 0},
                "overall_length": overall_length,
                "center_to_center": center_distance,
                "width": width,
                "rotation_angle": rotation_angle,
                "perimeter": perimeter,
                "area": area,
            },
            "sketch_id": sketch_id,
            "profiles_count": sketch.profiles.count,
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError(
            "slot",
            f"Failed to draw slot: {str(e)}",
            fusion_error=str(e)
        )


def draw_spline(
    sketch_id: str,
    points: List[Dict[str, float]],
    is_closed: bool = False,
) -> Dict[str, Any]:
    """Draw a spline (smooth curve) through control points in a sketch.

    Creates a fitted spline that passes through all specified points,
    creating a smooth curve.

    Args:
        sketch_id: ID of the sketch to draw in
        points: List of point dicts with 'x' and 'y' coordinates in mm.
                Must have at least 2 points (3 for closed spline).
                Example: [{"x": 0, "y": 0}, {"x": 10, "y": 5}, {"x": 20, "y": 0}]
        is_closed: If True, create a closed spline loop (default False)

    Returns:
        Dict with curve_id and spline information

    Raises:
        InvalidParameterError: If parameters are invalid
        EntityNotFoundError: If sketch not found
        FeatureError: If spline creation fails
    """
    min_points = 3 if is_closed else 2

    if not points or len(points) < min_points:
        raise InvalidParameterError(
            "points", f"{len(points) if points else 0} points",
            reason=f"Spline requires at least {min_points} points"
        )

    # Validate point format
    for i, pt in enumerate(points):
        if not isinstance(pt, dict) or "x" not in pt or "y" not in pt:
            raise InvalidParameterError(
                "points", str(pt),
                reason=f"Point {i} must have 'x' and 'y' coordinates"
            )

    registry = get_registry()
    sketch = _get_sketch(sketch_id)

    try:
        # Create ObjectCollection of Point3D objects
        point_collection = adsk.core.ObjectCollection.create()

        for pt in points:
            # Convert mm to cm
            x_cm = pt["x"] / 10.0
            y_cm = pt["y"] / 10.0
            point_collection.add(adsk.core.Point3D.create(x_cm, y_cm, 0))

        # Draw spline
        splines = sketch.sketchCurves.sketchFittedSplines
        if is_closed:
            spline = splines.addByInterpolation(point_collection, True)
        else:
            spline = splines.add(point_collection)

        if not spline:
            raise FeatureError("spline", "Failed to create spline")

        # Register and get ID
        curve_index = sketch.sketchCurves.count - 1
        curve_id = registry.register_sub_entity(
            sketch_id, "curve", curve_index, spline
        )

        # Return point list in mm for response
        points_mm = [{"x": pt["x"], "y": pt["y"], "z": 0} for pt in points]

        return {
            "success": True,
            "curve": {
                "id": curve_id,
                "type": "spline",
                "points": points_mm,
                "point_count": len(points),
                "is_closed": is_closed,
            },
            "sketch_id": sketch_id,
            "profiles_count": sketch.profiles.count if is_closed else 0,
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError(
            "spline",
            f"Failed to draw spline: {str(e)}",
            fusion_error=str(e)
        )


def draw_point(
    sketch_id: str,
    x: float,
    y: float,
    is_construction: bool = False,
) -> Dict[str, Any]:
    """Draw a point in a sketch.

    Creates a sketch point that can be used as a reference for dimensions,
    constraints, or construction geometry.

    Args:
        sketch_id: ID of the sketch to draw in
        x: X coordinate in mm
        y: Y coordinate in mm
        is_construction: If True, mark as construction geometry (default False)

    Returns:
        Dict with point_id and point information

    Raises:
        EntityNotFoundError: If sketch not found
        FeatureError: If point creation fails
    """
    registry = get_registry()
    sketch = _get_sketch(sketch_id)

    try:
        # Convert mm to cm
        x_cm = x / 10.0
        y_cm = y / 10.0

        # Create point
        point_3d = adsk.core.Point3D.create(x_cm, y_cm, 0)
        sketch_point = sketch.sketchPoints.add(point_3d)

        if not sketch_point:
            raise FeatureError("point", "Failed to create point")

        # Set construction mode if requested
        if is_construction:
            sketch_point.isConstruction = True

        # Register and get ID
        point_index = sketch.sketchPoints.count - 1
        point_id = registry.register_sub_entity(
            sketch_id, "point", point_index, sketch_point
        )

        return {
            "success": True,
            "point": {
                "id": point_id,
                "position": {"x": x, "y": y, "z": 0},
                "is_construction": is_construction,
            },
            "sketch_id": sketch_id,
        }

    except Exception as e:
        if isinstance(e, (EntityNotFoundError, FeatureError, DesignStateError)):
            raise
        raise FeatureError(
            "point",
            f"Failed to draw point: {str(e)}",
            fusion_error=str(e)
        )
