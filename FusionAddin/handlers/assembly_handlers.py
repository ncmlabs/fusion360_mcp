"""Assembly handlers for Fusion 360 MCP Add-in.

These handlers are called from the main thread via the EventManager
and provide assembly operations for components, occurrences, and joints.
"""

from typing import Dict, Any

from operations.assembly_ops import (
    create_component,
    get_components,
    get_component_by_id,
    activate_component,
    get_occurrences,
    move_occurrence,
    create_joint,
    create_joint_between_occurrences,
    get_joints,
    get_joint_by_id,
    get_component_bodies,
)
from shared.exceptions import InvalidParameterError


# --- Component Handlers ---

def handle_create_component(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle create_component request.

    Creates a new component in the design.

    Args:
        args: Request arguments
            - name: Component name (required)
            - transform: Optional transform dict with translation

    Returns:
        Dict with component and occurrence info
    """
    if "name" not in args:
        raise InvalidParameterError("name", None, reason="name is required")

    return create_component(
        name=args["name"],
        transform=args.get("transform"),
    )


def handle_get_components(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle get_components request.

    Lists all components in the design.

    Args:
        args: Request arguments (none required)

    Returns:
        Dict with list of component summaries
    """
    return get_components()


def handle_get_component_by_id(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle get_component_by_id request.

    Gets detailed info about a specific component.

    Args:
        args: Request arguments
            - component_id: Component ID to retrieve (required)

    Returns:
        Dict with full component info
    """
    if "component_id" not in args:
        raise InvalidParameterError("component_id", None, reason="component_id is required")

    return get_component_by_id(
        component_id=args["component_id"],
    )


def handle_activate_component(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle activate_component request.

    Activates a component for editing.

    Args:
        args: Request arguments
            - component_id: Component ID to activate (required)

    Returns:
        Dict confirming activation
    """
    if "component_id" not in args:
        raise InvalidParameterError("component_id", None, reason="component_id is required")

    return activate_component(
        component_id=args["component_id"],
    )


def handle_get_component_bodies(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle get_component_bodies request.

    Gets all bodies within a specific component.

    Args:
        args: Request arguments
            - component_id: Component ID to get bodies from (required)

    Returns:
        Dict with list of body summaries
    """
    if "component_id" not in args:
        raise InvalidParameterError("component_id", None, reason="component_id is required")

    return get_component_bodies(
        component_id=args["component_id"],
    )


# --- Occurrence Handlers ---

def handle_get_occurrences(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle get_occurrences request.

    Lists all occurrences in the design or within a component.

    Args:
        args: Request arguments
            - component_id: Optional component ID to filter occurrences

    Returns:
        Dict with list of occurrence info
    """
    return get_occurrences(
        component_id=args.get("component_id"),
    )


def handle_move_occurrence(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle move_occurrence request.

    Moves an occurrence to a new position.

    Args:
        args: Request arguments
            - occurrence_id: Occurrence ID to move (required)
            - x: X translation in mm (default 0)
            - y: Y translation in mm (default 0)
            - z: Z translation in mm (default 0)

    Returns:
        Dict with updated occurrence info
    """
    if "occurrence_id" not in args:
        raise InvalidParameterError("occurrence_id", None, reason="occurrence_id is required")

    return move_occurrence(
        occurrence_id=args["occurrence_id"],
        x=float(args.get("x", 0.0)),
        y=float(args.get("y", 0.0)),
        z=float(args.get("z", 0.0)),
    )


# --- Joint Handlers ---

def handle_create_joint(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle create_joint request.

    Creates a joint between two geometry entities.

    Args:
        args: Request arguments
            - geometry1_id: First geometry entity ID (required)
            - geometry2_id: Second geometry entity ID (required)
            - joint_type: Type of joint (default "rigid")
                Options: rigid, revolute, slider, cylindrical, pin_slot, planar, ball

    Returns:
        Dict with joint info
    """
    if "geometry1_id" not in args:
        raise InvalidParameterError("geometry1_id", None, reason="geometry1_id is required")
    if "geometry2_id" not in args:
        raise InvalidParameterError("geometry2_id", None, reason="geometry2_id is required")

    return create_joint(
        geometry1_id=args["geometry1_id"],
        geometry2_id=args["geometry2_id"],
        joint_type=args.get("joint_type", "rigid"),
    )


def handle_create_joint_between_occurrences(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle create_joint_between_occurrences request.

    Creates a joint between two occurrences using their origins.

    Args:
        args: Request arguments
            - occurrence1_id: First occurrence ID (required)
            - occurrence2_id: Second occurrence ID (required)
            - joint_type: Type of joint (default "rigid")
                Options: rigid, revolute, slider, cylindrical, pin_slot, planar, ball

    Returns:
        Dict with joint info
    """
    if "occurrence1_id" not in args:
        raise InvalidParameterError("occurrence1_id", None, reason="occurrence1_id is required")
    if "occurrence2_id" not in args:
        raise InvalidParameterError("occurrence2_id", None, reason="occurrence2_id is required")

    return create_joint_between_occurrences(
        occurrence1_id=args["occurrence1_id"],
        occurrence2_id=args["occurrence2_id"],
        joint_type=args.get("joint_type", "rigid"),
    )


def handle_get_joints(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle get_joints request.

    Lists all joints in the design.

    Args:
        args: Request arguments (none required)

    Returns:
        Dict with list of joint info
    """
    return get_joints()


def handle_get_joint_by_id(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle get_joint_by_id request.

    Gets detailed info about a specific joint.

    Args:
        args: Request arguments
            - joint_id: Joint ID to retrieve (required)

    Returns:
        Dict with joint info
    """
    if "joint_id" not in args:
        raise InvalidParameterError("joint_id", None, reason="joint_id is required")

    return get_joint_by_id(
        joint_id=args["joint_id"],
    )
