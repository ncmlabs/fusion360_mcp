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
    wrap_sketch_to_surface,
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
    sweep,
    loft,
    create_sphere,
    create_torus,
    create_coil,
    create_pipe,
    # Phase 8b: Feature Pattern Tools
    rectangular_pattern,
    circular_pattern,
    mirror_feature,
    # Phase 8c: Specialized Feature Tools
    create_thread,
    thicken,
    emboss,
)
from operations.plane_ops import (
    create_offset_plane,
    create_angle_plane,
    create_three_point_plane,
    create_midplane,
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


def handle_wrap_sketch_to_surface(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle wrap_sketch_to_surface request.

    Wraps sketch curves onto a curved surface using projection.

    Args:
        args: Request arguments
            - sketch_id: ID of the source sketch (required)
            - face_id: ID of the target curved face (required)
            - projection_type: "closest_point" or "along_vector" (default closest_point)
            - direction_axis: "X", "Y", or "Z" (required when projection_type is along_vector)
            - create_new_sketch: Whether to create a new sketch (default True)

    Returns:
        Dict with wrapped curve IDs and sketch information
    """
    if "sketch_id" not in args:
        raise InvalidParameterError("sketch_id", None, reason="sketch_id is required")
    if "face_id" not in args:
        raise InvalidParameterError("face_id", None, reason="face_id is required")

    return wrap_sketch_to_surface(
        sketch_id=args["sketch_id"],
        face_id=args["face_id"],
        projection_type=args.get("projection_type", "closest_point"),
        direction_axis=args.get("direction_axis"),
        create_new_sketch=bool(args.get("create_new_sketch", True)),
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


# --- Phase 8a: Advanced Feature Handlers ---

def handle_sweep(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle sweep request.

    Sweeps a profile along a path to create complex shapes.

    Args:
        args: Request arguments
            - profile_sketch_id: ID of the sketch containing the profile (required)
            - path_sketch_id: ID of the sketch containing the sweep path (required)
            - profile_index: Index of profile to sweep (default 0)
            - operation: "new_body", "join", "cut", "intersect" (default new_body)
            - orientation: "perpendicular" or "parallel" (default perpendicular)
            - name: Optional name for created body

    Returns:
        Dict with feature and body information
    """
    if "profile_sketch_id" not in args:
        raise InvalidParameterError("profile_sketch_id", None, reason="profile_sketch_id is required")
    if "path_sketch_id" not in args:
        raise InvalidParameterError("path_sketch_id", None, reason="path_sketch_id is required")

    return sweep(
        profile_sketch_id=args["profile_sketch_id"],
        path_sketch_id=args["path_sketch_id"],
        profile_index=int(args.get("profile_index", 0)),
        operation=args.get("operation", "new_body"),
        orientation=args.get("orientation", "perpendicular"),
        name=args.get("name"),
    )


def handle_loft(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle loft request.

    Creates a smooth transition between two or more profiles.

    Args:
        args: Request arguments
            - sketch_ids: Array of sketch IDs in order from start to end (required)
            - profile_indices: Array of profile indices for each sketch (optional)
            - operation: "new_body", "join", "cut", "intersect" (default new_body)
            - is_solid: Create solid (True) or surface (False) (default True)
            - is_closed: Close the loft ends (default False)
            - name: Optional name for created body
            - target_body_id: Body ID for boolean operations (required for cut/join/intersect)

    Returns:
        Dict with feature and body information
    """
    if "sketch_ids" not in args:
        raise InvalidParameterError("sketch_ids", None, reason="sketch_ids is required")

    sketch_ids = args["sketch_ids"]
    if isinstance(sketch_ids, str):
        sketch_ids = [sketch_ids]

    profile_indices = args.get("profile_indices")
    if profile_indices is not None and isinstance(profile_indices, list):
        profile_indices = [int(idx) for idx in profile_indices]

    return loft(
        sketch_ids=sketch_ids,
        profile_indices=profile_indices,
        operation=args.get("operation", "new_body"),
        is_solid=bool(args.get("is_solid", True)),
        is_closed=bool(args.get("is_closed", False)),
        name=args.get("name"),
        target_body_id=args.get("target_body_id"),
    )


def handle_create_sphere(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle create_sphere request.

    Creates a solid sphere primitive.

    Args:
        args: Request arguments
            - radius: Sphere radius in mm (required)
            - x: Center X position in mm (default 0)
            - y: Center Y position in mm (default 0)
            - z: Center Z position in mm (default 0)
            - name: Optional name for the body
            - component_id: Optional component ID

    Returns:
        Dict with body and feature information
    """
    if "radius" not in args:
        raise InvalidParameterError("radius", None, reason="radius is required")

    return create_sphere(
        radius=float(args["radius"]),
        x=float(args.get("x", 0)),
        y=float(args.get("y", 0)),
        z=float(args.get("z", 0)),
        name=args.get("name"),
        component_id=args.get("component_id"),
    )


def handle_create_torus(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle create_torus request.

    Creates a torus (donut/ring shape).

    Args:
        args: Request arguments
            - major_radius: Distance from center to tube center in mm (required)
            - minor_radius: Tube radius in mm (required)
            - x: Center X position in mm (default 0)
            - y: Center Y position in mm (default 0)
            - z: Center Z position in mm (default 0)
            - name: Optional name for the body
            - component_id: Optional component ID

    Returns:
        Dict with body and feature information
    """
    if "major_radius" not in args:
        raise InvalidParameterError("major_radius", None, reason="major_radius is required")
    if "minor_radius" not in args:
        raise InvalidParameterError("minor_radius", None, reason="minor_radius is required")

    return create_torus(
        major_radius=float(args["major_radius"]),
        minor_radius=float(args["minor_radius"]),
        x=float(args.get("x", 0)),
        y=float(args.get("y", 0)),
        z=float(args.get("z", 0)),
        name=args.get("name"),
        component_id=args.get("component_id"),
    )


def handle_create_coil(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle create_coil request.

    Creates a helix/spring shape.

    Args:
        args: Request arguments
            - diameter: Coil diameter in mm (required)
            - pitch: Distance between coils in mm (required)
            - revolutions: Number of turns (required)
            - section_size: Wire/section diameter in mm (required)
            - section_type: "circular" or "square" (default circular)
            - operation: "new_body", "join", "cut", "intersect" (default new_body)
            - name: Optional name for the body
            - x: X position in mm (default 0)
            - y: Y position in mm (default 0)
            - z: Z position in mm (default 0)
            - component_id: Optional component ID

    Returns:
        Dict with body and feature information
    """
    if "diameter" not in args:
        raise InvalidParameterError("diameter", None, reason="diameter is required")
    if "pitch" not in args:
        raise InvalidParameterError("pitch", None, reason="pitch is required")
    if "revolutions" not in args:
        raise InvalidParameterError("revolutions", None, reason="revolutions is required")
    if "section_size" not in args:
        raise InvalidParameterError("section_size", None, reason="section_size is required")

    return create_coil(
        diameter=float(args["diameter"]),
        pitch=float(args["pitch"]),
        revolutions=float(args["revolutions"]),
        section_size=float(args["section_size"]),
        section_type=args.get("section_type", "circular"),
        operation=args.get("operation", "new_body"),
        name=args.get("name"),
        x=float(args.get("x", 0)),
        y=float(args.get("y", 0)),
        z=float(args.get("z", 0)),
        component_id=args.get("component_id"),
    )


def handle_create_pipe(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle create_pipe request.

    Creates a hollow tubular shape along a path.

    Args:
        args: Request arguments
            - path_sketch_id: ID of the sketch containing the path (required)
            - outer_diameter: Outer pipe diameter in mm (required)
            - wall_thickness: Pipe wall thickness in mm (required)
            - operation: "new_body", "join", "cut", "intersect" (default new_body)
            - name: Optional name for the body

    Returns:
        Dict with body and feature information
    """
    if "path_sketch_id" not in args:
        raise InvalidParameterError("path_sketch_id", None, reason="path_sketch_id is required")
    if "outer_diameter" not in args:
        raise InvalidParameterError("outer_diameter", None, reason="outer_diameter is required")
    if "wall_thickness" not in args:
        raise InvalidParameterError("wall_thickness", None, reason="wall_thickness is required")

    return create_pipe(
        path_sketch_id=args["path_sketch_id"],
        outer_diameter=float(args["outer_diameter"]),
        wall_thickness=float(args["wall_thickness"]),
        operation=args.get("operation", "new_body"),
        name=args.get("name"),
    )


# --- Phase 8b: Feature Pattern Handlers ---


def handle_rectangular_pattern(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle rectangular_pattern request.

    Creates a rectangular (linear) pattern of bodies or features.

    Args:
        args: Request arguments
            - entity_ids: List of body or feature IDs to pattern (required)
            - entity_type: "bodies" or "features" (required)
            - x_count: Number of columns (required, minimum 2)
            - x_spacing: Column spacing in mm (required)
            - x_axis: Direction for columns, "X", "Y", "Z" or edge_id (default X)
            - y_count: Number of rows (default 1 for 1D pattern)
            - y_spacing: Row spacing in mm (default 0, required if y_count > 1)
            - y_axis: Direction for rows (default perpendicular to x_axis)

    Returns:
        Dict with pattern feature info and created instance IDs
    """
    if "entity_ids" not in args:
        raise InvalidParameterError("entity_ids", None, reason="entity_ids is required")
    if "entity_type" not in args:
        raise InvalidParameterError("entity_type", None, reason="entity_type is required")
    if "x_count" not in args:
        raise InvalidParameterError("x_count", None, reason="x_count is required")
    if "x_spacing" not in args:
        raise InvalidParameterError("x_spacing", None, reason="x_spacing is required")

    return rectangular_pattern(
        entity_ids=args["entity_ids"],
        entity_type=args["entity_type"],
        x_count=int(args["x_count"]),
        x_spacing=float(args["x_spacing"]),
        x_axis=args.get("x_axis", "X"),
        y_count=int(args.get("y_count", 1)),
        y_spacing=float(args.get("y_spacing", 0.0)),
        y_axis=args.get("y_axis"),
    )


def handle_circular_pattern(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle circular_pattern request.

    Creates a circular (radial) pattern of bodies or features.

    Args:
        args: Request arguments
            - entity_ids: List of body or feature IDs to pattern (required)
            - entity_type: "bodies" or "features" (required)
            - axis: Rotation axis "X", "Y", "Z" or axis_id (required)
            - count: Number of instances including original (required, minimum 2)
            - total_angle: Total angle span in degrees (default 360)
            - is_symmetric: Distribute evenly within total_angle (default True)

    Returns:
        Dict with pattern feature info and created instance IDs
    """
    if "entity_ids" not in args:
        raise InvalidParameterError("entity_ids", None, reason="entity_ids is required")
    if "entity_type" not in args:
        raise InvalidParameterError("entity_type", None, reason="entity_type is required")
    if "axis" not in args:
        raise InvalidParameterError("axis", None, reason="axis is required")
    if "count" not in args:
        raise InvalidParameterError("count", None, reason="count is required")

    return circular_pattern(
        entity_ids=args["entity_ids"],
        entity_type=args["entity_type"],
        axis=args["axis"],
        count=int(args["count"]),
        total_angle=float(args.get("total_angle", 360.0)),
        is_symmetric=bool(args.get("is_symmetric", True)),
    )


def handle_mirror_feature(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle mirror_feature request.

    Mirrors bodies or features across a plane.

    Args:
        args: Request arguments
            - entity_ids: List of body or feature IDs to mirror (required)
            - entity_type: "bodies" or "features" (required)
            - mirror_plane: Mirror plane "XY", "YZ", "XZ" or plane_id (required)

    Returns:
        Dict with mirror feature info and created instance IDs
    """
    if "entity_ids" not in args:
        raise InvalidParameterError("entity_ids", None, reason="entity_ids is required")
    if "entity_type" not in args:
        raise InvalidParameterError("entity_type", None, reason="entity_type is required")
    if "mirror_plane" not in args:
        raise InvalidParameterError("mirror_plane", None, reason="mirror_plane is required")

    return mirror_feature(
        entity_ids=args["entity_ids"],
        entity_type=args["entity_type"],
        mirror_plane=args["mirror_plane"],
    )


# --- Phase 8c: Specialized Feature Handlers ---


def handle_create_thread(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle create_thread request.

    Adds threads to a cylindrical face.

    Args:
        args: Request arguments
            - face_id: ID of the cylindrical face to add thread to (required)
            - thread_type: Thread standard e.g. "ISO Metric profile" (required)
            - thread_size: Thread designation e.g. "M6x1" (required)
            - is_internal: Internal thread (default False)
            - is_full_length: Thread entire face length (default True)
            - thread_length: Custom thread length in mm (optional)
            - is_modeled: Create physical thread geometry (default False)

    Returns:
        Dict with thread feature info
    """
    if "face_id" not in args:
        raise InvalidParameterError("face_id", None, reason="face_id is required")
    if "thread_type" not in args:
        raise InvalidParameterError("thread_type", None, reason="thread_type is required")
    if "thread_size" not in args:
        raise InvalidParameterError("thread_size", None, reason="thread_size is required")

    return create_thread(
        face_id=args["face_id"],
        thread_type=args["thread_type"],
        thread_size=args["thread_size"],
        is_internal=bool(args.get("is_internal", False)),
        is_full_length=bool(args.get("is_full_length", True)),
        thread_length=float(args["thread_length"]) if "thread_length" in args else None,
        is_modeled=bool(args.get("is_modeled", False)),
    )


def handle_thicken(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle thicken request.

    Adds thickness to surface faces to create solid bodies.

    Args:
        args: Request arguments
            - face_ids: List of face IDs to thicken (required)
            - thickness: Thickness in mm (required)
            - direction: "positive", "negative", or "both" (default both)
            - operation: "new_body", "join", "cut", "intersect" (default new_body)
            - is_chain: Include tangent-connected faces (default True)

    Returns:
        Dict with thicken feature info and created bodies
    """
    if "face_ids" not in args:
        raise InvalidParameterError("face_ids", None, reason="face_ids is required")
    if "thickness" not in args:
        raise InvalidParameterError("thickness", None, reason="thickness is required")

    face_ids = args["face_ids"]
    if isinstance(face_ids, str):
        face_ids = [face_ids]

    return thicken(
        face_ids=face_ids,
        thickness=float(args["thickness"]),
        direction=args.get("direction", "both"),
        operation=args.get("operation", "new_body"),
        is_chain=bool(args.get("is_chain", True)),
    )


def handle_emboss(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle emboss request.

    Creates raised (emboss) or recessed (deboss) features from sketch profiles.

    Args:
        args: Request arguments
            - sketch_id: ID of the sketch containing profile/text (required)
            - face_id: ID of the face to emboss onto (required)
            - depth: Emboss/deboss depth in mm (required)
            - is_emboss: Emboss (True) or deboss (False) (default True)
            - profile_index: Index of profile to use (default 0)
            - taper_angle: Side taper angle in degrees (default 0)

    Returns:
        Dict with emboss feature info
    """
    if "sketch_id" not in args:
        raise InvalidParameterError("sketch_id", None, reason="sketch_id is required")
    if "face_id" not in args:
        raise InvalidParameterError("face_id", None, reason="face_id is required")
    if "depth" not in args:
        raise InvalidParameterError("depth", None, reason="depth is required")

    return emboss(
        sketch_id=args["sketch_id"],
        face_id=args["face_id"],
        depth=float(args["depth"]),
        is_emboss=bool(args.get("is_emboss", True)),
        profile_index=int(args.get("profile_index", 0)),
        taper_angle=float(args.get("taper_angle", 0)),
    )


# --- Construction Plane Handlers ---


def handle_create_offset_plane(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle offset plane creation request.

    Creates a construction plane offset from an existing plane or face.

    Args:
        args: Request arguments
            - base_plane: Base plane ("XY", "YZ", "XZ", face_id, or plane_id) (required)
            - offset: Offset distance in mm (required)
            - name: Optional name for the plane
            - component_id: Optional component ID

    Returns:
        Dict with plane info including id, origin, normal
    """
    if "base_plane" not in args:
        raise InvalidParameterError("base_plane", None, reason="base_plane is required")
    if "offset" not in args:
        raise InvalidParameterError("offset", None, reason="offset is required")

    return create_offset_plane(
        base_plane=str(args["base_plane"]),
        offset=float(args["offset"]),
        name=args.get("name"),
        component_id=args.get("component_id"),
    )


def handle_create_angle_plane(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle angle plane creation request.

    Creates a construction plane at an angle from a plane along an edge.

    Args:
        args: Request arguments
            - base_plane: Base plane ("XY", "YZ", "XZ", face_id, or plane_id) (required)
            - edge_id: ID of the linear edge to rotate around (required)
            - angle: Rotation angle in degrees (required)
            - name: Optional name for the plane
            - component_id: Optional component ID

    Returns:
        Dict with plane info including id, origin, normal
    """
    if "base_plane" not in args:
        raise InvalidParameterError("base_plane", None, reason="base_plane is required")
    if "edge_id" not in args:
        raise InvalidParameterError("edge_id", None, reason="edge_id is required")
    if "angle" not in args:
        raise InvalidParameterError("angle", None, reason="angle is required")

    return create_angle_plane(
        base_plane=str(args["base_plane"]),
        edge_id=str(args["edge_id"]),
        angle=float(args["angle"]),
        name=args.get("name"),
        component_id=args.get("component_id"),
    )


def handle_create_three_point_plane(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle three-point plane creation request.

    Creates a construction plane through three points.

    Args:
        args: Request arguments
            - point1: First point {x, y, z} in mm (required)
            - point2: Second point {x, y, z} in mm (required)
            - point3: Third point {x, y, z} in mm (required)
            - name: Optional name for the plane
            - component_id: Optional component ID

    Returns:
        Dict with plane info including id, origin, normal
    """
    if "point1" not in args:
        raise InvalidParameterError("point1", None, reason="point1 is required")
    if "point2" not in args:
        raise InvalidParameterError("point2", None, reason="point2 is required")
    if "point3" not in args:
        raise InvalidParameterError("point3", None, reason="point3 is required")

    return create_three_point_plane(
        point1=args["point1"],
        point2=args["point2"],
        point3=args["point3"],
        name=args.get("name"),
        component_id=args.get("component_id"),
    )


def handle_create_midplane(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle midplane creation request.

    Creates a construction plane midway between two planes or faces.

    Args:
        args: Request arguments
            - plane1: First plane ("XY", "YZ", "XZ", face_id, or plane_id) (required)
            - plane2: Second plane (must be parallel to plane1) (required)
            - name: Optional name for the plane
            - component_id: Optional component ID

    Returns:
        Dict with plane info including id, origin, normal
    """
    if "plane1" not in args:
        raise InvalidParameterError("plane1", None, reason="plane1 is required")
    if "plane2" not in args:
        raise InvalidParameterError("plane2", None, reason="plane2 is required")

    return create_midplane(
        plane1=str(args["plane1"]),
        plane2=str(args["plane2"]),
        name=args.get("name"),
        component_id=args.get("component_id"),
    )
