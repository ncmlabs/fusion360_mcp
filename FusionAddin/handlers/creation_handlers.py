"""Creation handlers for Fusion 360 MCP Add-in.

These handlers are called from the main thread via the EventManager
and provide creation operations for bodies, sketches, and features.
"""

from typing import Dict, Any

from operations.body_ops import create_box, create_cylinder
from operations.sketch_ops import (
    create_sketch,
    draw_line,
    draw_circle,
    draw_rectangle,
    draw_arc,
    draw_polygon,
    draw_ellipse,
    draw_slot,
    draw_spline,
    draw_point,
    # Phase 7b: Sketch Patterns & Operations
    sketch_mirror,
    sketch_circular_pattern,
    sketch_rectangular_pattern,
    project_geometry,
    add_sketch_text,
    # Phase 7c: Sketch Constraints & Dimensions
    add_constraint_horizontal,
    add_constraint_vertical,
    add_constraint_coincident,
    add_constraint_perpendicular,
    add_constraint_parallel,
    add_constraint_tangent,
    add_constraint_equal,
    add_constraint_concentric,
    add_constraint_fix,
    add_dimension,
)
from operations.feature_ops import (
    extrude,
    revolve,
    fillet,
    chamfer,
    create_hole,
)
from shared.exceptions import InvalidParameterError


# --- Body Creation Handlers ---

def handle_create_box(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle create_box request.

    Creates a box (rectangular prism) in the design.

    Args:
        args: Request arguments
            - width: Box width in mm (required)
            - depth: Box depth in mm (required)
            - height: Box height in mm (required)
            - x: X position of center in mm (default 0)
            - y: Y position of center in mm (default 0)
            - z: Z position/offset in mm (default 0)
            - name: Optional name for the body
            - plane: Construction plane XY/YZ/XZ (default XY)
            - component_id: Optional component ID

    Returns:
        Dict with body and feature information
    """
    # Validate required parameters
    if "width" not in args:
        raise InvalidParameterError("width", None, reason="width is required")
    if "depth" not in args:
        raise InvalidParameterError("depth", None, reason="depth is required")
    if "height" not in args:
        raise InvalidParameterError("height", None, reason="height is required")

    return create_box(
        width=float(args["width"]),
        depth=float(args["depth"]),
        height=float(args["height"]),
        x=float(args.get("x", 0)),
        y=float(args.get("y", 0)),
        z=float(args.get("z", 0)),
        name=args.get("name"),
        plane=args.get("plane", "XY"),
        component_id=args.get("component_id"),
    )


def handle_create_cylinder(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle create_cylinder request.

    Creates a cylinder in the design.

    Args:
        args: Request arguments
            - radius: Cylinder radius in mm (required)
            - height: Cylinder height in mm (required)
            - x: X position of center in mm (default 0)
            - y: Y position of center in mm (default 0)
            - z: Z position/offset in mm (default 0)
            - name: Optional name for the body
            - plane: Construction plane XY/YZ/XZ (default XY)
            - component_id: Optional component ID

    Returns:
        Dict with body and feature information
    """
    if "radius" not in args:
        raise InvalidParameterError("radius", None, reason="radius is required")
    if "height" not in args:
        raise InvalidParameterError("height", None, reason="height is required")

    return create_cylinder(
        radius=float(args["radius"]),
        height=float(args["height"]),
        x=float(args.get("x", 0)),
        y=float(args.get("y", 0)),
        z=float(args.get("z", 0)),
        name=args.get("name"),
        plane=args.get("plane", "XY"),
        component_id=args.get("component_id"),
    )


# --- Sketch Creation Handlers ---

def handle_create_sketch(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle create_sketch request.

    Creates a new sketch on a construction plane.

    Args:
        args: Request arguments
            - plane: Construction plane XY/YZ/XZ or face_id (default XY)
            - name: Optional name for the sketch
            - offset: Offset from plane in mm (default 0)
            - component_id: Optional component ID

    Returns:
        Dict with sketch information
    """
    return create_sketch(
        plane=args.get("plane", "XY"),
        name=args.get("name"),
        offset=float(args.get("offset", 0)),
        component_id=args.get("component_id"),
    )


def handle_draw_line(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle draw_line request.

    Draws a line in a sketch.

    Args:
        args: Request arguments
            - sketch_id: ID of the sketch (required)
            - start_x: Start X coordinate in mm (required)
            - start_y: Start Y coordinate in mm (required)
            - end_x: End X coordinate in mm (required)
            - end_y: End Y coordinate in mm (required)

    Returns:
        Dict with curve information
    """
    if "sketch_id" not in args:
        raise InvalidParameterError("sketch_id", None, reason="sketch_id is required")

    # Support both start/end_x/y and start/end point formats
    if "start_x" in args:
        start_x = float(args["start_x"])
        start_y = float(args["start_y"])
        end_x = float(args["end_x"])
        end_y = float(args["end_y"])
    elif "start" in args:
        start = args["start"]
        end = args["end"]
        start_x = float(start.get("x", start[0]) if isinstance(start, dict) else start[0])
        start_y = float(start.get("y", start[1]) if isinstance(start, dict) else start[1])
        end_x = float(end.get("x", end[0]) if isinstance(end, dict) else end[0])
        end_y = float(end.get("y", end[1]) if isinstance(end, dict) else end[1])
    else:
        raise InvalidParameterError("start_x/start", None, reason="Line start point is required")

    return draw_line(
        sketch_id=args["sketch_id"],
        start_x=start_x,
        start_y=start_y,
        end_x=end_x,
        end_y=end_y,
    )


def handle_draw_circle(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle draw_circle request.

    Draws a circle in a sketch.

    Args:
        args: Request arguments
            - sketch_id: ID of the sketch (required)
            - center_x: Center X coordinate in mm (required)
            - center_y: Center Y coordinate in mm (required)
            - radius: Circle radius in mm (required)

    Returns:
        Dict with curve information
    """
    if "sketch_id" not in args:
        raise InvalidParameterError("sketch_id", None, reason="sketch_id is required")
    if "radius" not in args:
        raise InvalidParameterError("radius", None, reason="radius is required")

    # Support both center_x/y and center point formats
    if "center_x" in args:
        center_x = float(args["center_x"])
        center_y = float(args["center_y"])
    elif "center" in args:
        center = args["center"]
        center_x = float(center.get("x", center[0]) if isinstance(center, dict) else center[0])
        center_y = float(center.get("y", center[1]) if isinstance(center, dict) else center[1])
    else:
        center_x = 0.0
        center_y = 0.0

    return draw_circle(
        sketch_id=args["sketch_id"],
        center_x=center_x,
        center_y=center_y,
        radius=float(args["radius"]),
    )


def handle_draw_rectangle(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle draw_rectangle request.

    Draws a rectangle in a sketch using two corner points.

    Args:
        args: Request arguments
            - sketch_id: ID of the sketch (required)
            - x1, y1: First corner coordinates in mm
            - x2, y2: Opposite corner coordinates in mm
            OR
            - corner1, corner2: Point dicts or arrays

    Returns:
        Dict with curve information
    """
    if "sketch_id" not in args:
        raise InvalidParameterError("sketch_id", None, reason="sketch_id is required")

    if "x1" in args:
        x1 = float(args["x1"])
        y1 = float(args["y1"])
        x2 = float(args["x2"])
        y2 = float(args["y2"])
    elif "corner1" in args:
        c1 = args["corner1"]
        c2 = args["corner2"]
        x1 = float(c1.get("x", c1[0]) if isinstance(c1, dict) else c1[0])
        y1 = float(c1.get("y", c1[1]) if isinstance(c1, dict) else c1[1])
        x2 = float(c2.get("x", c2[0]) if isinstance(c2, dict) else c2[0])
        y2 = float(c2.get("y", c2[1]) if isinstance(c2, dict) else c2[1])
    else:
        raise InvalidParameterError("x1/corner1", None, reason="Rectangle corners are required")

    return draw_rectangle(
        sketch_id=args["sketch_id"],
        x1=x1,
        y1=y1,
        x2=x2,
        y2=y2,
    )


def handle_draw_arc(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle draw_arc request.

    Draws an arc in a sketch.

    Args:
        args: Request arguments
            - sketch_id: ID of the sketch (required)
            - center_x: Center X coordinate in mm
            - center_y: Center Y coordinate in mm
            - radius: Arc radius in mm (required)
            - start_angle: Start angle in degrees (required)
            - end_angle: End angle in degrees (required)

    Returns:
        Dict with curve information
    """
    if "sketch_id" not in args:
        raise InvalidParameterError("sketch_id", None, reason="sketch_id is required")
    if "radius" not in args:
        raise InvalidParameterError("radius", None, reason="radius is required")
    if "start_angle" not in args:
        raise InvalidParameterError("start_angle", None, reason="start_angle is required")
    if "end_angle" not in args:
        raise InvalidParameterError("end_angle", None, reason="end_angle is required")

    center_x = float(args.get("center_x", 0))
    center_y = float(args.get("center_y", 0))

    return draw_arc(
        sketch_id=args["sketch_id"],
        center_x=center_x,
        center_y=center_y,
        radius=float(args["radius"]),
        start_angle=float(args["start_angle"]),
        end_angle=float(args["end_angle"]),
    )


# --- Feature Handlers ---

def handle_extrude(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle extrude request.

    Extrudes a sketch profile.

    Args:
        args: Request arguments
            - sketch_id: ID of the sketch (required)
            - distance: Extrusion distance in mm (required)
            - direction: "positive", "negative", or "symmetric" (default positive)
            - operation: "new_body", "join", "cut", "intersect" (default new_body)
            - profile_index: Index of profile to extrude (default 0)
            - name: Optional name for created body
            - taper_angle: Taper angle in degrees (default 0)

    Returns:
        Dict with feature and body information
    """
    if "sketch_id" not in args:
        raise InvalidParameterError("sketch_id", None, reason="sketch_id is required")
    if "distance" not in args:
        raise InvalidParameterError("distance", None, reason="distance is required")

    return extrude(
        sketch_id=args["sketch_id"],
        distance=float(args["distance"]),
        direction=args.get("direction", "positive"),
        operation=args.get("operation", "new_body"),
        profile_index=int(args.get("profile_index", 0)),
        name=args.get("name"),
        taper_angle=float(args.get("taper_angle", 0)),
    )


def handle_revolve(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle revolve request.

    Revolves a sketch profile around an axis.

    Args:
        args: Request arguments
            - sketch_id: ID of the sketch (required)
            - axis: Axis to revolve around - "X", "Y", "Z" (required)
            - angle: Revolution angle in degrees (default 360)
            - operation: "new_body", "join", "cut", "intersect" (default new_body)
            - profile_index: Index of profile to revolve (default 0)
            - name: Optional name for created body

    Returns:
        Dict with feature and body information
    """
    if "sketch_id" not in args:
        raise InvalidParameterError("sketch_id", None, reason="sketch_id is required")
    if "axis" not in args:
        raise InvalidParameterError("axis", None, reason="axis is required")

    return revolve(
        sketch_id=args["sketch_id"],
        axis=args["axis"],
        angle=float(args.get("angle", 360)),
        operation=args.get("operation", "new_body"),
        profile_index=int(args.get("profile_index", 0)),
        name=args.get("name"),
    )


def handle_fillet(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle fillet request.

    Applies fillet to edges of a body.

    Args:
        args: Request arguments
            - body_id: ID of the body (required)
            - edge_ids: List of edge IDs to fillet (required)
            - radius: Fillet radius in mm (required)

    Returns:
        Dict with feature information
    """
    if "body_id" not in args:
        raise InvalidParameterError("body_id", None, reason="body_id is required")
    if "edge_ids" not in args:
        raise InvalidParameterError("edge_ids", None, reason="edge_ids is required")
    if "radius" not in args:
        raise InvalidParameterError("radius", None, reason="radius is required")

    edge_ids = args["edge_ids"]
    if isinstance(edge_ids, str):
        edge_ids = [edge_ids]

    return fillet(
        body_id=args["body_id"],
        edge_ids=edge_ids,
        radius=float(args["radius"]),
    )


def handle_chamfer(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle chamfer request.

    Applies chamfer to edges of a body.

    Args:
        args: Request arguments
            - body_id: ID of the body (required)
            - edge_ids: List of edge IDs to chamfer (required)
            - distance: Chamfer distance in mm (required)
            - distance2: Optional second distance for asymmetric chamfer

    Returns:
        Dict with feature information
    """
    if "body_id" not in args:
        raise InvalidParameterError("body_id", None, reason="body_id is required")
    if "edge_ids" not in args:
        raise InvalidParameterError("edge_ids", None, reason="edge_ids is required")
    if "distance" not in args:
        raise InvalidParameterError("distance", None, reason="distance is required")

    edge_ids = args["edge_ids"]
    if isinstance(edge_ids, str):
        edge_ids = [edge_ids]

    return chamfer(
        body_id=args["body_id"],
        edge_ids=edge_ids,
        distance=float(args["distance"]),
        distance2=float(args["distance2"]) if "distance2" in args else None,
    )


def handle_create_hole(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle create_hole request.

    Creates a hole in a body.

    Args:
        args: Request arguments
            - body_id: ID of the body (optional if face_id provided)
            - face_id: ID of the face to place hole on (optional)
            - x: X position in mm (default 0)
            - y: Y position in mm (default 0)
            - diameter: Hole diameter in mm (required)
            - depth: Hole depth in mm (required)
            - name: Optional name for the feature
            - hole_type: "simple", "countersink", "counterbore" (default simple)
            - countersink_angle: Countersink angle in degrees (default 90)
            - countersink_diameter: Countersink diameter in mm
            - counterbore_diameter: Counterbore diameter in mm
            - counterbore_depth: Counterbore depth in mm

    Returns:
        Dict with feature information
    """
    if "diameter" not in args:
        raise InvalidParameterError("diameter", None, reason="diameter is required")
    if "depth" not in args:
        raise InvalidParameterError("depth", None, reason="depth is required")
    if "body_id" not in args and "face_id" not in args:
        raise InvalidParameterError("body_id/face_id", None, reason="Either body_id or face_id is required")

    return create_hole(
        body_id=args.get("body_id"),
        face_id=args.get("face_id"),
        x=float(args.get("x", 0)),
        y=float(args.get("y", 0)),
        diameter=float(args["diameter"]),
        depth=float(args["depth"]),
        name=args.get("name"),
        hole_type=args.get("hole_type", "simple"),
        countersink_angle=float(args.get("countersink_angle", 90)),
        countersink_diameter=float(args.get("countersink_diameter", 0)),
        counterbore_diameter=float(args.get("counterbore_diameter", 0)),
        counterbore_depth=float(args.get("counterbore_depth", 0)),
    )


# --- Advanced Sketch Geometry Handlers ---

def handle_draw_polygon(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle draw_polygon request.

    Draws a regular polygon in a sketch.

    Args:
        args: Request arguments
            - sketch_id: ID of the sketch (required)
            - center_x: Center X coordinate in mm (default 0)
            - center_y: Center Y coordinate in mm (default 0)
            - radius: Circumscribed radius in mm (required)
            - sides: Number of sides 3-64 (required)
            - rotation_angle: Rotation angle in degrees (default 0)

    Returns:
        Dict with curve IDs and polygon information
    """
    if "sketch_id" not in args:
        raise InvalidParameterError("sketch_id", None, reason="sketch_id is required")
    if "radius" not in args:
        raise InvalidParameterError("radius", None, reason="radius is required")
    if "sides" not in args:
        raise InvalidParameterError("sides", None, reason="sides is required")

    return draw_polygon(
        sketch_id=args["sketch_id"],
        center_x=float(args.get("center_x", 0)),
        center_y=float(args.get("center_y", 0)),
        radius=float(args["radius"]),
        sides=int(args["sides"]),
        rotation_angle=float(args.get("rotation_angle", 0)),
    )


def handle_draw_ellipse(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle draw_ellipse request.

    Draws an ellipse in a sketch.

    Args:
        args: Request arguments
            - sketch_id: ID of the sketch (required)
            - center_x: Center X coordinate in mm (default 0)
            - center_y: Center Y coordinate in mm (default 0)
            - major_radius: Major axis radius in mm (required)
            - minor_radius: Minor axis radius in mm (required)
            - rotation_angle: Rotation of major axis in degrees (default 0)

    Returns:
        Dict with curve ID and ellipse information
    """
    if "sketch_id" not in args:
        raise InvalidParameterError("sketch_id", None, reason="sketch_id is required")
    if "major_radius" not in args:
        raise InvalidParameterError("major_radius", None, reason="major_radius is required")
    if "minor_radius" not in args:
        raise InvalidParameterError("minor_radius", None, reason="minor_radius is required")

    return draw_ellipse(
        sketch_id=args["sketch_id"],
        center_x=float(args.get("center_x", 0)),
        center_y=float(args.get("center_y", 0)),
        major_radius=float(args["major_radius"]),
        minor_radius=float(args["minor_radius"]),
        rotation_angle=float(args.get("rotation_angle", 0)),
    )


def handle_draw_slot(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle draw_slot request.

    Draws a slot shape (rounded rectangle/oblong) in a sketch.

    Args:
        args: Request arguments
            - sketch_id: ID of the sketch (required)
            - center_x: Center X coordinate in mm (default 0)
            - center_y: Center Y coordinate in mm (default 0)
            - length: Slot length in mm (required)
            - width: Slot width in mm (required)
            - slot_type: "overall" or "center_to_center" (default "overall")
            - rotation_angle: Rotation angle in degrees (default 0)

    Returns:
        Dict with curve IDs and slot information
    """
    if "sketch_id" not in args:
        raise InvalidParameterError("sketch_id", None, reason="sketch_id is required")
    if "length" not in args:
        raise InvalidParameterError("length", None, reason="length is required")
    if "width" not in args:
        raise InvalidParameterError("width", None, reason="width is required")

    return draw_slot(
        sketch_id=args["sketch_id"],
        center_x=float(args.get("center_x", 0)),
        center_y=float(args.get("center_y", 0)),
        length=float(args["length"]),
        width=float(args["width"]),
        slot_type=args.get("slot_type", "overall"),
        rotation_angle=float(args.get("rotation_angle", 0)),
    )


def handle_draw_spline(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle draw_spline request.

    Draws a spline (smooth curve) through control points in a sketch.

    Args:
        args: Request arguments
            - sketch_id: ID of the sketch (required)
            - points: List of {x, y} point dicts in mm (required)
            - is_closed: Whether to create a closed spline loop (default False)

    Returns:
        Dict with curve ID and spline information
    """
    if "sketch_id" not in args:
        raise InvalidParameterError("sketch_id", None, reason="sketch_id is required")
    if "points" not in args:
        raise InvalidParameterError("points", None, reason="points is required")

    points = args["points"]
    if not isinstance(points, list):
        raise InvalidParameterError("points", points, reason="points must be a list")

    return draw_spline(
        sketch_id=args["sketch_id"],
        points=points,
        is_closed=bool(args.get("is_closed", False)),
    )


def handle_draw_point(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle draw_point request.

    Draws a point in a sketch.

    Args:
        args: Request arguments
            - sketch_id: ID of the sketch (required)
            - x: X coordinate in mm (required)
            - y: Y coordinate in mm (required)
            - is_construction: Mark as construction geometry (default False)

    Returns:
        Dict with point ID and point information
    """
    if "sketch_id" not in args:
        raise InvalidParameterError("sketch_id", None, reason="sketch_id is required")
    if "x" not in args:
        raise InvalidParameterError("x", None, reason="x coordinate is required")
    if "y" not in args:
        raise InvalidParameterError("y", None, reason="y coordinate is required")

    return draw_point(
        sketch_id=args["sketch_id"],
        x=float(args["x"]),
        y=float(args["y"]),
        is_construction=bool(args.get("is_construction", False)),
    )


# --- Phase 7b: Sketch Patterns & Operations Handlers ---

def handle_sketch_mirror(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle sketch_mirror request.

    Mirrors sketch entities across a line.

    Args:
        args: Request arguments
            - sketch_id: ID of the sketch (required)
            - curve_ids: List of curve IDs to mirror (required)
            - mirror_line_id: ID of the line to mirror across (required)

    Returns:
        Dict with mirrored curve IDs and information
    """
    if "sketch_id" not in args:
        raise InvalidParameterError("sketch_id", None, reason="sketch_id is required")
    if "curve_ids" not in args:
        raise InvalidParameterError("curve_ids", None, reason="curve_ids is required")
    if "mirror_line_id" not in args:
        raise InvalidParameterError("mirror_line_id", None, reason="mirror_line_id is required")

    curve_ids = args["curve_ids"]
    if isinstance(curve_ids, str):
        curve_ids = [curve_ids]

    return sketch_mirror(
        sketch_id=args["sketch_id"],
        curve_ids=curve_ids,
        mirror_line_id=args["mirror_line_id"],
    )


def handle_sketch_circular_pattern(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle sketch_circular_pattern request.

    Creates a circular pattern of sketch entities.

    Args:
        args: Request arguments
            - sketch_id: ID of the sketch (required)
            - curve_ids: List of curve IDs to pattern (required)
            - center_x: Pattern center X in mm (default 0)
            - center_y: Pattern center Y in mm (default 0)
            - count: Number of instances including original (required)
            - total_angle: Total angle span in degrees (default 360)

    Returns:
        Dict with pattern information and new curve IDs
    """
    if "sketch_id" not in args:
        raise InvalidParameterError("sketch_id", None, reason="sketch_id is required")
    if "curve_ids" not in args:
        raise InvalidParameterError("curve_ids", None, reason="curve_ids is required")
    if "count" not in args:
        raise InvalidParameterError("count", None, reason="count is required")

    curve_ids = args["curve_ids"]
    if isinstance(curve_ids, str):
        curve_ids = [curve_ids]

    return sketch_circular_pattern(
        sketch_id=args["sketch_id"],
        curve_ids=curve_ids,
        center_x=float(args.get("center_x", 0)),
        center_y=float(args.get("center_y", 0)),
        count=int(args["count"]),
        total_angle=float(args.get("total_angle", 360)),
    )


def handle_sketch_rectangular_pattern(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle sketch_rectangular_pattern request.

    Creates a rectangular pattern of sketch entities.

    Args:
        args: Request arguments
            - sketch_id: ID of the sketch (required)
            - curve_ids: List of curve IDs to pattern (required)
            - x_count: Number of columns (required)
            - y_count: Number of rows (required)
            - x_spacing: Column spacing in mm (required)
            - y_spacing: Row spacing in mm (required)

    Returns:
        Dict with pattern information and new curve IDs
    """
    if "sketch_id" not in args:
        raise InvalidParameterError("sketch_id", None, reason="sketch_id is required")
    if "curve_ids" not in args:
        raise InvalidParameterError("curve_ids", None, reason="curve_ids is required")
    if "x_count" not in args:
        raise InvalidParameterError("x_count", None, reason="x_count is required")
    if "y_count" not in args:
        raise InvalidParameterError("y_count", None, reason="y_count is required")
    if "x_spacing" not in args:
        raise InvalidParameterError("x_spacing", None, reason="x_spacing is required")
    if "y_spacing" not in args:
        raise InvalidParameterError("y_spacing", None, reason="y_spacing is required")

    curve_ids = args["curve_ids"]
    if isinstance(curve_ids, str):
        curve_ids = [curve_ids]

    return sketch_rectangular_pattern(
        sketch_id=args["sketch_id"],
        curve_ids=curve_ids,
        x_count=int(args["x_count"]),
        y_count=int(args["y_count"]),
        x_spacing=float(args["x_spacing"]),
        y_spacing=float(args["y_spacing"]),
    )


def handle_project_geometry(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle project_geometry request.

    Projects edges or faces from 3D bodies onto a sketch.

    Args:
        args: Request arguments
            - sketch_id: ID of the target sketch (required)
            - entity_ids: List of entity IDs to project (required)
            - project_type: "standard" or "cut_edges" (default "standard")

    Returns:
        Dict with projected curve IDs and information
    """
    if "sketch_id" not in args:
        raise InvalidParameterError("sketch_id", None, reason="sketch_id is required")
    if "entity_ids" not in args:
        raise InvalidParameterError("entity_ids", None, reason="entity_ids is required")

    entity_ids = args["entity_ids"]
    if isinstance(entity_ids, str):
        entity_ids = [entity_ids]

    return project_geometry(
        sketch_id=args["sketch_id"],
        entity_ids=entity_ids,
        project_type=args.get("project_type", "standard"),
    )


def handle_add_sketch_text(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle add_sketch_text request.

    Adds text to a sketch for engraving or embossing.

    Args:
        args: Request arguments
            - sketch_id: ID of the target sketch (required)
            - text: Text content (required)
            - x: Text position X in mm (default 0)
            - y: Text position Y in mm (default 0)
            - height: Text height in mm (required)
            - font_name: Font name (optional)
            - is_bold: Bold text (default False)
            - is_italic: Italic text (default False)

    Returns:
        Dict with text information and profiles
    """
    if "sketch_id" not in args:
        raise InvalidParameterError("sketch_id", None, reason="sketch_id is required")
    if "text" not in args:
        raise InvalidParameterError("text", None, reason="text is required")
    if "height" not in args:
        raise InvalidParameterError("height", None, reason="height is required")

    return add_sketch_text(
        sketch_id=args["sketch_id"],
        text=args["text"],
        x=float(args.get("x", 0)),
        y=float(args.get("y", 0)),
        height=float(args["height"]),
        font_name=args.get("font_name"),
        is_bold=bool(args.get("is_bold", False)),
        is_italic=bool(args.get("is_italic", False)),
    )


# --- Phase 7c: Sketch Constraints & Dimensions Handlers ---

def handle_add_constraint_horizontal(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle add_constraint_horizontal request.

    Constrains a line to be horizontal.

    Args:
        args: Request arguments
            - sketch_id: ID of the sketch (required)
            - curve_id: ID of the line to constrain (required)

    Returns:
        Dict with constraint information and sketch status
    """
    if "sketch_id" not in args:
        raise InvalidParameterError("sketch_id", None, reason="sketch_id is required")
    if "curve_id" not in args:
        raise InvalidParameterError("curve_id", None, reason="curve_id is required")

    return add_constraint_horizontal(
        sketch_id=args["sketch_id"],
        curve_id=args["curve_id"],
    )


def handle_add_constraint_vertical(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle add_constraint_vertical request.

    Constrains a line to be vertical.

    Args:
        args: Request arguments
            - sketch_id: ID of the sketch (required)
            - curve_id: ID of the line to constrain (required)

    Returns:
        Dict with constraint information and sketch status
    """
    if "sketch_id" not in args:
        raise InvalidParameterError("sketch_id", None, reason="sketch_id is required")
    if "curve_id" not in args:
        raise InvalidParameterError("curve_id", None, reason="curve_id is required")

    return add_constraint_vertical(
        sketch_id=args["sketch_id"],
        curve_id=args["curve_id"],
    )


def handle_add_constraint_coincident(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle add_constraint_coincident request.

    Makes two points coincident, or places a point on a curve.

    Args:
        args: Request arguments
            - sketch_id: ID of the sketch (required)
            - entity1_id: ID of the first entity (required)
            - entity2_id: ID of the second entity (required)
            - point1: For curves, which point: "start" or "end" (default "end")
            - point2: For curves, which point: "start" or "end" (default "start")

    Returns:
        Dict with constraint information and sketch status
    """
    if "sketch_id" not in args:
        raise InvalidParameterError("sketch_id", None, reason="sketch_id is required")
    if "entity1_id" not in args:
        raise InvalidParameterError("entity1_id", None, reason="entity1_id is required")
    if "entity2_id" not in args:
        raise InvalidParameterError("entity2_id", None, reason="entity2_id is required")

    return add_constraint_coincident(
        sketch_id=args["sketch_id"],
        entity1_id=args["entity1_id"],
        entity2_id=args["entity2_id"],
        point1=args.get("point1", "end"),
        point2=args.get("point2", "start"),
    )


def handle_add_constraint_perpendicular(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle add_constraint_perpendicular request.

    Makes two lines perpendicular (at 90 degrees).

    Args:
        args: Request arguments
            - sketch_id: ID of the sketch (required)
            - curve1_id: ID of the first line (required)
            - curve2_id: ID of the second line (required)

    Returns:
        Dict with constraint information and sketch status
    """
    if "sketch_id" not in args:
        raise InvalidParameterError("sketch_id", None, reason="sketch_id is required")
    if "curve1_id" not in args:
        raise InvalidParameterError("curve1_id", None, reason="curve1_id is required")
    if "curve2_id" not in args:
        raise InvalidParameterError("curve2_id", None, reason="curve2_id is required")

    return add_constraint_perpendicular(
        sketch_id=args["sketch_id"],
        curve1_id=args["curve1_id"],
        curve2_id=args["curve2_id"],
    )


def handle_add_constraint_parallel(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle add_constraint_parallel request.

    Makes two lines parallel.

    Args:
        args: Request arguments
            - sketch_id: ID of the sketch (required)
            - curve1_id: ID of the first line (required)
            - curve2_id: ID of the second line (required)

    Returns:
        Dict with constraint information and sketch status
    """
    if "sketch_id" not in args:
        raise InvalidParameterError("sketch_id", None, reason="sketch_id is required")
    if "curve1_id" not in args:
        raise InvalidParameterError("curve1_id", None, reason="curve1_id is required")
    if "curve2_id" not in args:
        raise InvalidParameterError("curve2_id", None, reason="curve2_id is required")

    return add_constraint_parallel(
        sketch_id=args["sketch_id"],
        curve1_id=args["curve1_id"],
        curve2_id=args["curve2_id"],
    )


def handle_add_constraint_tangent(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle add_constraint_tangent request.

    Makes two curves tangent at their connection point.

    Args:
        args: Request arguments
            - sketch_id: ID of the sketch (required)
            - curve1_id: ID of the first curve (required)
            - curve2_id: ID of the second curve (required)

    Returns:
        Dict with constraint information and sketch status
    """
    if "sketch_id" not in args:
        raise InvalidParameterError("sketch_id", None, reason="sketch_id is required")
    if "curve1_id" not in args:
        raise InvalidParameterError("curve1_id", None, reason="curve1_id is required")
    if "curve2_id" not in args:
        raise InvalidParameterError("curve2_id", None, reason="curve2_id is required")

    return add_constraint_tangent(
        sketch_id=args["sketch_id"],
        curve1_id=args["curve1_id"],
        curve2_id=args["curve2_id"],
    )


def handle_add_constraint_equal(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle add_constraint_equal request.

    Makes two curves equal (same length for lines, same radius for arcs/circles).

    Args:
        args: Request arguments
            - sketch_id: ID of the sketch (required)
            - curve1_id: ID of the first curve (required)
            - curve2_id: ID of the second curve (required)

    Returns:
        Dict with constraint information and sketch status
    """
    if "sketch_id" not in args:
        raise InvalidParameterError("sketch_id", None, reason="sketch_id is required")
    if "curve1_id" not in args:
        raise InvalidParameterError("curve1_id", None, reason="curve1_id is required")
    if "curve2_id" not in args:
        raise InvalidParameterError("curve2_id", None, reason="curve2_id is required")

    return add_constraint_equal(
        sketch_id=args["sketch_id"],
        curve1_id=args["curve1_id"],
        curve2_id=args["curve2_id"],
    )


def handle_add_constraint_concentric(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle add_constraint_concentric request.

    Makes two circles or arcs share the same center point.

    Args:
        args: Request arguments
            - sketch_id: ID of the sketch (required)
            - curve1_id: ID of the first circle/arc (required)
            - curve2_id: ID of the second circle/arc (required)

    Returns:
        Dict with constraint information and sketch status
    """
    if "sketch_id" not in args:
        raise InvalidParameterError("sketch_id", None, reason="sketch_id is required")
    if "curve1_id" not in args:
        raise InvalidParameterError("curve1_id", None, reason="curve1_id is required")
    if "curve2_id" not in args:
        raise InvalidParameterError("curve2_id", None, reason="curve2_id is required")

    return add_constraint_concentric(
        sketch_id=args["sketch_id"],
        curve1_id=args["curve1_id"],
        curve2_id=args["curve2_id"],
    )


def handle_add_constraint_fix(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle add_constraint_fix request.

    Fixes a point or curve in place.

    Args:
        args: Request arguments
            - sketch_id: ID of the sketch (required)
            - entity_id: ID of the point or curve to fix (required)

    Returns:
        Dict with constraint information and sketch status
    """
    if "sketch_id" not in args:
        raise InvalidParameterError("sketch_id", None, reason="sketch_id is required")
    if "entity_id" not in args:
        raise InvalidParameterError("entity_id", None, reason="entity_id is required")

    return add_constraint_fix(
        sketch_id=args["sketch_id"],
        entity_id=args["entity_id"],
    )


def handle_add_dimension(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle add_dimension request.

    Adds a dimensional constraint to a sketch.

    Args:
        args: Request arguments
            - sketch_id: ID of the sketch (required)
            - dimension_type: Type of dimension - "distance", "radius", "diameter", "angle" (required)
            - entity1_id: ID of the first entity (required)
            - value: Dimension value in mm or degrees (required)
            - entity2_id: ID of second entity (required for distance between two entities and angle)
            - text_position_x: Optional X position for dimension text in mm
            - text_position_y: Optional Y position for dimension text in mm

    Returns:
        Dict with dimension information and sketch status
    """
    if "sketch_id" not in args:
        raise InvalidParameterError("sketch_id", None, reason="sketch_id is required")
    if "dimension_type" not in args:
        raise InvalidParameterError("dimension_type", None, reason="dimension_type is required")
    if "entity1_id" not in args:
        raise InvalidParameterError("entity1_id", None, reason="entity1_id is required")
    if "value" not in args:
        raise InvalidParameterError("value", None, reason="value is required")

    return add_dimension(
        sketch_id=args["sketch_id"],
        dimension_type=args["dimension_type"],
        entity1_id=args["entity1_id"],
        value=float(args["value"]),
        entity2_id=args.get("entity2_id"),
        text_position_x=float(args["text_position_x"]) if "text_position_x" in args else None,
        text_position_y=float(args["text_position_y"]) if "text_position_y" in args else None,
    )
