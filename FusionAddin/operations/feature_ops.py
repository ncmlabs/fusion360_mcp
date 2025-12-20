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
) -> Dict[str, Any]:
    """Create a loft between multiple profiles.

    Args:
        sketch_ids: List of sketch IDs (in order from start to end)
        profile_indices: Optional list of profile indices for each sketch
        operation: "new_body", "join", "cut", or "intersect"
        is_solid: Create solid (True) or surface (False)
        is_closed: Close the loft ends
        name: Optional name for created body

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
