"""Validation handlers for Fusion 360 MCP Add-in.

These handlers are called from the main thread via the EventManager
and provide measurement, interference detection, and validation operations.
"""

from typing import Dict, Any, List

from operations.validation_ops import (
    measure_distance,
    measure_angle,
    check_interference,
    get_body_properties,
    get_sketch_status,
)
from shared.exceptions import InvalidParameterError


# --- Measurement Handlers ---

def handle_measure_distance(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle measure_distance request.

    Measures the minimum distance between two entities (bodies, faces,
    edges, or vertices).

    Args:
        args: Request arguments
            - entity1_id: ID of the first entity (required)
            - entity2_id: ID of the second entity (required)

    Returns:
        Dict with distance (mm), point1, point2 (closest points)
    """
    if "entity1_id" not in args:
        raise InvalidParameterError(
            "entity1_id", None, reason="entity1_id is required"
        )
    if "entity2_id" not in args:
        raise InvalidParameterError(
            "entity2_id", None, reason="entity2_id is required"
        )

    return measure_distance(
        entity1_id=args["entity1_id"],
        entity2_id=args["entity2_id"],
    )


def handle_measure_angle(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle measure_angle request.

    Measures the angle between two planar faces or linear edges.

    Args:
        args: Request arguments
            - entity1_id: ID of the first entity (face or edge, required)
            - entity2_id: ID of the second entity (face or edge, required)

    Returns:
        Dict with angle in degrees (0-180)
    """
    if "entity1_id" not in args:
        raise InvalidParameterError(
            "entity1_id", None, reason="entity1_id is required"
        )
    if "entity2_id" not in args:
        raise InvalidParameterError(
            "entity2_id", None, reason="entity2_id is required"
        )

    return measure_angle(
        entity1_id=args["entity1_id"],
        entity2_id=args["entity2_id"],
    )


# --- Interference Detection Handler ---

def handle_check_interference(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle check_interference request.

    Analyzes overlapping volumes between bodies in the design.

    Args:
        args: Request arguments
            - body_ids: Optional list of body IDs to check.
                       If not provided, checks all bodies.

    Returns:
        Dict with:
            - has_interference: True if collisions found
            - interferences: List of {body1, body2, volume} dicts
            - bodies_checked: Number of bodies analyzed
    """
    body_ids = args.get("body_ids")

    # Validate body_ids if provided
    if body_ids is not None:
        if not isinstance(body_ids, list):
            raise InvalidParameterError(
                "body_ids",
                body_ids,
                reason="body_ids must be a list of body ID strings"
            )

    return check_interference(body_ids=body_ids)


# --- Body Properties Handler ---

def handle_get_body_properties(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle get_body_properties request.

    Returns detailed physical properties of a body including
    volume, area, center of mass, bounding box, and topology counts.

    Args:
        args: Request arguments
            - body_id: ID of the body to analyze (required)

    Returns:
        Dict with properties:
            - volume: mm³
            - area: mm²
            - center_of_mass: {x, y, z} in mm
            - bounding_box: {min, max} arrays
            - dimensions: {width, depth, height} in mm
            - faces_count, edges_count, vertices_count
    """
    if "body_id" not in args:
        raise InvalidParameterError(
            "body_id", None, reason="body_id is required"
        )

    return get_body_properties(body_id=args["body_id"])


# --- Sketch Status Handler ---

def handle_get_sketch_status(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle get_sketch_status request.

    Returns constraint status and profile validity of a sketch.

    Args:
        args: Request arguments
            - sketch_id: ID of the sketch to analyze (required)

    Returns:
        Dict with:
            - is_fully_constrained: True if all curves constrained
            - under_constrained_count: Number of under-constrained curves
            - profiles_count: Number of closed profiles
            - curves_count: Total curves
            - constraints_count: Number of constraints
            - dimensions_count: Number of dimensions
            - has_valid_profiles: True if has at least one profile
    """
    if "sketch_id" not in args:
        raise InvalidParameterError(
            "sketch_id", None, reason="sketch_id is required"
        )

    return get_sketch_status(sketch_id=args["sketch_id"])
