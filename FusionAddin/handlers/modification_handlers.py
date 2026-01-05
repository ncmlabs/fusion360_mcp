"""Modification handlers for Fusion 360 MCP Add-in.

These handlers are called from the main thread via the EventManager
and provide modification operations for bodies, features, and sketches.
"""

from typing import Dict, Any

from operations.modification_ops import (
    move_body,
    rotate_body,
    modify_feature,
    update_parameter,
    delete_body,
    delete_feature,
    edit_sketch,
)
from operations.feature_ops import (
    combine,
    split_body,
    shell,
)
from shared.exceptions import InvalidParameterError


# --- Move/Rotate Handlers ---

def handle_move_body(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle move_body request.

    Moves a body by translation. Uses defineAsTranslate to preserve
    parametric relationships.

    Args:
        args: Request arguments
            - body_id: ID of the body to move (required)
            - x: Translation in X direction in mm (default 0)
            - y: Translation in Y direction in mm (default 0)
            - z: Translation in Z direction in mm (default 0)

    Returns:
        Dict with success, feature info, and new position
    """
    if "body_id" not in args:
        raise InvalidParameterError("body_id", None, reason="body_id is required")

    x = float(args.get("x", 0))
    y = float(args.get("y", 0))
    z = float(args.get("z", 0))

    if x == 0 and y == 0 and z == 0:
        raise InvalidParameterError(
            "translation",
            [x, y, z],
            reason="At least one of x, y, z must be non-zero"
        )

    return move_body(
        body_id=args["body_id"],
        x=x,
        y=y,
        z=z,
    )


def handle_rotate_body(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle rotate_body request.

    Rotates a body around an axis. Uses defineAsRotate to preserve
    parametric relationships.

    Args:
        args: Request arguments
            - body_id: ID of the body to rotate (required)
            - axis: Axis to rotate around - "X", "Y", "Z" (required)
            - angle: Rotation angle in degrees (required)
            - origin_x: X coordinate of rotation origin in mm (default 0)
            - origin_y: Y coordinate of rotation origin in mm (default 0)
            - origin_z: Z coordinate of rotation origin in mm (default 0)

    Returns:
        Dict with success, feature info, and new orientation
    """
    if "body_id" not in args:
        raise InvalidParameterError("body_id", None, reason="body_id is required")
    if "axis" not in args:
        raise InvalidParameterError("axis", None, reason="axis is required")
    if "angle" not in args:
        raise InvalidParameterError("angle", None, reason="angle is required")

    return rotate_body(
        body_id=args["body_id"],
        axis=args["axis"],
        angle=float(args["angle"]),
        origin_x=float(args.get("origin_x", 0)),
        origin_y=float(args.get("origin_y", 0)),
        origin_z=float(args.get("origin_z", 0)),
    )


# --- Feature Modification Handlers ---

def handle_modify_feature(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle modify_feature request.

    Modifies feature parameters like extrusion distance, fillet radius, etc.

    Args:
        args: Request arguments
            - feature_id: ID of the feature to modify (required)
            - parameters: Dict of parameter names to new values (required)
                - For ExtrudeFeature: {"distance": float}
                - For FilletFeature: {"radius": float}
                - For ChamferFeature: {"distance": float}
                - For RevolveFeature: {"angle": float}

    Returns:
        Dict with success, feature info, and old/new values
    """
    if "feature_id" not in args:
        raise InvalidParameterError("feature_id", None, reason="feature_id is required")
    if "parameters" not in args:
        raise InvalidParameterError("parameters", None, reason="parameters dict is required")

    parameters = args["parameters"]
    if not isinstance(parameters, dict):
        raise InvalidParameterError(
            "parameters",
            parameters,
            reason="parameters must be a dict"
        )

    # Convert numeric values
    converted_params = {}
    for key, value in parameters.items():
        if isinstance(value, (int, float)):
            converted_params[key] = float(value)
        else:
            converted_params[key] = value

    return modify_feature(
        feature_id=args["feature_id"],
        parameters=converted_params,
    )


# --- Parameter Update Handlers ---

def handle_update_parameter(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle update_parameter request.

    Updates a parameter value using an expression.

    Args:
        args: Request arguments
            - name: Parameter name (required)
            - expression: New value expression (required)
                Examples: "50 mm", "25.4 in", "d1 * 2"

    Returns:
        Dict with success and old/new values
    """
    if "name" not in args:
        raise InvalidParameterError("name", None, reason="name is required")
    if "expression" not in args:
        raise InvalidParameterError("expression", None, reason="expression is required")

    return update_parameter(
        name=args["name"],
        expression=str(args["expression"]),
    )


# --- Delete Handlers ---

def handle_delete_body(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle delete_body request.

    Deletes a body from the design using a Remove feature.

    Args:
        args: Request arguments
            - body_id: ID of the body to delete (required)

    Returns:
        Dict with success and deleted entity info
    """
    if "body_id" not in args:
        raise InvalidParameterError("body_id", None, reason="body_id is required")

    return delete_body(body_id=args["body_id"])


def handle_delete_feature(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle delete_feature request.

    Deletes a feature from the timeline.

    Args:
        args: Request arguments
            - feature_id: ID of the feature to delete (required)

    Returns:
        Dict with success, deleted feature info, and any affected features
    """
    if "feature_id" not in args:
        raise InvalidParameterError("feature_id", None, reason="feature_id is required")

    return delete_feature(feature_id=args["feature_id"])


# --- Sketch Edit Handlers ---

def handle_edit_sketch(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle edit_sketch request.

    Edits a sketch curve's properties.

    Args:
        args: Request arguments
            - sketch_id: ID of the sketch (required)
            - curve_id: ID of the curve to modify (required)
            - properties: Dict of properties to modify (required)
                - For lines: {"start_x", "start_y", "end_x", "end_y"}
                - For circles: {"center_x", "center_y", "radius"}
                - For arcs: {"center_x", "center_y", "radius"}

    Returns:
        Dict with success and old/new values
    """
    if "sketch_id" not in args:
        raise InvalidParameterError("sketch_id", None, reason="sketch_id is required")
    if "curve_id" not in args:
        raise InvalidParameterError("curve_id", None, reason="curve_id is required")
    if "properties" not in args:
        raise InvalidParameterError("properties", None, reason="properties dict is required")

    properties = args["properties"]
    if not isinstance(properties, dict):
        raise InvalidParameterError(
            "properties",
            properties,
            reason="properties must be a dict"
        )

    # Convert numeric values
    converted_props = {}
    for key, value in properties.items():
        if isinstance(value, (int, float)):
            converted_props[key] = float(value)
        else:
            converted_props[key] = value

    return edit_sketch(
        sketch_id=args["sketch_id"],
        curve_id=args["curve_id"],
        properties=converted_props,
    )


# --- MODIFY Menu Handlers ---


def handle_combine(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle combine request.

    Combines multiple bodies using boolean operations (join, cut, intersect).

    Args:
        args: Request arguments
            - target_body_id: ID of the body to modify (required)
            - tool_body_ids: List of body IDs to combine with (required)
            - operation: "join", "cut", or "intersect" (default "join")
            - keep_tools: Keep tool bodies after operation (default False)

    Returns:
        Dict with success, feature info, and resulting body
    """
    if "target_body_id" not in args:
        raise InvalidParameterError("target_body_id", None, reason="target_body_id is required")
    if "tool_body_ids" not in args:
        raise InvalidParameterError("tool_body_ids", None, reason="tool_body_ids is required")

    tool_body_ids = args["tool_body_ids"]
    if not isinstance(tool_body_ids, list):
        tool_body_ids = [tool_body_ids]

    return combine(
        target_body_id=args["target_body_id"],
        tool_body_ids=tool_body_ids,
        operation=args.get("operation", "join"),
        keep_tools=bool(args.get("keep_tools", False)),
    )


def handle_split_body(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle split_body request.

    Splits a body using a plane or face.

    Args:
        args: Request arguments
            - body_id: ID of the body to split (required)
            - splitting_tool: Face ID, plane ID, or "XY"/"YZ"/"XZ" (required)
            - extend_splitting_tool: Extend tool to fully split (default True)

    Returns:
        Dict with success, feature info, and resulting bodies
    """
    if "body_id" not in args:
        raise InvalidParameterError("body_id", None, reason="body_id is required")
    if "splitting_tool" not in args:
        raise InvalidParameterError("splitting_tool", None, reason="splitting_tool is required")

    return split_body(
        body_id=args["body_id"],
        splitting_tool=args["splitting_tool"],
        extend_splitting_tool=bool(args.get("extend_splitting_tool", True)),
    )


def handle_shell(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle shell request.

    Creates a hollow shell by removing faces and adding wall thickness.

    Args:
        args: Request arguments
            - body_id: ID of the body to shell (required)
            - face_ids: List of face IDs to remove (required)
            - thickness: Wall thickness in mm (required)
            - direction: "inside" or "outside" (default "inside")

    Returns:
        Dict with success, feature info, and resulting body
    """
    if "body_id" not in args:
        raise InvalidParameterError("body_id", None, reason="body_id is required")
    if "face_ids" not in args:
        raise InvalidParameterError("face_ids", None, reason="face_ids is required")
    if "thickness" not in args:
        raise InvalidParameterError("thickness", None, reason="thickness is required")

    face_ids = args["face_ids"]
    if not isinstance(face_ids, list):
        face_ids = [face_ids]

    return shell(
        body_id=args["body_id"],
        face_ids=face_ids,
        thickness=float(args["thickness"]),
        direction=args.get("direction", "inside"),
    )


# NOTE: The following handlers are implemented but disabled pending debugging:
# - handle_draft: Add draft angle to faces
# - handle_scale: Scale bodies
# - handle_offset_face: Offset faces
# - handle_split_face: Split faces
# See feature_ops.py for the core implementations.
