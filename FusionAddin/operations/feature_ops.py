"""Feature operations for Fusion 360 MCP Add-in.

These operations create features like extrusions, revolutions, fillets,
chamfers, and holes in Fusion 360, returning structured results.
"""

from typing import Dict, Any, Optional, List, Tuple
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
    SelectionError,
)


# Map operation names to Fusion operation types
OPERATION_MAP = {
    "new_body": adsk.fusion.FeatureOperations.NewBodyFeatureOperation if FUSION_AVAILABLE else 0,
    "join": adsk.fusion.FeatureOperations.JoinFeatureOperation if FUSION_AVAILABLE else 1,
    "cut": adsk.fusion.FeatureOperations.CutFeatureOperation if FUSION_AVAILABLE else 2,
    "intersect": adsk.fusion.FeatureOperations.IntersectFeatureOperation if FUSION_AVAILABLE else 3,
}


def _get_active_design() -> Any:
    """Get the active Fusion 360 design."""
    if not FUSION_AVAILABLE:
        raise DesignStateError(
            "not_available",
            "Fusion 360 API not available. Running outside of Fusion 360."
        )

    app = adsk.core.Application.get()
    if not app:
        raise DesignStateError("no_application", "Cannot get Fusion 360 application instance.")

    product = app.activeProduct
    if not product:
        raise DesignStateError("no_product", "No active product. Please open a design.")

    design = adsk.fusion.Design.cast(product)
    if not design:
        raise DesignStateError("not_design", "Active product is not a Design.")

    return design


def _get_sketch(sketch_id: str) -> Tuple[Any, Any]:
    """Get a sketch by ID.

    Returns:
        Tuple of (sketch, component)
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

    # Get component from sketch's parent
    component = sketch.parentComponent

    return sketch, component


def _get_body(body_id: str) -> Any:
    """Get a body by ID."""
    design = _get_active_design()
    registry = get_registry()

    body = registry.get_body(body_id)

    if not body:
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


def _serialize_feature_result(
    feature: Any,
    registry: Any,
    bodies: Optional[List[Any]] = None
) -> Dict[str, Any]:
    """Serialize feature operation result."""
    feature_serializer = FeatureSerializer(registry)
    body_serializer = BodySerializer(registry)

    result = {
        "feature": feature_serializer.serialize_feature(feature),
    }

    # Add body info if bodies were created/modified
    if bodies:
        result["bodies"] = [body_serializer.serialize_summary(b) for b in bodies]

    return result


def extrude(
    sketch_id: str,
    distance: float,
    direction: str = "positive",
    operation: str = "new_body",
    profile_index: int = 0,
    name: Optional[str] = None,
    taper_angle: float = 0.0,
) -> Dict[str, Any]:
    """Extrude a sketch profile.

    Args:
        sketch_id: ID of the sketch containing the profile
        distance: Extrusion distance in mm
        direction: "positive", "negative", or "symmetric"
        operation: "new_body", "join", "cut", or "intersect"
        profile_index: Index of profile to extrude (0 for first/only)
        name: Optional name for created body
        taper_angle: Taper angle in degrees (0 for straight extrusion)

    Returns:
        Dict with feature_id, body_id, and geometry info

    Raises:
        InvalidParameterError: If parameters are invalid
        EntityNotFoundError: If sketch not found
        FeatureError: If extrusion fails
    """
    if distance <= 0:
        raise InvalidParameterError("distance", distance, min_value=0.001)

    if direction not in ["positive", "negative", "symmetric"]:
        raise InvalidParameterError("direction", direction, valid_values=["positive", "negative", "symmetric"])

    if operation not in OPERATION_MAP:
        raise InvalidParameterError("operation", operation, valid_values=list(OPERATION_MAP.keys()))

    sketch, component = _get_sketch(sketch_id)
    registry = get_registry()

    # Check for profiles
    if sketch.profiles.count == 0:
        raise FeatureError(
            "extrude",
            "Sketch has no closed profiles to extrude",
            affected_entities=[sketch_id]
        )

    if profile_index >= sketch.profiles.count:
        raise InvalidParameterError(
            "profile_index",
            profile_index,
            max_value=sketch.profiles.count - 1,
            reason=f"Sketch has only {sketch.profiles.count} profiles"
        )

    try:
        profile = sketch.profiles.item(profile_index)

        # Create extrusion input
        extrudes = component.features.extrudeFeatures
        extrude_input = extrudes.createInput(profile, OPERATION_MAP[operation])

        # Convert mm to cm
        dist_cm = distance / 10.0

        # Set extent based on direction
        if direction == "symmetric":
            # Symmetric extent
            extent = adsk.fusion.SymmetricExtentDefinition.create(
                adsk.core.ValueInput.createByReal(dist_cm / 2),
                True  # Symmetric
            )
            extrude_input.setSymmetricExtent(
                adsk.core.ValueInput.createByReal(dist_cm / 2),
                True
            )
        else:
            # One direction
            is_negative = (direction == "negative")
            extrude_input.setDistanceExtent(
                is_negative,
                adsk.core.ValueInput.createByReal(dist_cm)
            )

        # Set taper angle if specified
        if abs(taper_angle) > 0.001:
            taper_rad = math.radians(taper_angle)
            extrude_input.taperAngle = adsk.core.ValueInput.createByReal(taper_rad)

        # Create the extrusion
        extrude_feature = extrudes.add(extrude_input)

        if not extrude_feature:
            raise FeatureError("extrude", "Extrusion operation failed")

        # Register feature
        feature_id = registry.register_feature(extrude_feature)

        # Get and register created/modified bodies
        created_bodies = []
        for i in range(extrude_feature.bodies.count):
            body = extrude_feature.bodies.item(i)
            if name and extrude_feature.bodies.count == 1:
                body.name = name
            registry.register_body(body)
            created_bodies.append(body)

        # Serialize result
        result = _serialize_feature_result(extrude_feature, registry, created_bodies)
        result["success"] = True

        return result

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError("extrude", f"Failed to extrude: {str(e)}", fusion_error=str(e))


def revolve(
    sketch_id: str,
    axis: str,
    angle: float = 360.0,
    operation: str = "new_body",
    profile_index: int = 0,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """Revolve a sketch profile around an axis.

    Args:
        sketch_id: ID of the sketch containing the profile
        axis: Axis to revolve around ("X", "Y", "Z", or axis line ID)
        angle: Revolution angle in degrees (360 for full revolution)
        operation: "new_body", "join", "cut", or "intersect"
        profile_index: Index of profile to revolve
        name: Optional name for created body

    Returns:
        Dict with feature_id, body_id, and geometry info

    Raises:
        InvalidParameterError: If parameters are invalid
        EntityNotFoundError: If sketch not found
        FeatureError: If revolve fails
    """
    if angle <= 0 or angle > 360:
        raise InvalidParameterError("angle", angle, min_value=0.001, max_value=360)

    if operation not in OPERATION_MAP:
        raise InvalidParameterError("operation", operation, valid_values=list(OPERATION_MAP.keys()))

    sketch, component = _get_sketch(sketch_id)
    registry = get_registry()

    if sketch.profiles.count == 0:
        raise FeatureError("revolve", "Sketch has no closed profiles", affected_entities=[sketch_id])

    if profile_index >= sketch.profiles.count:
        raise InvalidParameterError("profile_index", profile_index, max_value=sketch.profiles.count - 1)

    try:
        profile = sketch.profiles.item(profile_index)

        # Resolve axis
        axis_upper = axis.upper()
        if axis_upper == "X":
            axis_obj = component.xConstructionAxis
        elif axis_upper == "Y":
            axis_obj = component.yConstructionAxis
        elif axis_upper == "Z":
            axis_obj = component.zConstructionAxis
        else:
            # Try to get axis from sketch curves (first line found)
            axis_obj = None
            for curve in sketch.sketchCurves.sketchLines:
                axis_obj = curve
                break
            if not axis_obj:
                raise InvalidParameterError(
                    "axis", axis,
                    valid_values=["X", "Y", "Z"],
                    reason="No valid axis found. Use X, Y, Z or ensure sketch has a line for axis."
                )

        # Create revolve input
        revolves = component.features.revolveFeatures
        revolve_input = revolves.createInput(profile, axis_obj, OPERATION_MAP[operation])

        # Set angle
        angle_rad = math.radians(angle)
        revolve_input.setAngleExtent(False, adsk.core.ValueInput.createByReal(angle_rad))

        # Create the revolve
        revolve_feature = revolves.add(revolve_input)

        if not revolve_feature:
            raise FeatureError("revolve", "Revolve operation failed")

        # Register feature
        feature_id = registry.register_feature(revolve_feature)

        # Get and register created bodies
        created_bodies = []
        for i in range(revolve_feature.bodies.count):
            body = revolve_feature.bodies.item(i)
            if name and revolve_feature.bodies.count == 1:
                body.name = name
            registry.register_body(body)
            created_bodies.append(body)

        result = _serialize_feature_result(revolve_feature, registry, created_bodies)
        result["success"] = True

        return result

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError("revolve", f"Failed to revolve: {str(e)}", fusion_error=str(e))


def fillet(
    body_id: str,
    edge_ids: List[str],
    radius: float,
) -> Dict[str, Any]:
    """Apply fillet to edges of a body.

    Args:
        body_id: ID of the body containing the edges
        edge_ids: List of edge IDs to fillet
        radius: Fillet radius in mm

    Returns:
        Dict with feature_id and updated body info

    Raises:
        InvalidParameterError: If radius is invalid
        EntityNotFoundError: If body or edges not found
        FeatureError: If fillet fails
    """
    if radius <= 0:
        raise InvalidParameterError("radius", radius, min_value=0.001)

    if not edge_ids:
        raise InvalidParameterError("edge_ids", edge_ids, reason="At least one edge ID is required")

    body = _get_body(body_id)
    registry = get_registry()

    try:
        # Get parent component from body
        component = body.parentComponent

        # Collect edges
        edges = adsk.core.ObjectCollection.create()
        for edge_id in edge_ids:
            edge = registry.get_sub_entity(edge_id)
            if edge:
                edges.add(edge)
            else:
                # Try to find edge by index
                if "_edge_" in edge_id:
                    try:
                        idx = int(edge_id.split("_edge_")[1])
                        if idx < body.edges.count:
                            edge = body.edges.item(idx)
                            edges.add(edge)
                    except (ValueError, IndexError):
                        pass

        if edges.count == 0:
            raise EntityNotFoundError(
                "Edge",
                edge_ids[0],
                suggestion="Use get_body_by_id with include_edges=True to see available edges"
            )

        # Create fillet
        fillets = component.features.filletFeatures
        fillet_input = fillets.createInput()

        # Add edges with constant radius
        radius_cm = radius / 10.0
        fillet_input.addConstantRadiusEdgeSet(
            edges,
            adsk.core.ValueInput.createByReal(radius_cm),
            True  # Is tangent chain
        )

        fillet_feature = fillets.add(fillet_input)

        if not fillet_feature:
            raise FeatureError("fillet", "Fillet operation failed")

        # Register feature
        feature_id = registry.register_feature(fillet_feature)

        result = _serialize_feature_result(fillet_feature, registry, [body])
        result["success"] = True
        result["radius"] = radius

        return result

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError("fillet", f"Failed to apply fillet: {str(e)}", fusion_error=str(e))


def chamfer(
    body_id: str,
    edge_ids: List[str],
    distance: float,
    distance2: Optional[float] = None,
) -> Dict[str, Any]:
    """Apply chamfer to edges of a body.

    Args:
        body_id: ID of the body containing the edges
        edge_ids: List of edge IDs to chamfer
        distance: Chamfer distance in mm
        distance2: Optional second distance for asymmetric chamfer

    Returns:
        Dict with feature_id and updated body info

    Raises:
        InvalidParameterError: If distance is invalid
        EntityNotFoundError: If body or edges not found
        FeatureError: If chamfer fails
    """
    if distance <= 0:
        raise InvalidParameterError("distance", distance, min_value=0.001)

    if distance2 is not None and distance2 <= 0:
        raise InvalidParameterError("distance2", distance2, min_value=0.001)

    if not edge_ids:
        raise InvalidParameterError("edge_ids", edge_ids, reason="At least one edge ID is required")

    body = _get_body(body_id)
    registry = get_registry()

    try:
        component = body.parentComponent

        # Collect edges
        edges = adsk.core.ObjectCollection.create()
        for edge_id in edge_ids:
            edge = registry.get_sub_entity(edge_id)
            if edge:
                edges.add(edge)
            else:
                if "_edge_" in edge_id:
                    try:
                        idx = int(edge_id.split("_edge_")[1])
                        if idx < body.edges.count:
                            edge = body.edges.item(idx)
                            edges.add(edge)
                    except (ValueError, IndexError):
                        pass

        if edges.count == 0:
            raise EntityNotFoundError("Edge", edge_ids[0])

        # Create chamfer
        chamfers = component.features.chamferFeatures
        chamfer_input = chamfers.createInput2()

        dist_cm = distance / 10.0

        if distance2 is not None:
            # Two distance chamfer
            dist2_cm = distance2 / 10.0
            chamfer_input.chamferType = adsk.fusion.ChamferType.TwoDistancesChamferType
            chamfer_input.setToTwoDistances(
                edges.item(0),
                adsk.core.ValueInput.createByReal(dist_cm),
                adsk.core.ValueInput.createByReal(dist2_cm)
            )
        else:
            # Equal distance chamfer
            chamfer_input.chamferType = adsk.fusion.ChamferType.EqualDistanceChamferType
            chamfer_input.setToEqualDistance(
                edges,
                adsk.core.ValueInput.createByReal(dist_cm)
            )

        chamfer_feature = chamfers.add(chamfer_input)

        if not chamfer_feature:
            raise FeatureError("chamfer", "Chamfer operation failed")

        feature_id = registry.register_feature(chamfer_feature)

        result = _serialize_feature_result(chamfer_feature, registry, [body])
        result["success"] = True
        result["distance"] = distance
        if distance2:
            result["distance2"] = distance2

        return result

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError("chamfer", f"Failed to apply chamfer: {str(e)}", fusion_error=str(e))


def sweep(
    profile_sketch_id: str,
    path_sketch_id: str,
    profile_index: int = 0,
    operation: str = "new_body",
    orientation: str = "perpendicular",
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """Sweep a profile along a path.

    Args:
        profile_sketch_id: ID of the sketch containing the profile
        path_sketch_id: ID of the sketch containing the sweep path
        profile_index: Index of profile to sweep (0 for first/only)
        operation: "new_body", "join", "cut", or "intersect"
        orientation: "perpendicular" or "parallel"
        name: Optional name for created body

    Returns:
        Dict with feature_id, body_id, and geometry info

    Raises:
        InvalidParameterError: If parameters are invalid
        EntityNotFoundError: If sketch not found
        FeatureError: If sweep fails
    """
    if operation not in OPERATION_MAP:
        raise InvalidParameterError("operation", operation, valid_values=list(OPERATION_MAP.keys()))

    if orientation not in ["perpendicular", "parallel"]:
        raise InvalidParameterError("orientation", orientation, valid_values=["perpendicular", "parallel"])

    profile_sketch, component = _get_sketch(profile_sketch_id)
    path_sketch, _ = _get_sketch(path_sketch_id)
    registry = get_registry()

    # Check for profile
    if profile_sketch.profiles.count == 0:
        raise FeatureError(
            "sweep",
            "Profile sketch has no closed profiles to sweep",
            affected_entities=[profile_sketch_id]
        )

    if profile_index >= profile_sketch.profiles.count:
        raise InvalidParameterError(
            "profile_index",
            profile_index,
            max_value=profile_sketch.profiles.count - 1,
            reason=f"Profile sketch has only {profile_sketch.profiles.count} profiles"
        )

    # Check for path curves
    path_curves = path_sketch.sketchCurves
    if path_curves.count == 0:
        raise FeatureError(
            "sweep",
            "Path sketch has no curves for sweep path",
            affected_entities=[path_sketch_id]
        )

    try:
        profile = profile_sketch.profiles.item(profile_index)

        # Collect all curves from the path sketch into an ObjectCollection
        curves_collection = adsk.core.ObjectCollection.create()

        # Add all curves from the path sketch
        for i in range(path_curves.sketchLines.count):
            curves_collection.add(path_curves.sketchLines.item(i))
        for i in range(path_curves.sketchArcs.count):
            curves_collection.add(path_curves.sketchArcs.item(i))
        for i in range(path_curves.sketchFittedSplines.count):
            curves_collection.add(path_curves.sketchFittedSplines.item(i))

        if curves_collection.count == 0:
            raise FeatureError("sweep", "No valid path curves found in path sketch")

        # Create a Path object from the curves
        path = component.features.createPath(curves_collection)

        if not path:
            raise FeatureError("sweep", "Failed to create path from sketch curves")

        # Create sweep input
        sweeps = component.features.sweepFeatures
        sweep_input = sweeps.createInput(profile, path, OPERATION_MAP[operation])

        # Set orientation
        if orientation == "parallel":
            sweep_input.orientation = adsk.fusion.SweepOrientationTypes.ParallelOrientationType
        else:
            sweep_input.orientation = adsk.fusion.SweepOrientationTypes.PerpendicularOrientationType

        # Create the sweep
        sweep_feature = sweeps.add(sweep_input)

        if not sweep_feature:
            raise FeatureError("sweep", "Sweep operation failed")

        # Register feature
        feature_id = registry.register_feature(sweep_feature)

        # Get and register created bodies
        created_bodies = []
        for i in range(sweep_feature.bodies.count):
            body = sweep_feature.bodies.item(i)
            if name and sweep_feature.bodies.count == 1:
                body.name = name
            registry.register_body(body)
            created_bodies.append(body)

        result = _serialize_feature_result(sweep_feature, registry, created_bodies)
        result["success"] = True
        result["orientation"] = orientation

        return result

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError("sweep", f"Failed to sweep: {str(e)}", fusion_error=str(e))


def loft(
    sketch_ids: List[str],
    profile_indices: Optional[List[int]] = None,
    operation: str = "new_body",
    is_solid: bool = True,
    is_closed: bool = False,
    name: Optional[str] = None,
    target_body_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a loft between multiple profiles.

    Args:
        sketch_ids: List of sketch IDs (in order from start to end)
        profile_indices: Optional list of profile indices for each sketch
        operation: "new_body", "join", "cut", or "intersect"
        is_solid: Create solid (True) or surface (False)
        is_closed: Close the loft ends
        name: Optional name for created body
        target_body_id: Body ID for boolean operations (cut/join/intersect).
                       When provided, this body will participate in the operation.
                       Required for cut operations to work correctly.

    Returns:
        Dict with feature_id, body_id, and geometry info

    Raises:
        InvalidParameterError: If parameters are invalid
        EntityNotFoundError: If sketch not found
        FeatureError: If loft fails
    """
    if len(sketch_ids) < 2:
        raise InvalidParameterError(
            "sketch_ids", sketch_ids,
            reason="At least 2 sketches are required for loft"
        )

    if operation not in OPERATION_MAP:
        raise InvalidParameterError("operation", operation, valid_values=list(OPERATION_MAP.keys()))

    # Validate target_body_id for boolean operations
    is_boolean_operation = operation in ["cut", "join", "intersect"]
    if is_boolean_operation and target_body_id is None:
        raise InvalidParameterError(
            "target_body_id",
            None,
            reason=f"target_body_id is required for '{operation}' operation. "
                   f"Specify the body to {operation} from/with."
        )

    # Get target body for boolean operations
    target_body = None
    if target_body_id is not None:
        target_body = _get_body(target_body_id)

    if profile_indices is None:
        profile_indices = [0] * len(sketch_ids)
    elif len(profile_indices) != len(sketch_ids):
        raise InvalidParameterError(
            "profile_indices", profile_indices,
            reason=f"profile_indices length ({len(profile_indices)}) must match sketch_ids length ({len(sketch_ids)})"
        )

    registry = get_registry()

    # Get all sketches and profiles
    profiles = []
    component = None
    for i, sketch_id in enumerate(sketch_ids):
        sketch, comp = _get_sketch(sketch_id)
        if component is None:
            component = comp

        if sketch.profiles.count == 0:
            raise FeatureError(
                "loft",
                f"Sketch '{sketch_id}' has no closed profiles",
                affected_entities=[sketch_id]
            )

        profile_idx = profile_indices[i]
        if profile_idx >= sketch.profiles.count:
            raise InvalidParameterError(
                f"profile_indices[{i}]",
                profile_idx,
                max_value=sketch.profiles.count - 1,
                reason=f"Sketch '{sketch_id}' has only {sketch.profiles.count} profiles"
            )

        profiles.append(sketch.profiles.item(profile_idx))

    try:
        # Create loft input
        lofts = component.features.loftFeatures
        loft_input = lofts.createInput(OPERATION_MAP[operation])

        # Add profiles as loft sections
        for profile in profiles:
            loft_input.loftSections.add(profile)

        # Set options
        loft_input.isSolid = is_solid
        loft_input.isClosed = is_closed

        # Set participant bodies for boolean operations
        if target_body is not None and is_boolean_operation:
            # participantBodies expects a list of BRepBody objects
            loft_input.participantBodies = [target_body]

        # Create the loft
        loft_feature = lofts.add(loft_input)

        if not loft_feature:
            raise FeatureError("loft", "Loft operation failed")

        # Register feature
        feature_id = registry.register_feature(loft_feature)

        # Get and register created bodies
        created_bodies = []
        for i in range(loft_feature.bodies.count):
            body = loft_feature.bodies.item(i)
            if name and loft_feature.bodies.count == 1:
                body.name = name
            registry.register_body(body)
            created_bodies.append(body)

        result = _serialize_feature_result(loft_feature, registry, created_bodies)
        result["success"] = True
        result["sections_count"] = len(profiles)
        result["is_solid"] = is_solid
        result["is_closed"] = is_closed

        return result

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError("loft", f"Failed to loft: {str(e)}", fusion_error=str(e))


def create_sphere(
    radius: float,
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
    name: Optional[str] = None,
    component_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a solid sphere primitive.

    Creates a sphere by drawing a semicircle and revolving it 360 degrees.

    Args:
        radius: Sphere radius in mm
        x: Center X position in mm
        y: Center Y position in mm
        z: Center Z position in mm
        name: Optional name for the body
        component_id: Optional component ID

    Returns:
        Dict with body and feature info

    Raises:
        InvalidParameterError: If radius is invalid
        FeatureError: If creation fails
    """
    if radius <= 0:
        raise InvalidParameterError("radius", radius, min_value=0.001)

    design = _get_active_design()
    registry = get_registry()

    try:
        # Get component
        if component_id:
            # Try to find component
            component = None
            root = design.rootComponent
            for occurrence in root.allOccurrences:
                if occurrence.component.name == component_id:
                    component = occurrence.component
                    break
            if not component:
                component = root
        else:
            component = design.rootComponent

        # Convert to cm
        radius_cm = radius / 10.0
        x_cm = x / 10.0
        y_cm = y / 10.0
        z_cm = z / 10.0

        # Create sketch on XY plane (offset by Z)
        planes = component.constructionPlanes
        sketches = component.sketches

        if abs(z_cm) > 0.0001:
            # Create offset plane
            plane_input = planes.createInput()
            offset = adsk.core.ValueInput.createByReal(z_cm)
            plane_input.setByOffset(component.xYConstructionPlane, offset)
            plane = planes.add(plane_input)
            sketch = sketches.add(plane)
        else:
            sketch = sketches.add(component.xYConstructionPlane)

        # Draw semicircle profile for revolve
        # Arc from (x, y+radius) to (x, y-radius) centered at (x, y)
        arcs = sketch.sketchCurves.sketchArcs
        lines = sketch.sketchCurves.sketchLines

        center = adsk.core.Point3D.create(x_cm, y_cm, 0)
        start_point = adsk.core.Point3D.create(x_cm, y_cm + radius_cm, 0)
        end_point = adsk.core.Point3D.create(x_cm, y_cm - radius_cm, 0)

        # Create semicircle arc
        arc = arcs.addByCenterStartSweep(center, start_point, math.pi)

        # Close with a line (the axis)
        axis_line = lines.addByTwoPoints(end_point, start_point)

        # Get the profile
        if sketch.profiles.count == 0:
            raise FeatureError("create_sphere", "Failed to create sphere profile")

        profile = sketch.profiles.item(0)

        # Revolve around the axis line
        revolves = component.features.revolveFeatures
        revolve_input = revolves.createInput(
            profile,
            axis_line,
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        )

        # Full 360 degree revolve
        revolve_input.setAngleExtent(False, adsk.core.ValueInput.createByReal(2 * math.pi))

        revolve_feature = revolves.add(revolve_input)

        if not revolve_feature:
            raise FeatureError("create_sphere", "Failed to create sphere")

        # Register feature
        feature_id = registry.register_feature(revolve_feature)

        # Get and register body
        body = revolve_feature.bodies.item(0)
        if name:
            body.name = name
        body_id = registry.register_body(body)

        # Serialize result
        body_serializer = BodySerializer(registry)

        return {
            "success": True,
            "body": body_serializer.serialize_summary(body),
            "feature": {
                "id": feature_id,
                "type": "SphereFeature",
            },
            "sphere": {
                "center": {"x": x, "y": y, "z": z},
                "radius": radius,
                "diameter": radius * 2,
                "volume": (4/3) * math.pi * (radius ** 3),
                "surface_area": 4 * math.pi * (radius ** 2),
            }
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError("create_sphere", f"Failed to create sphere: {str(e)}", fusion_error=str(e))


def create_torus(
    major_radius: float,
    minor_radius: float,
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
    name: Optional[str] = None,
    component_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a torus (donut/ring shape).

    Creates a torus by drawing a circle and revolving it around an offset axis.

    Args:
        major_radius: Distance from center to tube center in mm
        minor_radius: Tube radius in mm
        x: Center X position in mm
        y: Center Y position in mm
        z: Center Z position in mm
        name: Optional name for the body
        component_id: Optional component ID

    Returns:
        Dict with body and feature info

    Raises:
        InvalidParameterError: If radii are invalid
        FeatureError: If creation fails
    """
    if major_radius <= 0:
        raise InvalidParameterError("major_radius", major_radius, min_value=0.001)
    if minor_radius <= 0:
        raise InvalidParameterError("minor_radius", minor_radius, min_value=0.001)
    if minor_radius >= major_radius:
        raise InvalidParameterError(
            "minor_radius", minor_radius,
            reason=f"minor_radius ({minor_radius}) must be less than major_radius ({major_radius})"
        )

    design = _get_active_design()
    registry = get_registry()

    try:
        # Get component
        if component_id:
            component = None
            root = design.rootComponent
            for occurrence in root.allOccurrences:
                if occurrence.component.name == component_id:
                    component = occurrence.component
                    break
            if not component:
                component = root
        else:
            component = design.rootComponent

        # Convert to cm
        major_cm = major_radius / 10.0
        minor_cm = minor_radius / 10.0
        x_cm = x / 10.0
        y_cm = y / 10.0
        z_cm = z / 10.0

        # Create sketch on XZ plane (we'll revolve around Z axis)
        # This creates a torus lying flat in XY plane with hole along Z
        planes = component.constructionPlanes
        sketches = component.sketches

        sketch = sketches.add(component.xZConstructionPlane)

        # In XZ plane: sketch X = world X, sketch Y = world Z
        # Draw circle at (major_radius, 0) in sketch coords = world (major_radius, 0, 0)
        circles = sketch.sketchCurves.sketchCircles
        circle_center = adsk.core.Point3D.create(major_cm, 0, 0)
        circle = circles.addByCenterRadius(circle_center, minor_cm)

        # Get the profile
        if sketch.profiles.count == 0:
            raise FeatureError("create_torus", "Failed to create torus profile")

        profile = sketch.profiles.item(0)

        # Revolve around Z axis (perpendicular to XZ plane, through origin)
        revolves = component.features.revolveFeatures
        revolve_input = revolves.createInput(
            profile,
            component.zConstructionAxis,
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        )

        # Full 360 degree revolve
        revolve_input.setAngleExtent(False, adsk.core.ValueInput.createByReal(2 * math.pi))

        revolve_feature = revolves.add(revolve_input)

        if not revolve_feature:
            raise FeatureError("create_torus", "Failed to create torus")

        # Move to final position if needed
        if abs(x_cm) > 0.0001 or abs(y_cm) > 0.0001 or abs(z_cm) > 0.0001:
            body = revolve_feature.bodies.item(0)
            moves = component.features.moveFeatures
            move_input = moves.createInput2(body)

            # Create translation matrix
            transform = adsk.core.Matrix3D.create()
            transform.translation = adsk.core.Vector3D.create(x_cm, y_cm, z_cm)
            move_input.defineAsFreeMove(transform)
            moves.add(move_input)

        # Register feature
        feature_id = registry.register_feature(revolve_feature)

        # Get and register body
        body = revolve_feature.bodies.item(0)
        if name:
            body.name = name
        body_id = registry.register_body(body)

        # Serialize result
        body_serializer = BodySerializer(registry)

        # Calculate torus properties
        volume = 2 * (math.pi ** 2) * major_radius * (minor_radius ** 2)
        surface_area = 4 * (math.pi ** 2) * major_radius * minor_radius

        return {
            "success": True,
            "body": body_serializer.serialize_summary(body),
            "feature": {
                "id": feature_id,
                "type": "TorusFeature",
            },
            "torus": {
                "center": {"x": x, "y": y, "z": z},
                "major_radius": major_radius,
                "minor_radius": minor_radius,
                "volume": volume,
                "surface_area": surface_area,
            }
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError("create_torus", f"Failed to create torus: {str(e)}", fusion_error=str(e))


def create_coil(
    diameter: float,
    pitch: float,
    revolutions: float,
    section_size: float,
    section_type: str = "circular",
    operation: str = "new_body",
    name: Optional[str] = None,
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
    component_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a helix/spring shape (coil).

    NOTE: This feature is currently NOT SUPPORTED via the Fusion 360 API.
    The CoilFeatures API does not expose a createInput() method, and the
    text command workaround is unreliable and can crash Fusion 360.

    To create coils, please use Fusion 360's UI directly:
    Solid > Create > Coil

    Args:
        diameter: Coil diameter in mm
        pitch: Distance between coils in mm
        revolutions: Number of turns
        section_size: Wire/section diameter in mm
        section_type: "circular" or "square"
        operation: "new_body", "join", "cut", "intersect"
        name: Optional name for the body
        x: X position in mm
        y: Y position in mm
        z: Z position in mm
        component_id: Optional component ID

    Returns:
        Dict with body and feature info

    Raises:
        FeatureError: Always - this feature is not supported via API
    """
    raise FeatureError(
        "create_coil",
        "Coil creation is not supported via the Fusion 360 API. "
        "The CoilFeatures API does not expose a createInput() method. "
        "Please create coils manually using Fusion 360's UI: Solid > Create > Coil",
        suggestions=[
            "Use Fusion 360 UI: Solid > Create > Coil",
            "Alternative: Create a helix path sketch and use sweep to create spring-like shapes",
        ]
    )


def create_pipe(
    path_sketch_id: str,
    outer_diameter: float,
    wall_thickness: float,
    operation: str = "new_body",
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a hollow tubular shape (pipe) along a path.

    Args:
        path_sketch_id: ID of the sketch containing the path
        outer_diameter: Outer pipe diameter in mm
        wall_thickness: Pipe wall thickness in mm
        operation: "new_body", "join", "cut", "intersect"
        name: Optional name for the body

    Returns:
        Dict with body and feature info

    Raises:
        InvalidParameterError: If parameters are invalid
        EntityNotFoundError: If sketch not found
        FeatureError: If creation fails
    """
    if outer_diameter <= 0:
        raise InvalidParameterError("outer_diameter", outer_diameter, min_value=0.001)
    if wall_thickness <= 0:
        raise InvalidParameterError("wall_thickness", wall_thickness, min_value=0.001)
    if wall_thickness >= outer_diameter / 2:
        raise InvalidParameterError(
            "wall_thickness", wall_thickness,
            reason=f"wall_thickness ({wall_thickness}) must be less than half the outer_diameter ({outer_diameter/2})"
        )
    if operation not in OPERATION_MAP:
        raise InvalidParameterError("operation", operation, valid_values=list(OPERATION_MAP.keys()))

    path_sketch, component = _get_sketch(path_sketch_id)
    registry = get_registry()

    # Check for path curves
    path_curves = path_sketch.sketchCurves
    if path_curves.count == 0:
        raise FeatureError(
            "create_pipe",
            "Path sketch has no curves for pipe path",
            affected_entities=[path_sketch_id]
        )

    try:
        # Collect all curves from the path sketch into an ObjectCollection
        curves_collection = adsk.core.ObjectCollection.create()

        # Add all curves from the path sketch
        for i in range(path_curves.sketchLines.count):
            curves_collection.add(path_curves.sketchLines.item(i))
        for i in range(path_curves.sketchArcs.count):
            curves_collection.add(path_curves.sketchArcs.item(i))
        for i in range(path_curves.sketchFittedSplines.count):
            curves_collection.add(path_curves.sketchFittedSplines.item(i))

        if curves_collection.count == 0:
            raise FeatureError("create_pipe", "No valid path curves found in path sketch")

        # Create a Path object from the curves
        path = component.features.createPath(curves_collection)

        if not path:
            raise FeatureError("create_pipe", "Failed to create path from sketch curves")

        # Convert to cm
        outer_cm = outer_diameter / 10.0
        thickness_cm = wall_thickness / 10.0
        inner_diameter = outer_diameter - (2 * wall_thickness)

        # Use pipe feature
        pipes = component.features.pipeFeatures

        # Create pipe input
        pipe_input = pipes.createInput(path, OPERATION_MAP[operation])

        # Set diameter and wall thickness
        # sectionThickness automatically sets isHollow to true
        pipe_input.sectionType = adsk.fusion.PipeSectionTypes.CircularPipeSectionType
        pipe_input.sectionSize = adsk.core.ValueInput.createByReal(outer_cm)
        pipe_input.sectionThickness = adsk.core.ValueInput.createByReal(thickness_cm)

        # Create the pipe
        pipe_feature = pipes.add(pipe_input)

        if not pipe_feature:
            raise FeatureError("create_pipe", "Pipe creation failed")

        # Register feature
        feature_id = registry.register_feature(pipe_feature)

        # Get and register body
        created_bodies = []
        for i in range(pipe_feature.bodies.count):
            body = pipe_feature.bodies.item(i)
            if name and pipe_feature.bodies.count == 1:
                body.name = name
            registry.register_body(body)
            created_bodies.append(body)

        result = _serialize_feature_result(pipe_feature, registry, created_bodies)
        result["success"] = True
        result["pipe"] = {
            "outer_diameter": outer_diameter,
            "inner_diameter": inner_diameter,
            "wall_thickness": wall_thickness,
            "path_sketch_id": path_sketch_id,
        }

        return result

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError("create_pipe", f"Failed to create pipe: {str(e)}", fusion_error=str(e))


def _get_feature(feature_id: str) -> Any:
    """Get a feature by ID."""
    design = _get_active_design()
    registry = get_registry()

    feature = registry.get_feature(feature_id)

    if not feature:
        # Try to find in timeline
        timeline = design.timeline
        for i in range(timeline.count):
            item = timeline.item(i)
            if hasattr(item, 'entity') and item.entity:
                entity = item.entity
                if hasattr(entity, 'name') and entity.name == feature_id:
                    feature = entity
                    registry.register_feature(feature)
                    break

    if not feature:
        available = registry.get_available_feature_ids()
        raise EntityNotFoundError("Feature", feature_id, available)

    return feature


def _get_axis_entity(axis: str, component: Any) -> Tuple[Any, Any]:
    """Get axis entity and vector for patterns.

    Args:
        axis: Axis specification ("X", "Y", "Z" or edge_id)
        component: The component to get axis from

    Returns:
        Tuple of (axis_entity, axis_vector)
    """
    axis_upper = axis.upper() if len(axis) <= 2 else axis

    if axis_upper == "X":
        return component.xConstructionAxis, adsk.core.Vector3D.create(1, 0, 0)
    elif axis_upper == "Y":
        return component.yConstructionAxis, adsk.core.Vector3D.create(0, 1, 0)
    elif axis_upper == "Z":
        return component.zConstructionAxis, adsk.core.Vector3D.create(0, 0, 1)
    else:
        # Try to get edge from registry
        registry = get_registry()
        edge = registry.get_sub_entity(axis)
        if edge:
            return edge, None
        raise InvalidParameterError(
            "axis", axis,
            valid_values=["X", "Y", "Z"],
            reason="Invalid axis. Use X, Y, Z or a valid edge ID."
        )


def _get_mirror_plane(mirror_plane: str, component: Any) -> Any:
    """Get mirror plane entity.

    Args:
        mirror_plane: Plane specification ("XY", "YZ", "XZ" or plane_id)
        component: The component to get plane from

    Returns:
        Construction plane or face entity
    """
    plane_upper = mirror_plane.upper() if len(mirror_plane) <= 2 else mirror_plane

    if plane_upper == "XY":
        return component.xYConstructionPlane
    elif plane_upper == "YZ":
        return component.yZConstructionPlane
    elif plane_upper == "XZ":
        return component.xZConstructionPlane
    else:
        # Try to get from registry
        registry = get_registry()
        plane = registry.get_sub_entity(mirror_plane)
        if plane:
            return plane
        raise InvalidParameterError(
            "mirror_plane", mirror_plane,
            valid_values=["XY", "YZ", "XZ"],
            reason="Invalid plane. Use XY, YZ, XZ or a valid plane/face ID."
        )


def rectangular_pattern(
    entity_ids: List[str],
    entity_type: str,
    x_count: int,
    x_spacing: float,
    x_axis: str = "X",
    y_count: int = 1,
    y_spacing: float = 0.0,
    y_axis: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a rectangular (linear) pattern of bodies or features.

    Args:
        entity_ids: List of body or feature IDs to pattern
        entity_type: "bodies" or "features"
        x_count: Number of columns (instances in X direction)
        x_spacing: Column spacing in mm
        x_axis: Direction for columns ("X", "Y", "Z" or edge_id)
        y_count: Number of rows (default 1 for 1D pattern)
        y_spacing: Row spacing in mm
        y_axis: Direction for rows (perpendicular to x_axis if not specified)

    Returns:
        Dict with pattern feature info and created instance IDs

    Raises:
        InvalidParameterError: If parameters are invalid
        EntityNotFoundError: If entities not found
        FeatureError: If pattern fails
    """
    if entity_type not in ["bodies", "features"]:
        raise InvalidParameterError("entity_type", entity_type, valid_values=["bodies", "features"])

    if x_count < 2:
        raise InvalidParameterError("x_count", x_count, min_value=2, reason="Must have at least 2 instances")

    if x_spacing <= 0:
        raise InvalidParameterError("x_spacing", x_spacing, min_value=0.001)

    if y_count > 1 and y_spacing <= 0:
        raise InvalidParameterError("y_spacing", y_spacing, min_value=0.001, reason="y_spacing required when y_count > 1")

    if not entity_ids:
        raise InvalidParameterError("entity_ids", entity_ids, reason="At least one entity ID required")

    design = _get_active_design()
    registry = get_registry()

    try:
        # Collect entities
        entities = adsk.core.ObjectCollection.create()
        component = None

        for entity_id in entity_ids:
            if entity_type == "bodies":
                entity = _get_body(entity_id)
                if component is None:
                    component = entity.parentComponent
            else:
                entity = _get_feature(entity_id)
                if component is None:
                    component = entity.parentComponent if hasattr(entity, 'parentComponent') else design.rootComponent

            entities.add(entity)

        if component is None:
            component = design.rootComponent

        # Get axes
        x_axis_entity, x_vector = _get_axis_entity(x_axis, component)

        # Convert spacing to cm
        x_spacing_cm = x_spacing / 10.0
        y_spacing_cm = y_spacing / 10.0

        # Create rectangular pattern
        patterns = component.features.rectangularPatternFeatures
        pattern_input = patterns.createInput(
            entities,
            x_axis_entity,
            adsk.core.ValueInput.createByReal(x_count),
            adsk.core.ValueInput.createByReal(x_spacing_cm),
            adsk.fusion.PatternDistanceType.SpacingPatternDistanceType
        )

        # Set second direction if needed
        if y_count > 1:
            if y_axis:
                y_axis_entity, _ = _get_axis_entity(y_axis, component)
            else:
                # Default to perpendicular axis
                if x_axis.upper() == "X":
                    y_axis_entity = component.yConstructionAxis
                elif x_axis.upper() == "Y":
                    y_axis_entity = component.xConstructionAxis
                else:
                    y_axis_entity = component.yConstructionAxis

            pattern_input.setDirectionTwo(
                y_axis_entity,
                adsk.core.ValueInput.createByReal(y_count),
                adsk.core.ValueInput.createByReal(y_spacing_cm)
            )

        # Create the pattern
        pattern_feature = patterns.add(pattern_input)

        if not pattern_feature:
            raise FeatureError("rectangular_pattern", "Pattern creation failed")

        # Register feature
        feature_id = registry.register_feature(pattern_feature)

        # Collect created instances
        created_instances = []
        if entity_type == "bodies":
            for i in range(pattern_feature.bodies.count):
                body = pattern_feature.bodies.item(i)
                body_id = registry.register_body(body)
                created_instances.append(body_id)
        else:
            for i in range(pattern_feature.patternElements.count):
                created_instances.append(f"pattern_element_{i}")

        total_instances = x_count * y_count

        return {
            "success": True,
            "feature": {
                "id": feature_id,
                "type": "RectangularPatternFeature",
            },
            "pattern": {
                "type": "rectangular",
                "x_count": x_count,
                "x_spacing": x_spacing,
                "y_count": y_count,
                "y_spacing": y_spacing,
                "total_instances": total_instances,
            },
            "source_entities": entity_ids,
            "created_instances": created_instances,
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError("rectangular_pattern", f"Failed to create pattern: {str(e)}", fusion_error=str(e))


def circular_pattern(
    entity_ids: List[str],
    entity_type: str,
    axis: str,
    count: int,
    total_angle: float = 360.0,
    is_symmetric: bool = True,
) -> Dict[str, Any]:
    """Create a circular (radial) pattern of bodies or features.

    Args:
        entity_ids: List of body or feature IDs to pattern
        entity_type: "bodies" or "features"
        axis: Rotation axis ("X", "Y", "Z" or axis_id)
        count: Number of instances (including original)
        total_angle: Total angle span in degrees (default 360)
        is_symmetric: Distribute evenly within total_angle

    Returns:
        Dict with pattern feature info and created instance IDs

    Raises:
        InvalidParameterError: If parameters are invalid
        EntityNotFoundError: If entities not found
        FeatureError: If pattern fails
    """
    if entity_type not in ["bodies", "features"]:
        raise InvalidParameterError("entity_type", entity_type, valid_values=["bodies", "features"])

    if count < 2:
        raise InvalidParameterError("count", count, min_value=2, reason="Must have at least 2 instances")

    if total_angle <= 0 or total_angle > 360:
        raise InvalidParameterError("total_angle", total_angle, min_value=0.001, max_value=360)

    if not entity_ids:
        raise InvalidParameterError("entity_ids", entity_ids, reason="At least one entity ID required")

    design = _get_active_design()
    registry = get_registry()

    try:
        # Collect entities
        entities = adsk.core.ObjectCollection.create()
        component = None

        for entity_id in entity_ids:
            if entity_type == "bodies":
                entity = _get_body(entity_id)
                if component is None:
                    component = entity.parentComponent
            else:
                entity = _get_feature(entity_id)
                if component is None:
                    component = entity.parentComponent if hasattr(entity, 'parentComponent') else design.rootComponent

            entities.add(entity)

        if component is None:
            component = design.rootComponent

        # Get axis
        axis_entity, _ = _get_axis_entity(axis, component)

        # Convert angle to radians
        angle_rad = math.radians(total_angle)

        # Create circular pattern
        patterns = component.features.circularPatternFeatures
        pattern_input = patterns.createInput(entities, axis_entity)

        # Set count and angle
        pattern_input.quantity = adsk.core.ValueInput.createByReal(count)
        pattern_input.totalAngle = adsk.core.ValueInput.createByReal(angle_rad)
        pattern_input.isSymmetric = is_symmetric

        # Create the pattern
        pattern_feature = patterns.add(pattern_input)

        if not pattern_feature:
            raise FeatureError("circular_pattern", "Pattern creation failed")

        # Register feature
        feature_id = registry.register_feature(pattern_feature)

        # Collect created instances
        created_instances = []
        if entity_type == "bodies":
            for i in range(pattern_feature.bodies.count):
                body = pattern_feature.bodies.item(i)
                body_id = registry.register_body(body)
                created_instances.append(body_id)
        else:
            for i in range(pattern_feature.patternElements.count):
                created_instances.append(f"pattern_element_{i}")

        # Calculate angle between instances
        if is_symmetric:
            angle_between = total_angle / count
        else:
            angle_between = total_angle / (count - 1) if count > 1 else 0

        return {
            "success": True,
            "feature": {
                "id": feature_id,
                "type": "CircularPatternFeature",
            },
            "pattern": {
                "type": "circular",
                "axis": axis,
                "count": count,
                "total_angle": total_angle,
                "angle_between": angle_between,
                "is_symmetric": is_symmetric,
            },
            "source_entities": entity_ids,
            "created_instances": created_instances,
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError("circular_pattern", f"Failed to create pattern: {str(e)}", fusion_error=str(e))


def mirror_feature(
    entity_ids: List[str],
    entity_type: str,
    mirror_plane: str,
) -> Dict[str, Any]:
    """Mirror bodies or features across a plane.

    Args:
        entity_ids: List of body or feature IDs to mirror
        entity_type: "bodies" or "features"
        mirror_plane: Mirror plane ("XY", "YZ", "XZ" or plane_id)

    Returns:
        Dict with mirror feature info and created instance IDs

    Raises:
        InvalidParameterError: If parameters are invalid
        EntityNotFoundError: If entities not found
        FeatureError: If mirror fails
    """
    if entity_type not in ["bodies", "features"]:
        raise InvalidParameterError("entity_type", entity_type, valid_values=["bodies", "features"])

    if not entity_ids:
        raise InvalidParameterError("entity_ids", entity_ids, reason="At least one entity ID required")

    design = _get_active_design()
    registry = get_registry()

    try:
        # Collect entities
        entities = adsk.core.ObjectCollection.create()
        component = None

        for entity_id in entity_ids:
            if entity_type == "bodies":
                entity = _get_body(entity_id)
                if component is None:
                    component = entity.parentComponent
            else:
                entity = _get_feature(entity_id)
                if component is None:
                    component = entity.parentComponent if hasattr(entity, 'parentComponent') else design.rootComponent

            entities.add(entity)

        if component is None:
            component = design.rootComponent

        # Get mirror plane
        plane = _get_mirror_plane(mirror_plane, component)

        # Create mirror feature
        mirrors = component.features.mirrorFeatures
        mirror_input = mirrors.createInput(entities, plane)

        # Create the mirror
        mirror_feature_obj = mirrors.add(mirror_input)

        if not mirror_feature_obj:
            raise FeatureError("mirror_feature", "Mirror operation failed")

        # Register feature
        feature_id = registry.register_feature(mirror_feature_obj)

        # Collect created instances
        created_instances = []
        if entity_type == "bodies":
            for i in range(mirror_feature_obj.bodies.count):
                body = mirror_feature_obj.bodies.item(i)
                body_id = registry.register_body(body)
                created_instances.append(body_id)
        else:
            # For features, the mirror creates new elements
            created_instances.append(f"mirror_{feature_id}")

        return {
            "success": True,
            "feature": {
                "id": feature_id,
                "type": "MirrorFeature",
            },
            "mirror": {
                "plane": mirror_plane,
            },
            "source_entities": entity_ids,
            "created_instances": created_instances,
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError("mirror_feature", f"Failed to mirror: {str(e)}", fusion_error=str(e))


def create_hole(
    body_id: Optional[str] = None,
    face_id: Optional[str] = None,
    x: float = 0.0,
    y: float = 0.0,
    diameter: float = 6.0,
    depth: float = 10.0,
    name: Optional[str] = None,
    hole_type: str = "simple",
    countersink_angle: float = 90.0,
    countersink_diameter: float = 0.0,
    counterbore_diameter: float = 0.0,
    counterbore_depth: float = 0.0,
) -> Dict[str, Any]:
    """Create a hole in a body.

    Args:
        body_id: ID of the body to drill into (optional if face_id provided)
        face_id: ID of the face to place hole on
        x: X position of hole center in mm
        y: Y position of hole center in mm
        diameter: Hole diameter in mm
        depth: Hole depth in mm
        name: Optional name for the feature
        hole_type: "simple", "countersink", or "counterbore"
        countersink_angle: Countersink angle in degrees
        countersink_diameter: Countersink diameter in mm
        counterbore_diameter: Counterbore diameter in mm
        counterbore_depth: Counterbore depth in mm

    Returns:
        Dict with feature_id and hole info

    Raises:
        InvalidParameterError: If parameters are invalid
        EntityNotFoundError: If body/face not found
        FeatureError: If hole creation fails
    """
    if diameter <= 0:
        raise InvalidParameterError("diameter", diameter, min_value=0.001)
    if depth <= 0:
        raise InvalidParameterError("depth", depth, min_value=0.001)

    if hole_type not in ["simple", "countersink", "counterbore"]:
        raise InvalidParameterError("hole_type", hole_type, valid_values=["simple", "countersink", "counterbore"])

    if not body_id and not face_id:
        raise InvalidParameterError("body_id/face_id", None, reason="Either body_id or face_id must be provided")

    design = _get_active_design()
    registry = get_registry()

    try:
        # Get face to place hole on
        if face_id:
            face = registry.get_sub_entity(face_id)
            if not face:
                raise EntityNotFoundError("Face", face_id)
            body = face.body
        else:
            body = _get_body(body_id)
            # Use first planar face
            face = None
            for i in range(body.faces.count):
                f = body.faces.item(i)
                if f.geometry.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType:
                    face = f
                    break
            if not face:
                raise FeatureError("hole", "No planar face found on body for hole placement")

        component = body.parentComponent

        # Create sketch point for hole location
        sketches = component.sketches
        sketch = sketches.add(face)

        # Convert to cm
        x_cm = x / 10.0
        y_cm = y / 10.0

        # Add point to sketch
        sketch_points = sketch.sketchPoints
        center_point = sketch_points.add(adsk.core.Point3D.create(x_cm, y_cm, 0))

        # Create hole feature
        holes = component.features.holeFeatures
        hole_input = holes.createSimpleInput(
            adsk.core.ValueInput.createByReal(diameter / 20.0)  # Radius in cm
        )

        # Set hole position
        hole_input.setPositionBySketchPoint(center_point)

        # Set depth
        depth_cm = depth / 10.0
        hole_input.setDistanceExtent(adsk.core.ValueInput.createByReal(depth_cm))

        # Set hole type specifics
        if hole_type == "countersink":
            hole_input.isCountersink = True
            hole_input.countersinkAngle = adsk.core.ValueInput.createByReal(math.radians(countersink_angle))
            if countersink_diameter > 0:
                hole_input.countersinkDiameter = adsk.core.ValueInput.createByReal(countersink_diameter / 10.0)
        elif hole_type == "counterbore":
            hole_input.isCounterbore = True
            if counterbore_diameter > 0:
                hole_input.counterboreDiameter = adsk.core.ValueInput.createByReal(counterbore_diameter / 10.0)
            if counterbore_depth > 0:
                hole_input.counterboreDepth = adsk.core.ValueInput.createByReal(counterbore_depth / 10.0)

        hole_feature = holes.add(hole_input)

        if not hole_feature:
            raise FeatureError("hole", "Hole creation failed")

        feature_id = registry.register_feature(hole_feature)

        result = {
            "success": True,
            "feature": {
                "id": feature_id,
                "type": "HoleFeature",
                "hole_type": hole_type,
                "diameter": diameter,
                "depth": depth,
                "position": {"x": x, "y": y},
            },
            "body_id": registry.register_body(body),
        }

        return result

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError("hole", f"Failed to create hole: {str(e)}", fusion_error=str(e))


# --- Phase 8c: Specialized Feature Tools ---


def create_thread(
    face_id: str,
    thread_type: str,
    thread_size: str,
    is_internal: bool = False,
    is_full_length: bool = True,
    thread_length: Optional[float] = None,
    is_modeled: bool = False,
) -> Dict[str, Any]:
    """Add threads to a cylindrical face.

    Args:
        face_id: ID of the cylindrical face to add thread to
        thread_type: Thread standard (e.g., "ISO Metric profile")
        thread_size: Thread designation (e.g., "M6x1", "M8x1.25")
        is_internal: Internal thread (True) or external thread (False)
        is_full_length: Thread entire face length (True) or use custom length
        thread_length: Custom thread length in mm (used if is_full_length=False)
        is_modeled: Create physical thread geometry (slower but visible)

    Returns:
        Dict with thread feature info and thread specification

    Raises:
        InvalidParameterError: If parameters are invalid
        EntityNotFoundError: If face not found
        FeatureError: If thread creation fails
    """
    if not thread_type:
        raise InvalidParameterError("thread_type", thread_type, reason="Thread type is required")
    if not thread_size:
        raise InvalidParameterError("thread_size", thread_size, reason="Thread size is required")
    if not is_full_length and (thread_length is None or thread_length <= 0):
        raise InvalidParameterError(
            "thread_length", thread_length,
            reason="thread_length is required when is_full_length=False"
        )

    design = _get_active_design()
    registry = get_registry()

    try:
        # Get the face
        face = registry.get_sub_entity(face_id)
        if not face:
            raise EntityNotFoundError("Face", face_id, suggestion="Use get_body_by_id with include_faces=True")

        # Verify face is cylindrical
        if not hasattr(face, 'geometry') or face.geometry.surfaceType != adsk.core.SurfaceTypes.CylinderSurfaceType:
            raise InvalidParameterError(
                "face_id", face_id,
                reason="Face must be cylindrical for threading. Use a cylindrical face from a hole or shaft."
            )

        # Get component
        body = face.body
        component = body.parentComponent

        # Get thread data
        thread_data = component.features.threadFeatures.threadDataQuery

        # Find matching thread type
        all_thread_types = thread_data.allThreadTypes
        matching_type = None
        for t_type in all_thread_types:
            if thread_type.lower() in t_type.lower():
                matching_type = t_type
                break

        if not matching_type:
            available_types = list(all_thread_types)[:10]
            raise InvalidParameterError(
                "thread_type", thread_type,
                reason=f"Thread type not found. Available types include: {available_types}"
            )

        # Get available sizes for this thread type
        all_sizes = thread_data.allSizes(matching_type)
        matching_size = None

        # Parse requested size - extract diameter from formats like "M8x1.25" or "M8" or "8"
        import re
        size_match = re.match(r'M?(\d+(?:\.\d+)?)', thread_size, re.IGNORECASE)
        requested_diameter = size_match.group(1) if size_match else thread_size

        # First try exact match
        for size in all_sizes:
            if size == requested_diameter or size == thread_size:
                matching_size = size
                break

        # Then try matching diameter
        if not matching_size:
            for size in all_sizes:
                if size == requested_diameter:
                    matching_size = size
                    break

        # Then try if size starts with the diameter
        if not matching_size:
            for size in all_sizes:
                if size.startswith(requested_diameter) or requested_diameter.startswith(size):
                    matching_size = size
                    break

        if not matching_size:
            available_sizes = list(all_sizes)[:15]
            raise InvalidParameterError(
                "thread_size", thread_size,
                reason=f"Thread size not found for {matching_type}. Requested diameter: {requested_diameter}. Available sizes include: {available_sizes}"
            )

        # Get thread designations for this size
        all_designations = thread_data.allDesignations(matching_type, matching_size)
        if len(all_designations) == 0:
            raise FeatureError(
                "thread",
                f"No thread designations found for {matching_type} {matching_size}"
            )

        # Try to find a designation matching the requested thread_size (e.g., "M8x1.25")
        thread_designation = None
        thread_size_upper = thread_size.upper()
        for designation in all_designations:
            if designation.upper() == thread_size_upper:
                thread_designation = designation
                break

        # If no exact match, use first designation (default pitch)
        if not thread_designation:
            thread_designation = all_designations[0]

        # Get thread class (use allClasses to get available classes, then pick the first)
        all_classes = thread_data.allClasses(is_internal, matching_type, thread_designation)
        if len(all_classes) == 0:
            # Fallback: try a common class name
            thread_class = "6g" if not is_internal else "6H"
        else:
            thread_class = all_classes[0]

        # Create thread features reference
        threads = component.features.threadFeatures

        # Build thread info object using createThreadInfo (correct API)
        thread_info = threads.createThreadInfo(is_internal, matching_type, thread_designation, thread_class)

        # Create faces collection for the input
        faces = adsk.core.ObjectCollection.create()
        faces.add(face)

        # Create thread input
        thread_input = threads.createInput(faces, thread_info)

        # Set thread options
        thread_input.isModeled = is_modeled

        if is_full_length:
            thread_input.isFullLength = True
        else:
            thread_input.isFullLength = False
            thread_length_cm = thread_length / 10.0
            thread_input.threadLength = adsk.core.ValueInput.createByReal(thread_length_cm)

        # Create the thread
        thread_feature = threads.add(thread_input)

        if not thread_feature:
            raise FeatureError("thread", "Thread creation failed")

        # Register feature
        feature_id = registry.register_feature(thread_feature)

        return {
            "success": True,
            "feature": {
                "id": feature_id,
                "type": "ThreadFeature",
            },
            "thread": {
                "thread_type": matching_type,
                "thread_size": matching_size,
                "thread_designation": thread_designation,
                "thread_class": thread_class,
                "is_internal": is_internal,
                "is_full_length": is_full_length,
                "is_modeled": is_modeled,
                "is_right_hand": True,
            },
            "face_id": face_id,
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError("thread", f"Failed to create thread: {str(e)}", fusion_error=str(e))


def thicken(
    face_ids: List[str],
    thickness: float,
    direction: str = "both",
    operation: str = "new_body",
    is_chain: bool = True,
) -> Dict[str, Any]:
    """Add thickness to surface faces to create solid bodies.

    Args:
        face_ids: List of face IDs to thicken
        thickness: Thickness in mm
        direction: "positive", "negative", or "both"
        operation: "new_body", "join", "cut", "intersect"
        is_chain: Include tangent-connected faces

    Returns:
        Dict with thicken feature info and created bodies

    Raises:
        InvalidParameterError: If parameters are invalid
        EntityNotFoundError: If faces not found
        FeatureError: If thicken fails
    """
    if thickness <= 0:
        raise InvalidParameterError("thickness", thickness, min_value=0.001)

    if direction not in ["positive", "negative", "both"]:
        raise InvalidParameterError("direction", direction, valid_values=["positive", "negative", "both"])

    if operation not in OPERATION_MAP:
        raise InvalidParameterError("operation", operation, valid_values=list(OPERATION_MAP.keys()))

    if not face_ids:
        raise InvalidParameterError("face_ids", face_ids, reason="At least one face ID required")

    design = _get_active_design()
    registry = get_registry()

    try:
        # Collect faces
        faces = adsk.core.ObjectCollection.create()
        component = None

        for face_id in face_ids:
            face = registry.get_sub_entity(face_id)
            if not face:
                raise EntityNotFoundError("Face", face_id, suggestion="Use get_body_by_id with include_faces=True")

            faces.add(face)
            if component is None:
                component = face.body.parentComponent

        if component is None:
            component = design.rootComponent

        # Convert thickness to cm
        thickness_cm = thickness / 10.0

        # Create thicken input
        thickens = component.features.thickenFeatures

        # Determine thickness value based on direction
        if direction == "negative":
            thickness_value = adsk.core.ValueInput.createByReal(-thickness_cm)
        else:
            thickness_value = adsk.core.ValueInput.createByReal(thickness_cm)

        # Create input with operation
        thicken_input = thickens.createInput(
            faces,
            thickness_value,
            is_chain,  # isChainSelection
            OPERATION_MAP[operation]
        )

        # Set symmetric if direction is "both"
        if direction == "both":
            thicken_input.isSymmetric = True

        # Create the thicken
        thicken_feature = thickens.add(thicken_input)

        if not thicken_feature:
            raise FeatureError("thicken", "Thicken operation failed")

        # Register feature
        feature_id = registry.register_feature(thicken_feature)

        # Get and register created bodies
        created_bodies = []
        body_serializer = BodySerializer(registry)

        for i in range(thicken_feature.bodies.count):
            body = thicken_feature.bodies.item(i)
            registry.register_body(body)
            created_bodies.append(body_serializer.serialize_summary(body))

        return {
            "success": True,
            "feature": {
                "id": feature_id,
                "type": "ThickenFeature",
            },
            "thicken": {
                "thickness": thickness,
                "direction": direction,
                "operation": operation,
                "is_chain": is_chain,
                "source_faces": len(face_ids),
            },
            "bodies": created_bodies,
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError("thicken", f"Failed to thicken: {str(e)}", fusion_error=str(e))


def emboss(
    sketch_id: str,
    face_id: str,
    depth: float,
    is_emboss: bool = True,
    profile_index: int = 0,
    taper_angle: float = 0.0,
) -> Dict[str, Any]:
    """Create raised (emboss) or recessed (deboss) features from sketch profiles.

    Args:
        sketch_id: ID of the sketch containing profile/text to emboss
        face_id: ID of the face to emboss onto
        depth: Emboss/deboss depth in mm
        is_emboss: True for raised (emboss), False for recessed (deboss/engrave)
        profile_index: Index of profile to use from sketch
        taper_angle: Side taper angle in degrees

    Returns:
        Dict with emboss feature info

    Raises:
        InvalidParameterError: If parameters are invalid
        EntityNotFoundError: If sketch or face not found
        FeatureError: If emboss fails
    """
    if depth <= 0:
        raise InvalidParameterError("depth", depth, min_value=0.001)
    if taper_angle < 0 or taper_angle >= 90:
        raise InvalidParameterError("taper_angle", taper_angle, min_value=0, max_value=89.999)

    design = _get_active_design()
    registry = get_registry()

    try:
        # Get sketch
        sketch = registry.get_sketch(sketch_id)
        if not sketch:
            raise EntityNotFoundError("sketch", sketch_id)

        # Check for profiles or text
        # The emboss API accepts both Profile and SketchText objects
        emboss_entities = []

        if sketch.profiles.count > 0:
            # Use profile if available
            if profile_index >= sketch.profiles.count:
                raise InvalidParameterError(
                    "profile_index",
                    profile_index,
                    max_value=sketch.profiles.count - 1
                )
            emboss_entities.append(sketch.profiles.item(profile_index))
        elif sketch.sketchTexts.count > 0:
            # Use SketchText if no profiles but text exists
            # Add all text entities to the emboss
            for i in range(sketch.sketchTexts.count):
                emboss_entities.append(sketch.sketchTexts.item(i))
        else:
            raise FeatureError(
                "emboss",
                f"Sketch '{sketch_id}' has no closed profiles or text. "
                "Emboss requires closed profile geometry or SketchText.",
                suggestion="Draw closed shapes (circles, rectangles) or add text with add_sketch_text()"
            )

        # Get target face
        face = registry.get_sub_entity(face_id)
        if not face:
            raise EntityNotFoundError("face", face_id, suggestion="Use get_body_by_id with include_faces=True")

        # Get the component containing the face
        body = face.body
        component = body.parentComponent

        # Convert depth to cm
        depth_cm = depth / 10.0
        taper_rad = math.radians(taper_angle)

        # Try to use the EmbossFeatures API
        emboss_features = component.features.embossFeatures

        # Check if createInput method exists
        if not hasattr(emboss_features, 'createInput'):
            raise FeatureError(
                "emboss",
                "The EmbossFeatures.createInput() method is not available in this Fusion 360 version. "
                "Use extrude() with operation='join' or 'cut' as an alternative.",
                suggestion="Use extrude() with operation='join' (for raised) or 'cut' (for engraved)"
            )

        # Create arrays for profiles/text and faces (API requires arrays)
        # emboss_entities already contains Profile or SketchText objects
        faces_array = [face]

        # Depth: positive for emboss (raised), negative for deboss (engraved)
        actual_depth = depth_cm if is_emboss else -depth_cm
        depth_value = adsk.core.ValueInput.createByReal(actual_depth)

        # Create emboss input with profiles/text, faces, and depth
        emboss_input = emboss_features.createInput(emboss_entities, faces_array, depth_value)

        # Create the emboss feature
        emboss_feature = emboss_features.add(emboss_input)

        if not emboss_feature:
            raise FeatureError("emboss", "Failed to create emboss feature")

        # Register feature
        feature_id = registry.register_feature(emboss_feature)

        return {
            "success": True,
            "feature": {
                "id": feature_id,
                "name": emboss_feature.name,
                "type": "emboss" if is_emboss else "deboss",
            },
            "emboss": {
                "type": "emboss" if is_emboss else "deboss",
                "depth": depth,
                "taper_angle": taper_angle,
                "sketch_id": sketch_id,
                "face_id": face_id,
            },
            "body_id": body.name if body else None,
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        # Provide helpful error with workaround
        workaround = (
            f"Emboss API error: {str(e)}\n\n"
            "Alternative workflow:\n"
            "For RAISED features: Use extrude() with operation='join'\n"
            "For ENGRAVED features: Use extrude() with operation='cut' and direction='negative'"
        )
        raise FeatureError("emboss", workaround, fusion_error=str(e))


# --- MODIFY Menu Tools ---


# Valid operations for combine feature (subset of OPERATION_MAP)
COMBINE_VALID_OPERATIONS = ["join", "cut", "intersect"]


def combine(
    target_body_id: str,
    tool_body_ids: List[str],
    operation: str = "join",
    keep_tools: bool = False,
) -> Dict[str, Any]:
    """Combine multiple bodies using boolean operations.

    Args:
        target_body_id: ID of the body to modify (target)
        tool_body_ids: List of body IDs to combine with (tools)
        operation: "join", "cut", or "intersect"
        keep_tools: If True, keep tool bodies after operation

    Returns:
        Dict with feature info and resulting body

    Raises:
        InvalidParameterError: If parameters are invalid
        EntityNotFoundError: If bodies not found
        FeatureError: If combine fails
    """
    if operation not in COMBINE_VALID_OPERATIONS:
        raise InvalidParameterError(
            "operation", operation,
            valid_values=COMBINE_VALID_OPERATIONS
        )

    if not tool_body_ids:
        raise InvalidParameterError(
            "tool_body_ids", tool_body_ids,
            reason="At least one tool body ID is required"
        )

    design = _get_active_design()
    registry = get_registry()

    try:
        # Get target body
        target_body = _get_body(target_body_id)
        component = target_body.parentComponent

        # Collect tool bodies
        tool_bodies = adsk.core.ObjectCollection.create()
        for tool_id in tool_body_ids:
            tool_body = _get_body(tool_id)
            tool_bodies.add(tool_body)

        # Create combine feature
        combines = component.features.combineFeatures
        combine_input = combines.createInput(target_body, tool_bodies)

        # Set operation type
        combine_input.operation = OPERATION_MAP[operation]

        # Set whether to keep tool bodies
        combine_input.isKeepToolBodies = keep_tools

        # Create the combine
        combine_feature = combines.add(combine_input)

        if not combine_feature:
            raise FeatureError("combine", "Combine operation failed")

        # Register feature
        feature_id = registry.register_feature(combine_feature)

        # Get resulting body
        body_serializer = BodySerializer(registry)
        result_body = target_body  # Target body is modified in place
        registry.register_body(result_body)

        return {
            "success": True,
            "feature": {
                "id": feature_id,
                "type": "CombineFeature",
            },
            "combine": {
                "target_body_id": target_body_id,
                "tool_body_ids": tool_body_ids,
                "operation": operation,
                "keep_tools": keep_tools,
            },
            "body": body_serializer.serialize_summary(result_body),
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError("combine", f"Failed to combine: {str(e)}", fusion_error=str(e))


def split_body(
    body_id: str,
    splitting_tool: str,
    extend_splitting_tool: bool = True,
) -> Dict[str, Any]:
    """Split a body using a plane or face.

    Args:
        body_id: ID of the body to split
        splitting_tool: Face ID, plane ID, or "XY"/"YZ"/"XZ" for construction planes
        extend_splitting_tool: If True, extend tool to fully split body

    Returns:
        Dict with feature info and resulting bodies

    Raises:
        InvalidParameterError: If parameters are invalid
        EntityNotFoundError: If body or splitting tool not found
        FeatureError: If split fails
    """
    design = _get_active_design()
    registry = get_registry()

    try:
        # Get body to split
        body = _get_body(body_id)
        component = body.parentComponent

        # Resolve splitting tool
        splitting_entity = None
        tool_upper = splitting_tool.upper() if len(splitting_tool) <= 2 else splitting_tool

        if tool_upper == "XY":
            splitting_entity = component.xYConstructionPlane
        elif tool_upper == "YZ":
            splitting_entity = component.yZConstructionPlane
        elif tool_upper == "XZ":
            splitting_entity = component.xZConstructionPlane
        else:
            # Try to get from registry (could be a face or construction plane)
            splitting_entity = registry.get_sub_entity(splitting_tool)
            if not splitting_entity:
                # Try as a construction plane by name
                for plane in component.constructionPlanes:
                    if plane.name == splitting_tool:
                        splitting_entity = plane
                        break

        if not splitting_entity:
            raise EntityNotFoundError(
                "SplittingTool", splitting_tool,
                suggestion="Use 'XY', 'YZ', 'XZ', a face_id, or a construction plane name"
            )

        # Create split body feature
        split_bodies = component.features.splitBodyFeatures
        split_input = split_bodies.createInput(body, splitting_entity, extend_splitting_tool)

        # Create the split
        split_feature = split_bodies.add(split_input)

        if not split_feature:
            raise FeatureError("split_body", "Split body operation failed")

        # Register feature
        feature_id = registry.register_feature(split_feature)

        # Get and register resulting bodies
        body_serializer = BodySerializer(registry)
        resulting_bodies = []
        for i in range(split_feature.bodies.count):
            result_body = split_feature.bodies.item(i)
            registry.register_body(result_body)
            resulting_bodies.append(body_serializer.serialize_summary(result_body))

        return {
            "success": True,
            "feature": {
                "id": feature_id,
                "type": "SplitBodyFeature",
            },
            "split": {
                "source_body_id": body_id,
                "splitting_tool": splitting_tool,
                "extend_splitting_tool": extend_splitting_tool,
                "bodies_created": len(resulting_bodies),
            },
            "bodies": resulting_bodies,
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError("split_body", f"Failed to split body: {str(e)}", fusion_error=str(e))


def shell(
    body_id: str,
    face_ids: List[str],
    thickness: float,
    direction: str = "inside",
) -> Dict[str, Any]:
    """Create hollow shell by removing faces and adding wall thickness.

    Args:
        body_id: ID of the body to shell
        face_ids: List of face IDs to remove (these become openings)
        thickness: Wall thickness in mm
        direction: "inside" (shell inward) or "outside" (shell outward)

    Returns:
        Dict with feature info and resulting body

    Raises:
        InvalidParameterError: If parameters are invalid
        EntityNotFoundError: If body or faces not found
        FeatureError: If shell fails
    """
    if thickness <= 0:
        raise InvalidParameterError("thickness", thickness, min_value=0.001)

    if direction not in ["inside", "outside"]:
        raise InvalidParameterError("direction", direction, valid_values=["inside", "outside"])

    if not face_ids:
        raise InvalidParameterError("face_ids", face_ids, reason="At least one face ID is required")

    design = _get_active_design()
    registry = get_registry()

    try:
        # Get body
        body = _get_body(body_id)
        component = body.parentComponent

        # Collect faces to remove
        faces = adsk.core.ObjectCollection.create()
        for face_id in face_ids:
            face = registry.get_sub_entity(face_id)
            if not face:
                # Try to find by index
                if "_face_" in face_id:
                    try:
                        idx = int(face_id.split("_face_")[1])
                        if idx < body.faces.count:
                            face = body.faces.item(idx)
                    except (ValueError, IndexError):
                        pass

            if not face:
                raise EntityNotFoundError(
                    "Face", face_id,
                    suggestion="Use get_body_by_id with include_faces=True to see available faces"
                )
            faces.add(face)

        # Convert thickness to cm
        thickness_cm = thickness / 10.0

        # Create shell feature
        shells = component.features.shellFeatures
        shell_input = shells.createInput(faces, direction == "inside")

        # Set thickness
        shell_input.insideThickness = adsk.core.ValueInput.createByReal(thickness_cm)
        if direction == "outside":
            shell_input.outsideThickness = adsk.core.ValueInput.createByReal(thickness_cm)
            shell_input.insideThickness = adsk.core.ValueInput.createByReal(0)

        # Create the shell
        shell_feature = shells.add(shell_input)

        if not shell_feature:
            raise FeatureError("shell", "Shell operation failed")

        # Register feature
        feature_id = registry.register_feature(shell_feature)

        # Get resulting body
        body_serializer = BodySerializer(registry)
        registry.register_body(body)

        return {
            "success": True,
            "feature": {
                "id": feature_id,
                "type": "ShellFeature",
            },
            "shell": {
                "body_id": body_id,
                "removed_faces": face_ids,
                "thickness": thickness,
                "direction": direction,
            },
            "body": body_serializer.serialize_summary(body),
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError("shell", f"Failed to create shell: {str(e)}", fusion_error=str(e))


def draft(
    face_ids: List[str],
    plane: str,
    angle: float,
    is_tangent_chain: bool = True,
) -> Dict[str, Any]:
    """Add draft angle to faces for mold release.

    Args:
        face_ids: List of face IDs to draft
        plane: Pull direction plane (face_id or "XY"/"YZ"/"XZ")
        angle: Draft angle in degrees
        is_tangent_chain: If True, include tangent-connected faces

    Returns:
        Dict with feature info

    Raises:
        InvalidParameterError: If parameters are invalid
        EntityNotFoundError: If faces or plane not found
        FeatureError: If draft fails
    """
    if angle <= 0 or angle >= 90:
        raise InvalidParameterError("angle", angle, min_value=0.001, max_value=89.999)

    if not face_ids:
        raise InvalidParameterError("face_ids", face_ids, reason="At least one face ID is required")

    design = _get_active_design()
    registry = get_registry()

    try:
        # Get first face to determine component
        first_face = registry.get_sub_entity(face_ids[0])
        if not first_face:
            raise EntityNotFoundError("Face", face_ids[0])

        component = first_face.body.parentComponent

        # Collect faces
        faces = adsk.core.ObjectCollection.create()
        for face_id in face_ids:
            face = registry.get_sub_entity(face_id)
            if not face:
                raise EntityNotFoundError(
                    "Face", face_id,
                    suggestion="Use get_body_by_id with include_faces=True"
                )
            faces.add(face)

        # Resolve plane (pull direction)
        plane_entity = None
        plane_upper = plane.upper() if len(plane) <= 2 else plane

        if plane_upper == "XY":
            plane_entity = component.xYConstructionPlane
        elif plane_upper == "YZ":
            plane_entity = component.yZConstructionPlane
        elif plane_upper == "XZ":
            plane_entity = component.xZConstructionPlane
        else:
            # Try to get as face or plane from registry
            plane_entity = registry.get_sub_entity(plane)
            if not plane_entity:
                for cp in component.constructionPlanes:
                    if cp.name == plane:
                        plane_entity = cp
                        break

        if not plane_entity:
            raise EntityNotFoundError(
                "Plane", plane,
                suggestion="Use 'XY', 'YZ', 'XZ', a face_id, or a construction plane name"
            )

        # Convert angle to radians
        angle_rad = math.radians(angle)

        # Create draft feature
        drafts = component.features.draftFeatures
        draft_input = drafts.createInput(
            faces,
            plane_entity,
            adsk.core.ValueInput.createByReal(angle_rad),
            is_tangent_chain
        )

        # Create the draft
        draft_feature = drafts.add(draft_input)

        if not draft_feature:
            raise FeatureError("draft", "Draft operation failed")

        # Register feature
        feature_id = registry.register_feature(draft_feature)

        return {
            "success": True,
            "feature": {
                "id": feature_id,
                "type": "DraftFeature",
            },
            "draft": {
                "face_ids": face_ids,
                "plane": plane,
                "angle": angle,
                "is_tangent_chain": is_tangent_chain,
            },
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError("draft", f"Failed to create draft: {str(e)}", fusion_error=str(e))


def scale(
    body_ids: List[str],
    scale_factor: float = 1.0,
    point_x: float = 0.0,
    point_y: float = 0.0,
    point_z: float = 0.0,
    x_scale: Optional[float] = None,
    y_scale: Optional[float] = None,
    z_scale: Optional[float] = None,
) -> Dict[str, Any]:
    """Scale bodies uniformly or non-uniformly.

    Args:
        body_ids: List of body IDs to scale
        scale_factor: Uniform scale factor (used if x/y/z_scale not provided)
        point_x: Scale origin X in mm
        point_y: Scale origin Y in mm
        point_z: Scale origin Z in mm
        x_scale: Non-uniform X scale factor (overrides scale_factor)
        y_scale: Non-uniform Y scale factor (overrides scale_factor)
        z_scale: Non-uniform Z scale factor (overrides scale_factor)

    Returns:
        Dict with feature info and scaled bodies

    Raises:
        InvalidParameterError: If parameters are invalid
        EntityNotFoundError: If bodies not found
        FeatureError: If scale fails
    """
    # Determine if uniform or non-uniform
    is_non_uniform = any(s is not None for s in [x_scale, y_scale, z_scale])

    if is_non_uniform:
        # All three must be provided for non-uniform
        if x_scale is None or y_scale is None or z_scale is None:
            raise InvalidParameterError(
                "x_scale/y_scale/z_scale", [x_scale, y_scale, z_scale],
                reason="For non-uniform scaling, all three (x_scale, y_scale, z_scale) must be provided"
            )
        if x_scale <= 0 or y_scale <= 0 or z_scale <= 0:
            raise InvalidParameterError(
                "scale factors", [x_scale, y_scale, z_scale],
                reason="Scale factors must be positive"
            )
    else:
        if scale_factor <= 0:
            raise InvalidParameterError("scale_factor", scale_factor, min_value=0.001)

    if not body_ids:
        raise InvalidParameterError("body_ids", body_ids, reason="At least one body ID is required")

    design = _get_active_design()
    registry = get_registry()

    try:
        # Collect bodies
        bodies = adsk.core.ObjectCollection.create()
        component = None

        for body_id in body_ids:
            body = _get_body(body_id)
            bodies.add(body)
            if component is None:
                component = body.parentComponent

        if component is None:
            component = design.rootComponent

        # Create scale point (in cm)
        point_cm = adsk.core.Point3D.create(point_x / 10.0, point_y / 10.0, point_z / 10.0)

        # Create scale feature
        scales = component.features.scaleFeatures
        scale_input = scales.createInput(bodies, point_cm, adsk.core.ValueInput.createByReal(scale_factor))

        if is_non_uniform:
            # Set non-uniform scaling
            scale_input.setToNonUniform(
                adsk.core.ValueInput.createByReal(x_scale),
                adsk.core.ValueInput.createByReal(y_scale),
                adsk.core.ValueInput.createByReal(z_scale)
            )

        # Create the scale
        scale_feature = scales.add(scale_input)

        if not scale_feature:
            raise FeatureError("scale", "Scale operation failed")

        # Register feature
        feature_id = registry.register_feature(scale_feature)

        # Get scaled bodies
        body_serializer = BodySerializer(registry)
        scaled_bodies = []
        for i in range(scale_feature.bodies.count):
            scaled_body = scale_feature.bodies.item(i)
            registry.register_body(scaled_body)
            scaled_bodies.append(body_serializer.serialize_summary(scaled_body))

        result = {
            "success": True,
            "feature": {
                "id": feature_id,
                "type": "ScaleFeature",
            },
            "scale": {
                "body_ids": body_ids,
                "origin": {"x": point_x, "y": point_y, "z": point_z},
                "is_uniform": not is_non_uniform,
            },
            "bodies": scaled_bodies,
        }

        if is_non_uniform:
            result["scale"]["x_scale"] = x_scale
            result["scale"]["y_scale"] = y_scale
            result["scale"]["z_scale"] = z_scale
        else:
            result["scale"]["scale_factor"] = scale_factor

        return result

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError("scale", f"Failed to scale: {str(e)}", fusion_error=str(e))


def offset_face(
    face_ids: List[str],
    distance: float,
) -> Dict[str, Any]:
    """Offset faces to add or remove material (Press Pull for faces).

    Args:
        face_ids: List of face IDs to offset
        distance: Offset distance in mm (positive = outward, negative = inward)

    Returns:
        Dict with feature info

    Raises:
        InvalidParameterError: If parameters are invalid
        EntityNotFoundError: If faces not found
        FeatureError: If offset fails
    """
    if distance == 0:
        raise InvalidParameterError("distance", distance, reason="Distance must be non-zero")

    if not face_ids:
        raise InvalidParameterError("face_ids", face_ids, reason="At least one face ID is required")

    design = _get_active_design()
    registry = get_registry()

    try:
        # Collect faces
        faces = adsk.core.ObjectCollection.create()
        component = None

        for face_id in face_ids:
            face = registry.get_sub_entity(face_id)
            if not face:
                raise EntityNotFoundError(
                    "Face", face_id,
                    suggestion="Use get_body_by_id with include_faces=True"
                )
            faces.add(face)
            if component is None:
                component = face.body.parentComponent

        if component is None:
            component = design.rootComponent

        # Convert distance to cm
        distance_cm = distance / 10.0

        # Create offset faces feature
        offset_faces = component.features.offsetFacesFeatures
        offset_input = offset_faces.createInput(
            faces,
            adsk.core.ValueInput.createByReal(distance_cm)
        )

        # Create the offset
        offset_feature = offset_faces.add(offset_input)

        if not offset_feature:
            raise FeatureError("offset_face", "Offset face operation failed")

        # Register feature
        feature_id = registry.register_feature(offset_feature)

        return {
            "success": True,
            "feature": {
                "id": feature_id,
                "type": "OffsetFacesFeature",
            },
            "offset": {
                "face_ids": face_ids,
                "distance": distance,
            },
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError("offset_face", f"Failed to offset faces: {str(e)}", fusion_error=str(e))


def split_face(
    face_ids: List[str],
    splitting_tool: str,
    extend_splitting_tool: bool = True,
) -> Dict[str, Any]:
    """Split faces using edges or curves.

    Args:
        face_ids: List of face IDs to split
        splitting_tool: Edge ID, curve ID, or sketch ID to split with
        extend_splitting_tool: If True, extend tool to fully split faces

    Returns:
        Dict with feature info and resulting faces

    Raises:
        InvalidParameterError: If parameters are invalid
        EntityNotFoundError: If faces or tool not found
        FeatureError: If split fails
    """
    if not face_ids:
        raise InvalidParameterError("face_ids", face_ids, reason="At least one face ID is required")

    design = _get_active_design()
    registry = get_registry()

    try:
        # Collect faces
        faces = adsk.core.ObjectCollection.create()
        component = None

        for face_id in face_ids:
            face = registry.get_sub_entity(face_id)
            if not face:
                raise EntityNotFoundError(
                    "Face", face_id,
                    suggestion="Use get_body_by_id with include_faces=True"
                )
            faces.add(face)
            if component is None:
                component = face.body.parentComponent

        if component is None:
            component = design.rootComponent

        # Resolve splitting tool (could be edge, sketch curve, or sketch)
        splitting_entity = registry.get_sub_entity(splitting_tool)

        if not splitting_entity:
            # Try as a sketch
            sketch = registry.get_sketch(splitting_tool)
            if sketch:
                # Use all curves from the sketch
                curves = adsk.core.ObjectCollection.create()
                for i in range(sketch.sketchCurves.count):
                    curves.add(sketch.sketchCurves.item(i))
                splitting_entity = curves
            else:
                raise EntityNotFoundError(
                    "SplittingTool", splitting_tool,
                    suggestion="Use an edge_id, sketch curve_id, or sketch_id"
                )

        # Create split face feature
        split_faces = component.features.splitFaceFeatures

        # Determine the type of splitting tool
        if isinstance(splitting_entity, adsk.core.ObjectCollection):
            # Multiple curves from a sketch
            split_input = split_faces.createInput(faces, splitting_entity, extend_splitting_tool)
        else:
            # Single entity (edge or curve)
            split_input = split_faces.createInput(faces, splitting_entity, extend_splitting_tool)

        # Create the split
        split_feature = split_faces.add(split_input)

        if not split_feature:
            raise FeatureError("split_face", "Split face operation failed")

        # Register feature
        feature_id = registry.register_feature(split_feature)

        return {
            "success": True,
            "feature": {
                "id": feature_id,
                "type": "SplitFaceFeature",
            },
            "split": {
                "face_ids": face_ids,
                "splitting_tool": splitting_tool,
                "extend_splitting_tool": extend_splitting_tool,
            },
        }

    except Exception as e:
        if isinstance(e, (InvalidParameterError, EntityNotFoundError, FeatureError)):
            raise
        raise FeatureError("split_face", f"Failed to split faces: {str(e)}", fusion_error=str(e))
