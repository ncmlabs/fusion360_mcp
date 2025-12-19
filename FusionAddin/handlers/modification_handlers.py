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
