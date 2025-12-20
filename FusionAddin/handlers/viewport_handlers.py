"""Viewport handlers for Fusion 360 MCP Add-in.

These handlers are called from the main thread via the EventManager
and provide viewport control and screenshot operations.
"""

from typing import Dict, Any

from operations.viewport_ops import (
    take_screenshot,
    set_camera,
    get_camera,
    set_view,
    fit_view,
)


def handle_take_screenshot(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle take_screenshot request.

    Captures the viewport as a PNG image.

    Args:
        args: Request arguments
            - file_path: Optional path to save image
            - view: View to capture ("current" or standard view name)
            - width: Image width in pixels (default 1920)
            - height: Image height in pixels (default 1080)
            - return_base64: Return base64 encoded image (default True)

    Returns:
        Dict with image data and metadata
    """
    return take_screenshot(
        file_path=args.get("file_path"),
        view=args.get("view", "current"),
        width=int(args.get("width", 1920)),
        height=int(args.get("height", 1080)),
        return_base64=bool(args.get("return_base64", True)),
    )


def handle_set_camera(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle set_camera request.

    Sets the viewport camera position and orientation.

    Args:
        args: Request arguments
            - eye_x: Camera eye X position in mm (required)
            - eye_y: Camera eye Y position in mm (required)
            - eye_z: Camera eye Z position in mm (required)
            - target_x: Camera target X in mm (default 0)
            - target_y: Camera target Y in mm (default 0)
            - target_z: Camera target Z in mm (default 0)
            - up_x: Up vector X (default 0)
            - up_y: Up vector Y (default 0)
            - up_z: Up vector Z (default 1)
            - smooth_transition: Animate transition (default True)

    Returns:
        Dict with camera state after change
    """
    from shared.exceptions import InvalidParameterError

    # Validate required parameters
    if "eye_x" not in args:
        raise InvalidParameterError("eye_x", None, reason="eye_x is required")
    if "eye_y" not in args:
        raise InvalidParameterError("eye_y", None, reason="eye_y is required")
    if "eye_z" not in args:
        raise InvalidParameterError("eye_z", None, reason="eye_z is required")

    return set_camera(
        eye_x=float(args["eye_x"]),
        eye_y=float(args["eye_y"]),
        eye_z=float(args["eye_z"]),
        target_x=float(args.get("target_x", 0)),
        target_y=float(args.get("target_y", 0)),
        target_z=float(args.get("target_z", 0)),
        up_x=float(args.get("up_x", 0)),
        up_y=float(args.get("up_y", 0)),
        up_z=float(args.get("up_z", 1)),
        smooth_transition=bool(args.get("smooth_transition", True)),
    )


def handle_get_camera(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle get_camera request.

    Gets the current viewport camera state.

    Args:
        args: Request arguments (none required)

    Returns:
        Dict with current camera state
    """
    return get_camera()


def handle_set_view(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle set_view request.

    Sets the viewport to a standard named view.

    Args:
        args: Request arguments
            - view: Named view (required)
                   Options: front, back, top, bottom,
                            left, right, isometric, trimetric, home
            - smooth_transition: Animate the change (default True)

    Returns:
        Dict with view name and camera state
    """
    from shared.exceptions import InvalidParameterError

    if "view" not in args:
        raise InvalidParameterError("view", None, reason="view is required")

    return set_view(
        view=args["view"],
        smooth_transition=bool(args.get("smooth_transition", True)),
    )


def handle_fit_view(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle fit_view request.

    Fits the viewport to show specific entities or all geometry.

    Args:
        args: Request arguments
            - entity_ids: Optional list of entity IDs to fit to
            - smooth_transition: Animate the change (default True)

    Returns:
        Dict with fitted_to and camera state
    """
    entity_ids = args.get("entity_ids")
    if entity_ids and not isinstance(entity_ids, list):
        entity_ids = [entity_ids]

    return fit_view(
        entity_ids=entity_ids,
        smooth_transition=bool(args.get("smooth_transition", True)),
    )
