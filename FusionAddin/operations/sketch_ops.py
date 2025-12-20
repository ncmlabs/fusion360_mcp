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
        spline = splines.add(point_collection)

        if not spline:
            raise FeatureError("spline", "Failed to create spline")

        # Close the spline if requested
        if is_closed:
            spline.isClosed = True
            # Force profile recalculation
            sketch.isComputeDeferred = True
            sketch.isComputeDeferred = False

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


# --- Phase 7b: Sketch Patterns & Operations ---


def _get_curve(sketch: Any, curve_id: str, registry: Any) -> Any:
    """Get a sketch curve by ID.

    Args:
        sketch: Fusion Sketch object
        curve_id: Curve ID
        registry: Entity registry

    Returns:
        Fusion SketchCurve object

    Raises:
        EntityNotFoundError: If curve not found
    """
    curve = registry.get_sub_entity(curve_id)

    if not curve:
        # Try to find by index from the curve_id
        # curve_id format: "sketch_id_curve_N"
        parts = curve_id.split("_curve_")
        if len(parts) == 2:
            try:
                curve_index = int(parts[1])
                if curve_index < sketch.sketchCurves.count:
                    curve = sketch.sketchCurves.item(curve_index)
            except ValueError:
                pass

    if not curve:
        raise EntityNotFoundError("Curve", curve_id, [])

    return curve


def sketch_mirror(
    sketch_id: str,
    curve_ids: List[str],
    mirror_line_id: str,
) -> Dict[str, Any]:
    """Mirror sketch entities across a line.

    Creates mirrored copies of the specified curves, maintaining
    symmetry constraints with the mirror line.

    Args:
        sketch_id: ID of the sketch
        curve_ids: List of curve IDs to mirror
        mirror_line_id: ID of the line to mirror across

    Returns:
        Dict with mirrored curve IDs and information

    Raises:
        EntityNotFoundError: If sketch, curves, or mirror line not found
        FeatureError: If mirror operation fails
    """
    if not curve_ids:
        raise InvalidParameterError(
            "curve_ids", "empty list",
            reason="At least one curve ID is required"
        )

    registry = get_registry()
    sketch = _get_sketch(sketch_id)

    try:
        # Get mirror line
        mirror_line = _get_curve(sketch, mirror_line_id, registry)

        if not hasattr(mirror_line, "startSketchPoint"):
            raise InvalidParameterError(
                "mirror_line_id", mirror_line_id,
                reason="Mirror line must be a SketchLine"
            )

        # Collect curves to mirror
        curves_to_mirror = adsk.core.ObjectCollection.create()
        for curve_id in curve_ids:
            curve = _get_curve(sketch, curve_id, registry)
            curves_to_mirror.add(curve)

        # Get mirror line geometry
        line_start = mirror_line.startSketchPoint.geometry
        line_end = mirror_line.endSketchPoint.geometry

        # Create mirrored copies manually using transformation
        # Calculate mirror transformation matrix
        # Mirror across line from line_start to line_end
        dx = line_end.x - line_start.x
        dy = line_end.y - line_start.y
        line_length = math.sqrt(dx * dx + dy * dy)

        if line_length < 0.0001:
            raise FeatureError(
                "mirror",
                "Mirror line is too short",
            )

        # Normalize direction vector
        nx = dx / line_length
        ny = dy / line_length

        # Mirror transformation: P' = 2 * (P . n) * n - P
        # For a line through origin with unit normal (nx, ny)
        # Reflection matrix: [[nx*nx - ny*ny, 2*nx*ny], [2*nx*ny, ny*ny - nx*nx]]

        mirrored_curve_ids = []
        base_index = sketch.sketchCurves.count

        for i, curve_id in enumerate(curve_ids):
            curve = _get_curve(sketch, curve_id, registry)

            # Mirror based on curve type
            if hasattr(curve, "startSketchPoint") and hasattr(curve, "endSketchPoint"):
                # Line or arc
                start_pt = curve.startSketchPoint.geometry
                end_pt = curve.endSketchPoint.geometry

                # Transform points across mirror line
                new_start = _mirror_point(start_pt, line_start, nx, ny)
                new_end = _mirror_point(end_pt, line_start, nx, ny)

                if hasattr(curve, "centerSketchPoint"):
                    # Arc
                    center_pt = curve.centerSketchPoint.geometry
                    new_center = _mirror_point(center_pt, line_start, nx, ny)

                    arcs = sketch.sketchCurves.sketchArcs
                    new_arc = arcs.addByCenterStartEnd(new_center, new_end, new_start)

                    if new_arc:
                        mirrored_id = registry.register_sub_entity(
                            sketch_id, "curve", base_index + len(mirrored_curve_ids), new_arc
                        )
                        mirrored_curve_ids.append(mirrored_id)
                else:
                    # Line
                    lines = sketch.sketchCurves.sketchLines
                    new_line = lines.addByTwoPoints(new_start, new_end)

                    if new_line:
                        mirrored_id = registry.register_sub_entity(
                            sketch_id, "curve", base_index + len(mirrored_curve_ids), new_line
                        )
                        mirrored_curve_ids.append(mirrored_id)

            elif hasattr(curve, "centerSketchPoint") and hasattr(curve, "radius"):
                # Circle
                center_pt = curve.centerSketchPoint.geometry
                radius = curve.radius
                new_center = _mirror_point(center_pt, line_start, nx, ny)

                circles = sketch.sketchCurves.sketchCircles
                new_circle = circles.addByCenterRadius(new_center, radius)

                if new_circle:
                    mirrored_id = registry.register_sub_entity(
                        sketch_id, "curve", base_index + len(mirrored_curve_ids), new_circle
                    )
                    mirrored_curve_ids.append(mirrored_id)

        return {
            "success": True,
            "mirrored_curves": mirrored_curve_ids,
            "original_curves": curve_ids,
            "mirror_line_id": mirror_line_id,
            "sketch_id": sketch_id,
            "profiles_count": sketch.profiles.count,
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError(
            "mirror",
            f"Failed to mirror curves: {str(e)}",
            fusion_error=str(e)
        )


def _mirror_point(
    point: Any,
    line_point: Any,
    nx: float,
    ny: float,
) -> Any:
    """Mirror a point across a line.

    Args:
        point: Point to mirror
        line_point: A point on the mirror line
        nx: Normalized X direction of mirror line
        ny: Normalized Y direction of mirror line

    Returns:
        Mirrored Point3D
    """
    # Translate point relative to line
    px = point.x - line_point.x
    py = point.y - line_point.y

    # Reflect across line through origin
    # P' = 2 * (P . n) * n - P
    # Where n is the line direction (nx, ny)
    dot = px * nx + py * ny
    rx = 2 * dot * nx - px
    ry = 2 * dot * ny - py

    # Translate back
    return adsk.core.Point3D.create(
        rx + line_point.x,
        ry + line_point.y,
        point.z
    )


def sketch_circular_pattern(
    sketch_id: str,
    curve_ids: List[str],
    center_x: float,
    center_y: float,
    count: int,
    total_angle: float = 360.0,
) -> Dict[str, Any]:
    """Create a circular pattern of sketch entities.

    Copies the specified curves in a circular array around a center point.

    Args:
        sketch_id: ID of the sketch
        curve_ids: List of curve IDs to pattern
        center_x: Pattern center X coordinate in mm
        center_y: Pattern center Y coordinate in mm
        count: Number of instances (including original)
        total_angle: Total angle span in degrees (default 360)

    Returns:
        Dict with pattern information and new curve IDs

    Raises:
        InvalidParameterError: If parameters are invalid
        EntityNotFoundError: If sketch or curves not found
        FeatureError: If pattern operation fails
    """
    if not curve_ids:
        raise InvalidParameterError(
            "curve_ids", "empty list",
            reason="At least one curve ID is required"
        )

    if count < 2:
        raise InvalidParameterError(
            "count", count,
            reason="Count must be at least 2"
        )

    if count > 360:
        raise InvalidParameterError(
            "count", count,
            reason="Count cannot exceed 360"
        )

    registry = get_registry()
    sketch = _get_sketch(sketch_id)

    try:
        # Convert mm to cm
        cx_cm = center_x / 10.0
        cy_cm = center_y / 10.0

        # Calculate angle step
        angle_step = math.radians(total_angle) / count

        all_pattern_curve_ids = []
        base_index = sketch.sketchCurves.count

        # Create copies for each instance (skip first - it's the original)
        for instance in range(1, count):
            angle = instance * angle_step

            cos_a = math.cos(angle)
            sin_a = math.sin(angle)

            for curve_id in curve_ids:
                curve = _get_curve(sketch, curve_id, registry)

                # Pattern based on curve type
                if hasattr(curve, "startSketchPoint") and hasattr(curve, "endSketchPoint"):
                    # Line or arc
                    start_pt = curve.startSketchPoint.geometry
                    end_pt = curve.endSketchPoint.geometry

                    new_start = _rotate_point(start_pt, cx_cm, cy_cm, cos_a, sin_a)
                    new_end = _rotate_point(end_pt, cx_cm, cy_cm, cos_a, sin_a)

                    if hasattr(curve, "centerSketchPoint"):
                        # Arc
                        center_pt = curve.centerSketchPoint.geometry
                        new_center = _rotate_point(center_pt, cx_cm, cy_cm, cos_a, sin_a)

                        arcs = sketch.sketchCurves.sketchArcs
                        new_arc = arcs.addByCenterStartEnd(new_center, new_start, new_end)

                        if new_arc:
                            new_id = registry.register_sub_entity(
                                sketch_id, "curve", base_index + len(all_pattern_curve_ids), new_arc
                            )
                            all_pattern_curve_ids.append(new_id)
                    else:
                        # Line
                        lines = sketch.sketchCurves.sketchLines
                        new_line = lines.addByTwoPoints(new_start, new_end)

                        if new_line:
                            new_id = registry.register_sub_entity(
                                sketch_id, "curve", base_index + len(all_pattern_curve_ids), new_line
                            )
                            all_pattern_curve_ids.append(new_id)

                elif hasattr(curve, "centerSketchPoint") and hasattr(curve, "radius"):
                    # Circle
                    center_pt = curve.centerSketchPoint.geometry
                    radius = curve.radius
                    new_center = _rotate_point(center_pt, cx_cm, cy_cm, cos_a, sin_a)

                    circles = sketch.sketchCurves.sketchCircles
                    new_circle = circles.addByCenterRadius(new_center, radius)

                    if new_circle:
                        new_id = registry.register_sub_entity(
                            sketch_id, "curve", base_index + len(all_pattern_curve_ids), new_circle
                        )
                        all_pattern_curve_ids.append(new_id)

        return {
            "success": True,
            "pattern_curves": all_pattern_curve_ids,
            "original_curves": curve_ids,
            "pattern": {
                "type": "circular",
                "center": {"x": center_x, "y": center_y, "z": 0},
                "count": count,
                "total_angle": total_angle,
                "angle_step": total_angle / count,
            },
            "sketch_id": sketch_id,
            "profiles_count": sketch.profiles.count,
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError(
            "circular_pattern",
            f"Failed to create circular pattern: {str(e)}",
            fusion_error=str(e)
        )


def _rotate_point(
    point: Any,
    cx: float,
    cy: float,
    cos_a: float,
    sin_a: float,
) -> Any:
    """Rotate a point around a center.

    Args:
        point: Point to rotate
        cx: Center X in cm
        cy: Center Y in cm
        cos_a: Cosine of rotation angle
        sin_a: Sine of rotation angle

    Returns:
        Rotated Point3D
    """
    # Translate to origin
    px = point.x - cx
    py = point.y - cy

    # Rotate
    rx = px * cos_a - py * sin_a
    ry = px * sin_a + py * cos_a

    # Translate back
    return adsk.core.Point3D.create(rx + cx, ry + cy, point.z)


def sketch_rectangular_pattern(
    sketch_id: str,
    curve_ids: List[str],
    x_count: int,
    y_count: int,
    x_spacing: float,
    y_spacing: float,
) -> Dict[str, Any]:
    """Create a rectangular pattern of sketch entities.

    Copies the specified curves in a rectangular grid array.

    Args:
        sketch_id: ID of the sketch
        curve_ids: List of curve IDs to pattern
        x_count: Number of columns
        y_count: Number of rows
        x_spacing: Column spacing in mm
        y_spacing: Row spacing in mm

    Returns:
        Dict with pattern information and new curve IDs

    Raises:
        InvalidParameterError: If parameters are invalid
        EntityNotFoundError: If sketch or curves not found
        FeatureError: If pattern operation fails
    """
    if not curve_ids:
        raise InvalidParameterError(
            "curve_ids", "empty list",
            reason="At least one curve ID is required"
        )

    if x_count < 1 or y_count < 1:
        raise InvalidParameterError(
            "count", f"x={x_count}, y={y_count}",
            reason="Both x_count and y_count must be at least 1"
        )

    if x_count * y_count > 1000:
        raise InvalidParameterError(
            "count", x_count * y_count,
            reason="Total pattern count cannot exceed 1000"
        )

    registry = get_registry()
    sketch = _get_sketch(sketch_id)

    try:
        # Convert mm to cm
        x_spacing_cm = x_spacing / 10.0
        y_spacing_cm = y_spacing / 10.0

        all_pattern_curve_ids = []
        base_index = sketch.sketchCurves.count

        # Create copies for each grid position (skip 0,0 - it's the original)
        for row in range(y_count):
            for col in range(x_count):
                if row == 0 and col == 0:
                    continue  # Skip original position

                dx = col * x_spacing_cm
                dy = row * y_spacing_cm

                for curve_id in curve_ids:
                    curve = _get_curve(sketch, curve_id, registry)

                    # Pattern based on curve type
                    if hasattr(curve, "startSketchPoint") and hasattr(curve, "endSketchPoint"):
                        # Line or arc
                        start_pt = curve.startSketchPoint.geometry
                        end_pt = curve.endSketchPoint.geometry

                        new_start = _translate_point(start_pt, dx, dy)
                        new_end = _translate_point(end_pt, dx, dy)

                        if hasattr(curve, "centerSketchPoint"):
                            # Arc
                            center_pt = curve.centerSketchPoint.geometry
                            new_center = _translate_point(center_pt, dx, dy)

                            arcs = sketch.sketchCurves.sketchArcs
                            new_arc = arcs.addByCenterStartEnd(new_center, new_start, new_end)

                            if new_arc:
                                new_id = registry.register_sub_entity(
                                    sketch_id, "curve", base_index + len(all_pattern_curve_ids), new_arc
                                )
                                all_pattern_curve_ids.append(new_id)
                        else:
                            # Line
                            lines = sketch.sketchCurves.sketchLines
                            new_line = lines.addByTwoPoints(new_start, new_end)

                            if new_line:
                                new_id = registry.register_sub_entity(
                                    sketch_id, "curve", base_index + len(all_pattern_curve_ids), new_line
                                )
                                all_pattern_curve_ids.append(new_id)

                    elif hasattr(curve, "centerSketchPoint") and hasattr(curve, "radius"):
                        # Circle
                        center_pt = curve.centerSketchPoint.geometry
                        radius = curve.radius
                        new_center = _translate_point(center_pt, dx, dy)

                        circles = sketch.sketchCurves.sketchCircles
                        new_circle = circles.addByCenterRadius(new_center, radius)

                        if new_circle:
                            new_id = registry.register_sub_entity(
                                sketch_id, "curve", base_index + len(all_pattern_curve_ids), new_circle
                            )
                            all_pattern_curve_ids.append(new_id)

        return {
            "success": True,
            "pattern_curves": all_pattern_curve_ids,
            "original_curves": curve_ids,
            "pattern": {
                "type": "rectangular",
                "x_count": x_count,
                "y_count": y_count,
                "x_spacing": x_spacing,
                "y_spacing": y_spacing,
                "total_instances": x_count * y_count,
            },
            "sketch_id": sketch_id,
            "profiles_count": sketch.profiles.count,
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError(
            "rectangular_pattern",
            f"Failed to create rectangular pattern: {str(e)}",
            fusion_error=str(e)
        )


def _translate_point(point: Any, dx: float, dy: float) -> Any:
    """Translate a point by dx, dy.

    Args:
        point: Point to translate
        dx: X translation in cm
        dy: Y translation in cm

    Returns:
        Translated Point3D
    """
    return adsk.core.Point3D.create(point.x + dx, point.y + dy, point.z)


def project_geometry(
    sketch_id: str,
    entity_ids: List[str],
    project_type: str = "standard",
) -> Dict[str, Any]:
    """Project edges or faces from 3D bodies onto a sketch.

    Projects existing 3D geometry (edges, faces) onto the sketch plane,
    creating reference curves that can be used for further sketch operations.

    Args:
        sketch_id: ID of the target sketch
        entity_ids: List of entity IDs to project (edges, faces, or bodies)
        project_type: Projection type:
            - "standard": Regular projection (default)
            - "cut_edges": Project only edges that intersect sketch plane

    Returns:
        Dict with projected curve IDs and information

    Raises:
        InvalidParameterError: If parameters are invalid
        EntityNotFoundError: If sketch or entities not found
        FeatureError: If projection fails
    """
    if not entity_ids:
        raise InvalidParameterError(
            "entity_ids", "empty list",
            reason="At least one entity ID is required"
        )

    if project_type not in ["standard", "cut_edges"]:
        raise InvalidParameterError(
            "project_type", project_type,
            valid_values=["standard", "cut_edges"]
        )

    registry = get_registry()
    sketch = _get_sketch(sketch_id)

    try:
        projected_curve_ids = []
        base_index = sketch.sketchCurves.count

        for entity_id in entity_ids:
            # Get the entity
            entity = registry.get_sub_entity(entity_id)

            if not entity:
                # Try to find body
                entity = registry.get_body(entity_id)

            if not entity:
                raise EntityNotFoundError("Entity", entity_id, [])

            # Project based on type
            if project_type == "cut_edges":
                # Use projectCutEdges for bodies/faces that intersect sketch plane
                curves = sketch.projectCutEdges(entity)
            else:
                # Standard projection
                curves = sketch.project(entity)

            if curves:
                # Register projected curves
                for j in range(curves.count):
                    curve = curves.item(j)
                    curve_id = registry.register_sub_entity(
                        sketch_id, "curve", base_index + len(projected_curve_ids), curve
                    )
                    projected_curve_ids.append(curve_id)

        return {
            "success": True,
            "projected_curves": projected_curve_ids,
            "source_entities": entity_ids,
            "project_type": project_type,
            "sketch_id": sketch_id,
            "curves_created": len(projected_curve_ids),
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError(
            "project_geometry",
            f"Failed to project geometry: {str(e)}",
            fusion_error=str(e)
        )


def add_sketch_text(
    sketch_id: str,
    text: str,
    x: float,
    y: float,
    height: float,
    font_name: Optional[str] = None,
    is_bold: bool = False,
    is_italic: bool = False,
) -> Dict[str, Any]:
    """Add text to a sketch for engraving or embossing.

    Creates sketch text that generates profiles suitable for extrusion,
    enabling engraved or embossed text on parts.

    Args:
        sketch_id: ID of the target sketch
        text: Text content to add
        x: Text position X coordinate in mm
        y: Text position Y coordinate in mm
        height: Text height in mm
        font_name: Optional font name (uses system default if not specified)
        is_bold: Make text bold (default False)
        is_italic: Make text italic (default False)

    Returns:
        Dict with text curve IDs and information

    Raises:
        InvalidParameterError: If parameters are invalid
        EntityNotFoundError: If sketch not found
        FeatureError: If text creation fails
    """
    if not text or not text.strip():
        raise InvalidParameterError(
            "text", text,
            reason="Text content cannot be empty"
        )

    if height <= 0:
        raise InvalidParameterError(
            "height", height,
            reason="Text height must be positive"
        )

    registry = get_registry()
    sketch = _get_sketch(sketch_id)

    try:
        # Convert mm to cm
        x_cm = x / 10.0
        y_cm = y / 10.0
        height_cm = height / 10.0

        # Create corner point
        corner_point = adsk.core.Point3D.create(x_cm, y_cm, 0)

        # Create text input
        texts = sketch.sketchTexts
        text_input = texts.createInput2(text, height_cm)

        # Set position using multi-line mode with a bounding box
        # Create a second corner point for the text box (width based on text length estimate)
        estimated_width = len(text) * height_cm * 0.6  # Rough estimate
        corner_point2 = adsk.core.Point3D.create(x_cm + estimated_width, y_cm - height_cm * 1.5, 0)

        text_input.setAsMultiLine(
            corner_point,
            corner_point2,
            adsk.core.HorizontalAlignments.LeftHorizontalAlignment,
            adsk.core.VerticalAlignments.TopVerticalAlignment,
            0.0  # No rotation
        )

        # Set font if specified
        if font_name:
            text_input.fontName = font_name

        # Set style
        text_input.isBold = is_bold
        text_input.isItalic = is_italic

        # Add text to sketch
        sketch_text = texts.add(text_input)

        if not sketch_text:
            raise FeatureError("text", "Failed to create sketch text")

        # Get curves created by text
        text_curve_ids = []
        curves_before = sketch.sketchCurves.count
        # Text creates curves, register them
        # Note: curves are created as part of the text entity
        for i in range(curves_before, sketch.sketchCurves.count):
            curve = sketch.sketchCurves.item(i)
            curve_id = registry.register_sub_entity(
                sketch_id, "curve", i, curve
            )
            text_curve_ids.append(curve_id)

        return {
            "success": True,
            "text": {
                "content": text,
                "position": {"x": x, "y": y, "z": 0},
                "height": height,
                "font_name": font_name or "Default",
                "is_bold": is_bold,
                "is_italic": is_italic,
            },
            "curves": text_curve_ids,
            "sketch_id": sketch_id,
            "profiles_count": sketch.profiles.count,
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError(
            "text",
            f"Failed to add sketch text: {str(e)}",
            fusion_error=str(e)
        )


# --- Phase 7c: Sketch Constraints & Dimensions ---


def _get_sketch_entity(sketch: Any, entity_id: str, registry: Any) -> Any:
    """Get a sketch entity (curve or point) by ID.

    Args:
        sketch: Fusion Sketch object
        entity_id: Entity ID (curve_N or point_N format)
        registry: Entity registry

    Returns:
        Fusion sketch entity (SketchCurve, SketchPoint, etc.)

    Raises:
        EntityNotFoundError: If entity not found
    """
    entity = registry.get_sub_entity(entity_id)

    if not entity:
        # Try to find by index from the entity_id
        if "_curve_" in entity_id:
            parts = entity_id.split("_curve_")
            if len(parts) == 2:
                try:
                    curve_index = int(parts[1])
                    if curve_index < sketch.sketchCurves.count:
                        entity = sketch.sketchCurves.item(curve_index)
                except ValueError:
                    pass
        elif "_point_" in entity_id:
            parts = entity_id.split("_point_")
            if len(parts) == 2:
                try:
                    point_index = int(parts[1])
                    if point_index < sketch.sketchPoints.count:
                        entity = sketch.sketchPoints.item(point_index)
                except ValueError:
                    pass

    if not entity:
        raise EntityNotFoundError("SketchEntity", entity_id, [])

    return entity


def _get_sketch_status(sketch: Any) -> Dict[str, Any]:
    """Get the constraint status of a sketch.

    Args:
        sketch: Fusion Sketch object

    Returns:
        Dict with constraint status information
    """
    # Count constraint types
    under_constrained = 0
    fully_constrained = 0

    for curve in sketch.sketchCurves:
        if hasattr(curve, 'isFullyConstrained'):
            if curve.isFullyConstrained:
                fully_constrained += 1
            else:
                under_constrained += 1

    for point in sketch.sketchPoints:
        if hasattr(point, 'isFullyConstrained'):
            if point.isFullyConstrained:
                fully_constrained += 1
            else:
                under_constrained += 1

    is_fully_constrained = under_constrained == 0 and fully_constrained > 0

    return {
        "is_fully_constrained": is_fully_constrained,
        "under_constrained_count": under_constrained,
        "fully_constrained_count": fully_constrained,
        "constraints_count": sketch.geometricConstraints.count,
        "dimensions_count": sketch.sketchDimensions.count,
        "profiles_count": sketch.profiles.count,
    }


def add_constraint_horizontal(
    sketch_id: str,
    curve_id: str,
) -> Dict[str, Any]:
    """Add a horizontal constraint to a line.

    Constrains a line to be horizontal (parallel to the sketch X axis).

    Args:
        sketch_id: ID of the sketch
        curve_id: ID of the line to constrain

    Returns:
        Dict with constraint information and sketch status

    Raises:
        EntityNotFoundError: If sketch or curve not found
        InvalidParameterError: If curve is not a line
        FeatureError: If constraint creation fails
    """
    registry = get_registry()
    sketch = _get_sketch(sketch_id)

    try:
        curve = _get_sketch_entity(sketch, curve_id, registry)

        # Verify it's a line
        if not hasattr(curve, 'startSketchPoint') or hasattr(curve, 'centerSketchPoint'):
            raise InvalidParameterError(
                "curve_id", curve_id,
                reason="Horizontal constraint requires a line (not arc or circle)"
            )

        # Add horizontal constraint
        constraints = sketch.geometricConstraints
        constraint = constraints.addHorizontal(curve)

        if not constraint:
            raise FeatureError("horizontal_constraint", "Failed to create horizontal constraint")

        # Get constraint index for ID
        constraint_index = constraints.count - 1
        constraint_id = f"{sketch_id}_constraint_{constraint_index}"

        return {
            "success": True,
            "constraint": {
                "id": constraint_id,
                "type": "horizontal",
                "curve_id": curve_id,
            },
            "sketch_id": sketch_id,
            "sketch_status": _get_sketch_status(sketch),
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError(
            "horizontal_constraint",
            f"Failed to add horizontal constraint: {str(e)}",
            fusion_error=str(e)
        )


def add_constraint_vertical(
    sketch_id: str,
    curve_id: str,
) -> Dict[str, Any]:
    """Add a vertical constraint to a line.

    Constrains a line to be vertical (parallel to the sketch Y axis).

    Args:
        sketch_id: ID of the sketch
        curve_id: ID of the line to constrain

    Returns:
        Dict with constraint information and sketch status

    Raises:
        EntityNotFoundError: If sketch or curve not found
        InvalidParameterError: If curve is not a line
        FeatureError: If constraint creation fails
    """
    registry = get_registry()
    sketch = _get_sketch(sketch_id)

    try:
        curve = _get_sketch_entity(sketch, curve_id, registry)

        # Verify it's a line
        if not hasattr(curve, 'startSketchPoint') or hasattr(curve, 'centerSketchPoint'):
            raise InvalidParameterError(
                "curve_id", curve_id,
                reason="Vertical constraint requires a line (not arc or circle)"
            )

        # Add vertical constraint
        constraints = sketch.geometricConstraints
        constraint = constraints.addVertical(curve)

        if not constraint:
            raise FeatureError("vertical_constraint", "Failed to create vertical constraint")

        # Get constraint index for ID
        constraint_index = constraints.count - 1
        constraint_id = f"{sketch_id}_constraint_{constraint_index}"

        return {
            "success": True,
            "constraint": {
                "id": constraint_id,
                "type": "vertical",
                "curve_id": curve_id,
            },
            "sketch_id": sketch_id,
            "sketch_status": _get_sketch_status(sketch),
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError(
            "vertical_constraint",
            f"Failed to add vertical constraint: {str(e)}",
            fusion_error=str(e)
        )


def add_constraint_coincident(
    sketch_id: str,
    entity1_id: str,
    entity2_id: str,
    point1: str = "end",
    point2: str = "start",
) -> Dict[str, Any]:
    """Add a coincident constraint between two entities.

    Makes two points coincident, or places a point on a curve.

    Args:
        sketch_id: ID of the sketch
        entity1_id: ID of the first entity (point or curve)
        entity2_id: ID of the second entity (point or curve)
        point1: For curves, which point to use: "start" or "end" (default "end")
        point2: For curves, which point to use: "start" or "end" (default "start")

    Returns:
        Dict with constraint information and sketch status

    Raises:
        EntityNotFoundError: If sketch or entities not found
        FeatureError: If constraint creation fails
    """
    registry = get_registry()
    sketch = _get_sketch(sketch_id)

    try:
        entity1 = _get_sketch_entity(sketch, entity1_id, registry)
        entity2 = _get_sketch_entity(sketch, entity2_id, registry)

        # Extract points from curves if needed
        # For lines, use startSketchPoint or endSketchPoint
        if hasattr(entity1, 'startSketchPoint') and hasattr(entity1, 'endSketchPoint'):
            # It's a line, get the specified endpoint
            if point1 == "start":
                entity1 = entity1.startSketchPoint
            else:
                entity1 = entity1.endSketchPoint

        if hasattr(entity2, 'startSketchPoint') and hasattr(entity2, 'endSketchPoint'):
            # It's a line, get the specified endpoint
            if point2 == "start":
                entity2 = entity2.startSketchPoint
            else:
                entity2 = entity2.endSketchPoint

        # For circles/arcs, use centerSketchPoint
        if hasattr(entity1, 'centerSketchPoint') and not hasattr(entity1, 'startSketchPoint'):
            entity1 = entity1.centerSketchPoint
        if hasattr(entity2, 'centerSketchPoint') and not hasattr(entity2, 'startSketchPoint'):
            entity2 = entity2.centerSketchPoint

        # Add coincident constraint
        constraints = sketch.geometricConstraints
        constraint = constraints.addCoincident(entity1, entity2)

        if not constraint:
            raise FeatureError("coincident_constraint", "Failed to create coincident constraint")

        # Get constraint index for ID
        constraint_index = constraints.count - 1
        constraint_id = f"{sketch_id}_constraint_{constraint_index}"

        return {
            "success": True,
            "constraint": {
                "id": constraint_id,
                "type": "coincident",
                "entity1_id": entity1_id,
                "entity2_id": entity2_id,
            },
            "sketch_id": sketch_id,
            "sketch_status": _get_sketch_status(sketch),
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError(
            "coincident_constraint",
            f"Failed to add coincident constraint: {str(e)}",
            fusion_error=str(e)
        )


def add_constraint_perpendicular(
    sketch_id: str,
    curve1_id: str,
    curve2_id: str,
) -> Dict[str, Any]:
    """Add a perpendicular constraint between two lines.

    Makes two lines perpendicular (at 90 degrees).

    Args:
        sketch_id: ID of the sketch
        curve1_id: ID of the first line
        curve2_id: ID of the second line

    Returns:
        Dict with constraint information and sketch status

    Raises:
        EntityNotFoundError: If sketch or curves not found
        FeatureError: If constraint creation fails
    """
    registry = get_registry()
    sketch = _get_sketch(sketch_id)

    try:
        curve1 = _get_sketch_entity(sketch, curve1_id, registry)
        curve2 = _get_sketch_entity(sketch, curve2_id, registry)

        # Add perpendicular constraint
        constraints = sketch.geometricConstraints
        constraint = constraints.addPerpendicular(curve1, curve2)

        if not constraint:
            raise FeatureError("perpendicular_constraint", "Failed to create perpendicular constraint")

        # Get constraint index for ID
        constraint_index = constraints.count - 1
        constraint_id = f"{sketch_id}_constraint_{constraint_index}"

        return {
            "success": True,
            "constraint": {
                "id": constraint_id,
                "type": "perpendicular",
                "curve1_id": curve1_id,
                "curve2_id": curve2_id,
            },
            "sketch_id": sketch_id,
            "sketch_status": _get_sketch_status(sketch),
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError(
            "perpendicular_constraint",
            f"Failed to add perpendicular constraint: {str(e)}",
            fusion_error=str(e)
        )


def add_constraint_parallel(
    sketch_id: str,
    curve1_id: str,
    curve2_id: str,
) -> Dict[str, Any]:
    """Add a parallel constraint between two lines.

    Makes two lines parallel.

    Args:
        sketch_id: ID of the sketch
        curve1_id: ID of the first line
        curve2_id: ID of the second line

    Returns:
        Dict with constraint information and sketch status

    Raises:
        EntityNotFoundError: If sketch or curves not found
        FeatureError: If constraint creation fails
    """
    registry = get_registry()
    sketch = _get_sketch(sketch_id)

    try:
        curve1 = _get_sketch_entity(sketch, curve1_id, registry)
        curve2 = _get_sketch_entity(sketch, curve2_id, registry)

        # Add parallel constraint
        constraints = sketch.geometricConstraints
        constraint = constraints.addParallel(curve1, curve2)

        if not constraint:
            raise FeatureError("parallel_constraint", "Failed to create parallel constraint")

        # Get constraint index for ID
        constraint_index = constraints.count - 1
        constraint_id = f"{sketch_id}_constraint_{constraint_index}"

        return {
            "success": True,
            "constraint": {
                "id": constraint_id,
                "type": "parallel",
                "curve1_id": curve1_id,
                "curve2_id": curve2_id,
            },
            "sketch_id": sketch_id,
            "sketch_status": _get_sketch_status(sketch),
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError(
            "parallel_constraint",
            f"Failed to add parallel constraint: {str(e)}",
            fusion_error=str(e)
        )


def add_constraint_tangent(
    sketch_id: str,
    curve1_id: str,
    curve2_id: str,
) -> Dict[str, Any]:
    """Add a tangent constraint between two curves.

    Makes two curves tangent at their connection point.

    Args:
        sketch_id: ID of the sketch
        curve1_id: ID of the first curve
        curve2_id: ID of the second curve

    Returns:
        Dict with constraint information and sketch status

    Raises:
        EntityNotFoundError: If sketch or curves not found
        FeatureError: If constraint creation fails
    """
    registry = get_registry()
    sketch = _get_sketch(sketch_id)

    try:
        curve1 = _get_sketch_entity(sketch, curve1_id, registry)
        curve2 = _get_sketch_entity(sketch, curve2_id, registry)

        # Add tangent constraint
        constraints = sketch.geometricConstraints
        constraint = constraints.addTangent(curve1, curve2)

        if not constraint:
            raise FeatureError("tangent_constraint", "Failed to create tangent constraint")

        # Get constraint index for ID
        constraint_index = constraints.count - 1
        constraint_id = f"{sketch_id}_constraint_{constraint_index}"

        return {
            "success": True,
            "constraint": {
                "id": constraint_id,
                "type": "tangent",
                "curve1_id": curve1_id,
                "curve2_id": curve2_id,
            },
            "sketch_id": sketch_id,
            "sketch_status": _get_sketch_status(sketch),
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError(
            "tangent_constraint",
            f"Failed to add tangent constraint: {str(e)}",
            fusion_error=str(e)
        )


def add_constraint_equal(
    sketch_id: str,
    curve1_id: str,
    curve2_id: str,
) -> Dict[str, Any]:
    """Add an equal constraint between two curves.

    Makes two curves equal (same length for lines, same radius for arcs/circles).

    Args:
        sketch_id: ID of the sketch
        curve1_id: ID of the first curve
        curve2_id: ID of the second curve

    Returns:
        Dict with constraint information and sketch status

    Raises:
        EntityNotFoundError: If sketch or curves not found
        FeatureError: If constraint creation fails
    """
    registry = get_registry()
    sketch = _get_sketch(sketch_id)

    try:
        curve1 = _get_sketch_entity(sketch, curve1_id, registry)
        curve2 = _get_sketch_entity(sketch, curve2_id, registry)

        # Add equal constraint
        constraints = sketch.geometricConstraints
        constraint = constraints.addEqual(curve1, curve2)

        if not constraint:
            raise FeatureError("equal_constraint", "Failed to create equal constraint")

        # Get constraint index for ID
        constraint_index = constraints.count - 1
        constraint_id = f"{sketch_id}_constraint_{constraint_index}"

        return {
            "success": True,
            "constraint": {
                "id": constraint_id,
                "type": "equal",
                "curve1_id": curve1_id,
                "curve2_id": curve2_id,
            },
            "sketch_id": sketch_id,
            "sketch_status": _get_sketch_status(sketch),
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError(
            "equal_constraint",
            f"Failed to add equal constraint: {str(e)}",
            fusion_error=str(e)
        )


def add_constraint_concentric(
    sketch_id: str,
    curve1_id: str,
    curve2_id: str,
) -> Dict[str, Any]:
    """Add a concentric constraint between two circles or arcs.

    Makes two circles or arcs share the same center point.

    Args:
        sketch_id: ID of the sketch
        curve1_id: ID of the first circle/arc
        curve2_id: ID of the second circle/arc

    Returns:
        Dict with constraint information and sketch status

    Raises:
        EntityNotFoundError: If sketch or curves not found
        FeatureError: If constraint creation fails
    """
    registry = get_registry()
    sketch = _get_sketch(sketch_id)

    try:
        curve1 = _get_sketch_entity(sketch, curve1_id, registry)
        curve2 = _get_sketch_entity(sketch, curve2_id, registry)

        # Add concentric constraint
        constraints = sketch.geometricConstraints
        constraint = constraints.addConcentric(curve1, curve2)

        if not constraint:
            raise FeatureError("concentric_constraint", "Failed to create concentric constraint")

        # Get constraint index for ID
        constraint_index = constraints.count - 1
        constraint_id = f"{sketch_id}_constraint_{constraint_index}"

        return {
            "success": True,
            "constraint": {
                "id": constraint_id,
                "type": "concentric",
                "curve1_id": curve1_id,
                "curve2_id": curve2_id,
            },
            "sketch_id": sketch_id,
            "sketch_status": _get_sketch_status(sketch),
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError(
            "concentric_constraint",
            f"Failed to add concentric constraint: {str(e)}",
            fusion_error=str(e)
        )


def add_constraint_fix(
    sketch_id: str,
    entity_id: str,
) -> Dict[str, Any]:
    """Fix a point or curve in place.

    NOTE: The Fix/Unfix constraint is not available via the Fusion 360 API.
    This function is provided for API completeness but will raise an error.
    Use dimensions to lock geometry positions instead.

    Args:
        sketch_id: ID of the sketch
        entity_id: ID of the point or curve to fix

    Raises:
        FeatureError: Always - Fix constraint not available via API
    """
    raise FeatureError(
        "fix_constraint",
        "Fix constraint is not available via the Fusion 360 API. "
        "Use dimensions (distance from origin) to lock geometry positions instead.",
        suggestion="Add distance dimensions from origin points to fix positions."
    )


def add_dimension(
    sketch_id: str,
    dimension_type: str,
    entity1_id: str,
    value: float,
    entity2_id: Optional[str] = None,
    text_position_x: Optional[float] = None,
    text_position_y: Optional[float] = None,
) -> Dict[str, Any]:
    """Add a dimensional constraint to a sketch.

    Adds a dimension that drives geometry (changing the value moves the geometry).

    Args:
        sketch_id: ID of the sketch
        dimension_type: Type of dimension:
            - "distance": Distance between two points/entities or line length
            - "radius": Radius of a circle or arc
            - "diameter": Diameter of a circle or arc
            - "angle": Angle between two lines
        entity1_id: ID of the first entity
        value: Dimension value in mm (for distance/radius/diameter) or degrees (for angle)
        entity2_id: ID of second entity (required for distance between two entities and angle)
        text_position_x: Optional X position for dimension text in mm
        text_position_y: Optional Y position for dimension text in mm

    Returns:
        Dict with dimension information and sketch status

    Raises:
        InvalidParameterError: If dimension_type is invalid or value is non-positive
        EntityNotFoundError: If sketch or entities not found
        FeatureError: If dimension creation fails
    """
    valid_types = ["distance", "radius", "diameter", "angle"]
    if dimension_type not in valid_types:
        raise InvalidParameterError(
            "dimension_type", dimension_type,
            valid_values=valid_types
        )

    if value <= 0 and dimension_type != "angle":
        raise InvalidParameterError(
            "value", value,
            reason=f"{dimension_type} value must be positive"
        )

    registry = get_registry()
    sketch = _get_sketch(sketch_id)

    try:
        entity1 = _get_sketch_entity(sketch, entity1_id, registry)

        # Get text position if specified, otherwise use default
        if text_position_x is not None and text_position_y is not None:
            text_point = adsk.core.Point3D.create(
                text_position_x / 10.0,
                text_position_y / 10.0,
                0
            )
        else:
            # Default text position slightly offset from entity
            text_point = adsk.core.Point3D.create(0, 0, 0)

        dimensions = sketch.sketchDimensions
        dimension = None

        if dimension_type == "distance":
            if entity2_id:
                # Distance between two entities
                entity2 = _get_sketch_entity(sketch, entity2_id, registry)
                dimension = dimensions.addDistanceDimension(
                    entity1, entity2,
                    adsk.fusion.DimensionOrientations.AlignedDimensionOrientation,
                    text_point
                )
            else:
                # Length of a line - use start and end points
                if hasattr(entity1, 'startSketchPoint') and hasattr(entity1, 'endSketchPoint'):
                    dimension = dimensions.addDistanceDimension(
                        entity1.startSketchPoint, entity1.endSketchPoint,
                        adsk.fusion.DimensionOrientations.AlignedDimensionOrientation,
                        text_point
                    )
                else:
                    raise InvalidParameterError(
                        "entity1_id", entity1_id,
                        reason="Distance dimension on single entity requires a line"
                    )

        elif dimension_type == "radius":
            if not hasattr(entity1, 'centerSketchPoint'):
                raise InvalidParameterError(
                    "entity1_id", entity1_id,
                    reason="Radius dimension requires a circle or arc"
                )
            dimension = dimensions.addRadialDimension(entity1, text_point)

        elif dimension_type == "diameter":
            if not hasattr(entity1, 'centerSketchPoint'):
                raise InvalidParameterError(
                    "entity1_id", entity1_id,
                    reason="Diameter dimension requires a circle or arc"
                )
            dimension = dimensions.addDiameterDimension(entity1, text_point)

        elif dimension_type == "angle":
            if not entity2_id:
                raise InvalidParameterError(
                    "entity2_id", None,
                    reason="Angle dimension requires two lines"
                )
            entity2 = _get_sketch_entity(sketch, entity2_id, registry)
            dimension = dimensions.addAngularDimension(entity1, entity2, text_point)

        if not dimension:
            raise FeatureError("dimension", f"Failed to create {dimension_type} dimension")

        # Set the dimension value
        if dimension_type == "angle":
            # Angle in radians
            dimension.parameter.value = math.radians(value)
        else:
            # Distance in cm
            dimension.parameter.value = value / 10.0

        # Get dimension index for ID
        dimension_index = dimensions.count - 1
        dimension_id = f"{sketch_id}_dimension_{dimension_index}"

        # Get the actual value after setting (may differ due to constraints)
        if dimension_type == "angle":
            actual_value = math.degrees(dimension.parameter.value)
        else:
            actual_value = dimension.parameter.value * 10.0  # Convert cm to mm

        return {
            "success": True,
            "dimension": {
                "id": dimension_id,
                "type": dimension_type,
                "entity1_id": entity1_id,
                "entity2_id": entity2_id,
                "requested_value": value,
                "actual_value": actual_value,
                "parameter_name": dimension.parameter.name,
            },
            "sketch_id": sketch_id,
            "sketch_status": _get_sketch_status(sketch),
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError(
            "dimension",
            f"Failed to add {dimension_type} dimension: {str(e)}",
            fusion_error=str(e)
        )
