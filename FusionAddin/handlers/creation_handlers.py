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
