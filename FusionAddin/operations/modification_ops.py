"""Modification operations for Fusion 360 MCP Add-in.

These operations modify existing geometry in Fusion 360 - move, rotate,
modify parameters, delete entities, and edit sketches.

CRITICAL: Use defineAsTranslate/defineAsRotate for move/rotate operations
to preserve parametric relationships. NEVER use defineAsFreeMove.
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
from serializers.body_serializer import BodySerializer
from serializers.feature_serializer import FeatureSerializer
from shared.exceptions import (
    DesignStateError,
    FeatureError,
    InvalidParameterError,
    EntityNotFoundError,
)


def _get_active_design() -> Any:
    """Get the active Fusion 360 design.

    Returns:
        Fusion Design object

    Raises:
        DesignStateError: If no design is active
    """
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


def _get_body(body_id: str) -> Any:
    """Get a body by ID.

    Args:
        body_id: The body's stable ID

    Returns:
        Fusion BRepBody object

    Raises:
        EntityNotFoundError: If body not found
    """
    design = _get_active_design()
    registry = get_registry()

    body = registry.get_body(body_id)

    if not body:
        # Try to find by name
        root = design.rootComponent
        for brep_body in root.bRepBodies:
            if brep_body.name == body_id:
                body = brep_body
                registry.register_body(body)
                break

        if not body:
            for occurrence in root.allOccurrences:
                for brep_body in occurrence.component.bRepBodies:
                    if brep_body.name == body_id:
                        body = brep_body
                        registry.register_body(body)
                        break
                if body:
                    break

    if not body:
        available = registry.get_available_body_ids()
        raise EntityNotFoundError("Body", body_id, available)

    return body


def _get_feature(feature_id: str) -> Any:
    """Get a feature by ID.

    Args:
        feature_id: The feature's stable ID

    Returns:
        Fusion Feature object

    Raises:
        EntityNotFoundError: If feature not found
    """
    design = _get_active_design()
    registry = get_registry()

    feature = registry.get_feature(feature_id)

    if not feature:
        # Try to find by name in timeline
        timeline = design.timeline
        for i in range(timeline.count):
            item = timeline.item(i)
            if item.entity:
                entity = item.entity
                if hasattr(entity, 'name') and entity.name == feature_id:
                    feature = entity
                    registry.register_feature(feature)
                    break

    if not feature:
        available = registry.get_available_feature_ids()
        raise EntityNotFoundError("Feature", feature_id, available)

    return feature


def _get_parameter(param_id: str) -> Any:
    """Get a parameter by ID/name.

    Args:
        param_id: The parameter's name or ID

    Returns:
        Fusion Parameter object

    Raises:
        EntityNotFoundError: If parameter not found
    """
    design = _get_active_design()
    registry = get_registry()

    param = registry.get_parameter(param_id)

    if not param:
        # Try to find by name
        all_params = design.allParameters
        for p in all_params:
            if p.name == param_id:
                param = p
                registry.register_parameter(param)
                break

        # Also check user parameters
        if not param:
            user_params = design.userParameters
            for p in user_params:
                if p.name == param_id:
                    param = p
                    registry.register_parameter(param)
                    break

    if not param:
        available = registry.get_available_parameter_ids()
        raise EntityNotFoundError("Parameter", param_id, available)

    return param


def _serialize_bounding_box(body: Any) -> Dict[str, Any]:
    """Serialize body bounding box.

    Args:
        body: Fusion BRepBody object

    Returns:
        Dict with bounding box min/max coordinates
    """
    bbox = body.boundingBox
    return {
        "min": [bbox.minPoint.x * 10, bbox.minPoint.y * 10, bbox.minPoint.z * 10],
        "max": [bbox.maxPoint.x * 10, bbox.maxPoint.y * 10, bbox.maxPoint.z * 10],
    }


def move_body(
    body_id: str,
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
) -> Dict[str, Any]:
    """Move a body by translation.

    Uses defineAsTranslate to preserve parametric relationships.
    This creates a Move feature in the timeline.

    Args:
        body_id: ID of the body to move
        x: Translation in X direction (mm)
        y: Translation in Y direction (mm)
        z: Translation in Z direction (mm)

    Returns:
        Dict with success, feature info, and new position

    Raises:
        EntityNotFoundError: If body not found
        FeatureError: If move operation fails
    """
    if x == 0 and y == 0 and z == 0:
        raise InvalidParameterError(
            "translation",
            [x, y, z],
            reason="At least one of x, y, z must be non-zero"
        )

    body = _get_body(body_id)
    design = _get_active_design()
    registry = get_registry()

    try:
        component = body.parentComponent

        # Create move feature input
        move_features = component.features.moveFeatures

        # Create an object collection containing the body to move
        bodies_to_move = adsk.core.ObjectCollection.create()
        bodies_to_move.add(body)

        # Create move input
        move_input = move_features.createInput2(bodies_to_move)

        # Convert mm to cm for Fusion API
        x_cm = x / 10.0
        y_cm = y / 10.0
        z_cm = z / 10.0

        # Create translation vector
        translation = adsk.core.Vector3D.create(x_cm, y_cm, z_cm)

        # CRITICAL: Use defineAsTranslate to preserve parametric relationships
        # DO NOT use defineAsFreeMove as it breaks parametric history
        move_input.defineAsTranslate(translation)

        # Execute the move
        move_feature = move_features.add(move_input)

        if not move_feature:
            raise FeatureError(
                "move_body",
                "Move operation failed"
            )

        # Register the new feature
        feature_id = registry.register_feature(move_feature)

        # Serialize result
        feature_serializer = FeatureSerializer(registry)

        result = {
            "success": True,
            "feature": {
                "id": feature_id,
                "type": "MoveFeature",
                "translation": {"x": x, "y": y, "z": z},
            },
            "new_position": {
                "bounding_box": _serialize_bounding_box(body),
            },
        }

        return result

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError(
            "move_body",
            f"Failed to move body: {str(e)}",
            fusion_error=str(e)
        )


def rotate_body(
    body_id: str,
    axis: str,
    angle: float,
    origin_x: float = 0.0,
    origin_y: float = 0.0,
    origin_z: float = 0.0,
) -> Dict[str, Any]:
    """Rotate a body around an axis.

    Uses defineAsRotate to preserve parametric relationships.
    This creates a Move feature in the timeline.

    Args:
        body_id: ID of the body to rotate
        axis: Axis to rotate around ("X", "Y", "Z")
        angle: Rotation angle in degrees
        origin_x: X coordinate of rotation origin (mm)
        origin_y: Y coordinate of rotation origin (mm)
        origin_z: Z coordinate of rotation origin (mm)

    Returns:
        Dict with success, feature info, and new orientation

    Raises:
        EntityNotFoundError: If body not found
        InvalidParameterError: If axis or angle is invalid
        FeatureError: If rotate operation fails
    """
    if axis.upper() not in ["X", "Y", "Z"]:
        raise InvalidParameterError(
            "axis",
            axis,
            valid_values=["X", "Y", "Z"],
            reason="Axis must be X, Y, or Z"
        )

    if angle == 0:
        raise InvalidParameterError(
            "angle",
            angle,
            reason="Angle must be non-zero"
        )

    body = _get_body(body_id)
    design = _get_active_design()
    registry = get_registry()

    try:
        component = body.parentComponent

        # Create move feature input
        move_features = component.features.moveFeatures

        # Create an object collection containing the body to rotate
        bodies_to_rotate = adsk.core.ObjectCollection.create()
        bodies_to_rotate.add(body)

        # Create move input
        move_input = move_features.createInput2(bodies_to_rotate)

        # Convert mm to cm for origin
        origin_cm = adsk.core.Point3D.create(
            origin_x / 10.0,
            origin_y / 10.0,
            origin_z / 10.0
        )

        # Create axis vector based on specified axis
        axis_upper = axis.upper()
        if axis_upper == "X":
            axis_vector = adsk.core.Vector3D.create(1, 0, 0)
        elif axis_upper == "Y":
            axis_vector = adsk.core.Vector3D.create(0, 1, 0)
        else:  # Z
            axis_vector = adsk.core.Vector3D.create(0, 0, 1)

        # Create axis for rotation
        rotation_axis = adsk.core.InfiniteLine3D.create(origin_cm, axis_vector)

        # Convert angle to radians
        angle_rad = math.radians(angle)

        # CRITICAL: Use defineAsRotate to preserve parametric relationships
        # DO NOT use defineAsFreeMove as it breaks parametric history
        move_input.defineAsRotate(
            rotation_axis,
            adsk.core.ValueInput.createByReal(angle_rad)
        )

        # Execute the rotation
        move_feature = move_features.add(move_input)

        if not move_feature:
            raise FeatureError(
                "rotate_body",
                "Rotate operation failed"
            )

        # Register the new feature
        feature_id = registry.register_feature(move_feature)

        result = {
            "success": True,
            "feature": {
                "id": feature_id,
                "type": "MoveFeature",
                "rotation": {
                    "axis": axis,
                    "angle": angle,
                    "origin": {"x": origin_x, "y": origin_y, "z": origin_z},
                },
            },
            "new_position": {
                "bounding_box": _serialize_bounding_box(body),
            },
        }

        return result

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError(
            "rotate_body",
            f"Failed to rotate body: {str(e)}",
            fusion_error=str(e)
        )


def modify_feature(
    feature_id: str,
    parameters: Dict[str, Any],
) -> Dict[str, Any]:
    """Modify feature parameters.

    Supports modifying extrusion distance, fillet/chamfer radius, etc.
    by accessing the feature's Definition object.

    Args:
        feature_id: ID of the feature to modify
        parameters: Dict of parameter names to new values
            - For ExtrudeFeature: {"distance": float}
            - For FilletFeature: {"radius": float}
            - For ChamferFeature: {"distance": float}
            - For RevolveFeature: {"angle": float}

    Returns:
        Dict with success, feature info, and old/new values

    Raises:
        EntityNotFoundError: If feature not found
        InvalidParameterError: If parameters are invalid
        FeatureError: If modification fails
    """
    if not parameters:
        raise InvalidParameterError(
            "parameters",
            parameters,
            reason="At least one parameter must be specified"
        )

    feature = _get_feature(feature_id)
    design = _get_active_design()
    registry = get_registry()

    try:
        changes = {}

        # Handle different feature types
        feature_type = type(feature).__name__

        if hasattr(feature, 'extentDefinition'):
            # Extrude feature
            if "distance" in parameters:
                new_distance = parameters["distance"]
                if new_distance <= 0:
                    raise InvalidParameterError(
                        "distance",
                        new_distance,
                        min_value=0.001,
                        reason="Distance must be positive"
                    )

                extent = feature.extentDefinition
                if hasattr(extent, 'distance'):
                    old_value = extent.distance.value * 10  # cm to mm

                    # Update the distance
                    extent.distance.value = new_distance / 10.0  # mm to cm

                    changes["distance"] = {
                        "old": old_value,
                        "new": new_distance,
                    }

        elif hasattr(feature, 'edgeSets'):
            # Fillet feature
            if "radius" in parameters:
                new_radius = parameters["radius"]
                if new_radius <= 0:
                    raise InvalidParameterError(
                        "radius",
                        new_radius,
                        min_value=0.001,
                        reason="Radius must be positive"
                    )

                # Get first edge set
                if feature.edgeSets.count > 0:
                    edge_set = feature.edgeSets.item(0)
                    if hasattr(edge_set, 'radius'):
                        old_value = edge_set.radius.value * 10  # cm to mm

                        # Update the radius
                        edge_set.radius.value = new_radius / 10.0  # mm to cm

                        changes["radius"] = {
                            "old": old_value,
                            "new": new_radius,
                        }

        elif hasattr(feature, 'chamferType'):
            # Chamfer feature
            if "distance" in parameters:
                new_distance = parameters["distance"]
                if new_distance <= 0:
                    raise InvalidParameterError(
                        "distance",
                        new_distance,
                        min_value=0.001,
                        reason="Distance must be positive"
                    )

                if hasattr(feature, 'distance'):
                    old_value = feature.distance.value * 10  # cm to mm

                    # Update the distance
                    feature.distance.value = new_distance / 10.0  # mm to cm

                    changes["distance"] = {
                        "old": old_value,
                        "new": new_distance,
                    }

        elif hasattr(feature, 'angle'):
            # Revolve feature
            if "angle" in parameters:
                new_angle = parameters["angle"]
                if new_angle <= 0 or new_angle > 360:
                    raise InvalidParameterError(
                        "angle",
                        new_angle,
                        min_value=0.001,
                        max_value=360,
                        reason="Angle must be between 0 and 360"
                    )

                old_value = math.degrees(feature.angle.value)

                # Update the angle
                feature.angle.value = math.radians(new_angle)

                changes["angle"] = {
                    "old": old_value,
                    "new": new_angle,
                }

        if not changes:
            raise FeatureError(
                "modify_feature",
                f"Feature type '{feature_type}' does not support the specified parameters",
                suggestion="Check the feature type and use appropriate parameters"
            )

        result = {
            "success": True,
            "feature": {
                "id": feature_id,
                "type": feature_type,
            },
            "changes": changes,
        }

        return result

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError(
            "modify_feature",
            f"Failed to modify feature: {str(e)}",
            fusion_error=str(e)
        )


def update_parameter(
    name: str,
    expression: str,
) -> Dict[str, Any]:
    """Update a parameter value.

    Supports value expressions like "50 mm", "25.4 in", or expressions
    referencing other parameters like "d1 * 2".

    Args:
        name: Parameter name
        expression: New value expression (e.g., "50 mm", "d1 * 2")

    Returns:
        Dict with success, old/new values

    Raises:
        EntityNotFoundError: If parameter not found
        InvalidParameterError: If expression is invalid
        FeatureError: If update fails
    """
    if not expression:
        raise InvalidParameterError(
            "expression",
            expression,
            reason="Expression cannot be empty"
        )

    param = _get_parameter(name)
    design = _get_active_design()
    registry = get_registry()

    try:
        # Store old values
        old_expression = param.expression
        old_value = param.value

        # Get units for display
        units = param.unit if hasattr(param, 'unit') else ""

        # Update the parameter expression
        param.expression = expression

        # Get new value after update
        new_value = param.value

        result = {
            "success": True,
            "parameter": {
                "name": name,
                "unit": units,
            },
            "changes": {
                "expression": {
                    "old": old_expression,
                    "new": expression,
                },
                "value": {
                    "old": old_value * 10 if units in ["mm", "cm", "m", "in"] else old_value,
                    "new": new_value * 10 if units in ["mm", "cm", "m", "in"] else new_value,
                },
            },
        }

        return result

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError(
            "update_parameter",
            f"Failed to update parameter: {str(e)}",
            fusion_error=str(e),
            suggestion="Check that the expression is valid. Examples: '50 mm', '2 in', 'd1 * 2'"
        )


def delete_body(body_id: str) -> Dict[str, Any]:
    """Delete a body from the design.

    This removes the body using the Remove feature, which preserves
    timeline history.

    Args:
        body_id: ID of the body to delete

    Returns:
        Dict with success and deleted entity info

    Raises:
        EntityNotFoundError: If body not found
        FeatureError: If deletion fails
    """
    body = _get_body(body_id)
    design = _get_active_design()
    registry = get_registry()

    try:
        component = body.parentComponent

        # Store body info before deletion
        body_name = body.name if hasattr(body, 'name') else body_id

        # Use removeFeatures to delete the body (preserves timeline)
        remove_features = component.features.removeFeatures

        # Create object collection with the body
        bodies_to_remove = adsk.core.ObjectCollection.create()
        bodies_to_remove.add(body)

        # Create remove feature
        remove_feature = remove_features.add(bodies_to_remove)

        if not remove_feature:
            raise FeatureError(
                "delete_body",
                "Failed to create remove feature"
            )

        # Register the remove feature
        feature_id = registry.register_feature(remove_feature)

        # Remove from registry
        # Note: The registry will be refreshed on next query

        result = {
            "success": True,
            "deleted": {
                "id": body_id,
                "name": body_name,
                "type": "Body",
            },
            "feature": {
                "id": feature_id,
                "type": "RemoveFeature",
            },
        }

        return result

    except Exception as e:
        if isinstance(e, (EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError(
            "delete_body",
            f"Failed to delete body: {str(e)}",
            fusion_error=str(e)
        )


def delete_feature(feature_id: str) -> Dict[str, Any]:
    """Delete a feature from the timeline.

    This removes the feature from the design timeline. Dependent features
    may be affected or deleted as well.

    Args:
        feature_id: ID of the feature to delete

    Returns:
        Dict with success, deleted feature info, and any affected features

    Raises:
        EntityNotFoundError: If feature not found
        FeatureError: If deletion fails
    """
    feature = _get_feature(feature_id)
    design = _get_active_design()
    registry = get_registry()

    try:
        # Store feature info before deletion
        feature_name = feature.name if hasattr(feature, 'name') else feature_id
        feature_type = type(feature).__name__

        # Get timeline object for the feature
        timeline_obj = feature.timelineObject if hasattr(feature, 'timelineObject') else None

        affected_features = []

        # Check for dependent features
        if timeline_obj:
            dependents = timeline_obj.childObjects if hasattr(timeline_obj, 'childObjects') else None
            if dependents:
                for dep in dependents:
                    if hasattr(dep, 'entity') and dep.entity:
                        affected_features.append({
                            "id": dep.entity.name if hasattr(dep.entity, 'name') else "unknown",
                            "type": type(dep.entity).__name__,
                        })

        # Delete the feature
        # Use the deleteMe method on the feature
        delete_success = feature.deleteMe()

        if not delete_success:
            raise FeatureError(
                "delete_feature",
                "Feature deletion failed",
                suggestion="The feature may have dependent features that prevent deletion"
            )

        result = {
            "success": True,
            "deleted": {
                "id": feature_id,
                "name": feature_name,
                "type": feature_type,
            },
        }

        if affected_features:
            result["affected_features"] = affected_features
            result["warning"] = "Dependent features may have been affected or deleted"

        return result

    except Exception as e:
        if isinstance(e, (EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError(
            "delete_feature",
            f"Failed to delete feature: {str(e)}",
            fusion_error=str(e),
            suggestion="Check if the feature has dependent features that prevent deletion"
        )


def edit_sketch(
    sketch_id: str,
    curve_id: str,
    properties: Dict[str, Any],
) -> Dict[str, Any]:
    """Edit a sketch curve.

    Supports modifying curve properties like endpoints, center, radius.

    Args:
        sketch_id: ID of the sketch
        curve_id: ID of the curve to modify (e.g., "Sketch1_line_0")
        properties: Dict of properties to modify
            - For lines: {"start_x", "start_y", "end_x", "end_y"}
            - For circles: {"center_x", "center_y", "radius"}
            - For arcs: {"center_x", "center_y", "radius", "start_angle", "end_angle"}

    Returns:
        Dict with success and old/new values

    Raises:
        EntityNotFoundError: If sketch or curve not found
        InvalidParameterError: If properties are invalid
        FeatureError: If edit fails
    """
    if not properties:
        raise InvalidParameterError(
            "properties",
            properties,
            reason="At least one property must be specified"
        )

    design = _get_active_design()
    registry = get_registry()

    # Get sketch
    sketch = registry.get_sketch(sketch_id)

    if not sketch:
        # Try to find by name
        root = design.rootComponent
        for sk in root.sketches:
            if sk.name == sketch_id:
                sketch = sk
                registry.register_sketch(sketch)
                break

        if not sketch:
            available = registry.get_available_sketch_ids()
            raise EntityNotFoundError("Sketch", sketch_id, available)

    # Get curve from sub-entity registry
    curve = registry.get_sub_entity(curve_id)

    if not curve:
        # Try to parse curve_id and get from sketch
        # Format: "{sketch_id}_{type}_{index}"
        parts = curve_id.split("_")
        if len(parts) >= 3:
            curve_type = parts[-2]
            try:
                curve_index = int(parts[-1])

                if curve_type == "line":
                    if curve_index < sketch.sketchCurves.sketchLines.count:
                        curve = sketch.sketchCurves.sketchLines.item(curve_index)
                elif curve_type == "circle":
                    if curve_index < sketch.sketchCurves.sketchCircles.count:
                        curve = sketch.sketchCurves.sketchCircles.item(curve_index)
                elif curve_type == "arc":
                    if curve_index < sketch.sketchCurves.sketchArcs.count:
                        curve = sketch.sketchCurves.sketchArcs.item(curve_index)
            except (ValueError, IndexError):
                pass

    if not curve:
        raise EntityNotFoundError(
            "SketchCurve",
            curve_id,
            suggestion="Use get_sketch_by_id with include_curves=True to see available curves"
        )

    try:
        changes = {}
        curve_type = type(curve).__name__

        # Handle different curve types
        if "SketchLine" in curve_type:
            # Line modification
            if any(k in properties for k in ["start_x", "start_y"]):
                start_pt = curve.startSketchPoint
                old_start = {
                    "x": start_pt.geometry.x * 10,
                    "y": start_pt.geometry.y * 10,
                }
                new_x = properties.get("start_x", old_start["x"]) / 10.0
                new_y = properties.get("start_y", old_start["y"]) / 10.0
                start_pt.move(
                    adsk.core.Vector3D.create(
                        new_x - start_pt.geometry.x,
                        new_y - start_pt.geometry.y,
                        0
                    )
                )
                changes["start"] = {
                    "old": old_start,
                    "new": {"x": new_x * 10, "y": new_y * 10},
                }

            if any(k in properties for k in ["end_x", "end_y"]):
                end_pt = curve.endSketchPoint
                old_end = {
                    "x": end_pt.geometry.x * 10,
                    "y": end_pt.geometry.y * 10,
                }
                new_x = properties.get("end_x", old_end["x"]) / 10.0
                new_y = properties.get("end_y", old_end["y"]) / 10.0
                end_pt.move(
                    adsk.core.Vector3D.create(
                        new_x - end_pt.geometry.x,
                        new_y - end_pt.geometry.y,
                        0
                    )
                )
                changes["end"] = {
                    "old": old_end,
                    "new": {"x": new_x * 10, "y": new_y * 10},
                }

        elif "SketchCircle" in curve_type:
            # Circle modification
            if any(k in properties for k in ["center_x", "center_y"]):
                center = curve.centerSketchPoint
                old_center = {
                    "x": center.geometry.x * 10,
                    "y": center.geometry.y * 10,
                }
                new_x = properties.get("center_x", old_center["x"]) / 10.0
                new_y = properties.get("center_y", old_center["y"]) / 10.0
                center.move(
                    adsk.core.Vector3D.create(
                        new_x - center.geometry.x,
                        new_y - center.geometry.y,
                        0
                    )
                )
                changes["center"] = {
                    "old": old_center,
                    "new": {"x": new_x * 10, "y": new_y * 10},
                }

            if "radius" in properties:
                old_radius = curve.radius * 10  # cm to mm
                new_radius = properties["radius"]
                if new_radius <= 0:
                    raise InvalidParameterError(
                        "radius",
                        new_radius,
                        min_value=0.001,
                        reason="Radius must be positive"
                    )
                curve.radius = new_radius / 10.0  # mm to cm
                changes["radius"] = {
                    "old": old_radius,
                    "new": new_radius,
                }

        elif "SketchArc" in curve_type:
            # Arc modification
            if any(k in properties for k in ["center_x", "center_y"]):
                center = curve.centerSketchPoint
                old_center = {
                    "x": center.geometry.x * 10,
                    "y": center.geometry.y * 10,
                }
                new_x = properties.get("center_x", old_center["x"]) / 10.0
                new_y = properties.get("center_y", old_center["y"]) / 10.0
                center.move(
                    adsk.core.Vector3D.create(
                        new_x - center.geometry.x,
                        new_y - center.geometry.y,
                        0
                    )
                )
                changes["center"] = {
                    "old": old_center,
                    "new": {"x": new_x * 10, "y": new_y * 10},
                }

        if not changes:
            raise FeatureError(
                "edit_sketch",
                f"Curve type '{curve_type}' does not support the specified properties",
                suggestion="Check the curve type and use appropriate properties"
            )

        result = {
            "success": True,
            "sketch_id": sketch_id,
            "curve_id": curve_id,
            "curve_type": curve_type,
            "changes": changes,
        }

        return result

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError(
            "edit_sketch",
            f"Failed to edit sketch curve: {str(e)}",
            fusion_error=str(e)
        )
