"""Validation operations for Fusion 360 MCP Add-in.

These operations provide measurement, interference detection,
and validation functionality for AI design verification.
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
from shared.exceptions import (
    DesignStateError,
    EntityNotFoundError,
    InvalidParameterError,
    ValidationError,
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


def _get_entity_by_id(entity_id: str) -> Any:
    """Get any entity (body, face, edge, vertex, sketch) by ID.

    Args:
        entity_id: Entity ID string

    Returns:
        Fusion entity object

    Raises:
        EntityNotFoundError: If entity not found
    """
    registry = get_registry()
    design = _get_active_design()

    # Try body first
    entity = registry.get_body(entity_id)
    if entity:
        return entity

    # Try face
    entity = registry.get_sub_entity(entity_id)
    if entity:
        return entity

    # Try sketch
    entity = registry.get_sketch(entity_id)
    if entity:
        return entity

    # Try to find by name in the design
    root = design.rootComponent

    # Check bodies by name
    for body in root.bRepBodies:
        if body.name == entity_id:
            registry.register_body(body)
            return body

    # Check all components for bodies
    for occurrence in root.allOccurrences:
        for body in occurrence.component.bRepBodies:
            if body.name == entity_id:
                registry.register_body(body)
                return body

    raise EntityNotFoundError(
        "Entity",
        entity_id,
        registry.get_available_body_ids() + registry.get_available_sketch_ids()
    )


def _serialize_point3d(point: Any) -> Dict[str, float]:
    """Serialize a Point3D to dict with mm units.

    Args:
        point: Fusion Point3D object (in cm)

    Returns:
        Dict with x, y, z in mm
    """
    if not point:
        return {"x": 0.0, "y": 0.0, "z": 0.0}

    # Convert from cm to mm
    return {
        "x": round(point.x * 10.0, 6),
        "y": round(point.y * 10.0, 6),
        "z": round(point.z * 10.0, 6),
    }


def measure_distance(
    entity1_id: str,
    entity2_id: str,
) -> Dict[str, Any]:
    """Measure minimum distance between two entities.

    Supports body-to-body, face-to-face, edge-to-edge, and point-to-point
    measurements using the Fusion 360 MeasureManager.

    Args:
        entity1_id: ID of the first entity
        entity2_id: ID of the second entity

    Returns:
        Dict with:
            - distance: Minimum distance in mm
            - point1: Closest point on entity1 (x, y, z in mm)
            - point2: Closest point on entity2 (x, y, z in mm)

    Raises:
        EntityNotFoundError: If entity not found
        ValidationError: If measurement fails
    """
    app = adsk.core.Application.get()
    measure_mgr = app.measureManager

    # Get entities
    entity1 = _get_entity_by_id(entity1_id)
    entity2 = _get_entity_by_id(entity2_id)

    try:
        # Measure minimum distance
        result = measure_mgr.measureMinimumDistance(entity1, entity2)

        if not result:
            raise ValidationError(
                "measurement",
                f"Failed to measure distance between {entity1_id} and {entity2_id}",
                suggestion="Ensure both entities are valid geometric objects."
            )

        # Get distance in mm (Fusion uses cm internally)
        distance_mm = result.value * 10.0

        # Get closest points
        point1 = _serialize_point3d(result.positionOne)
        point2 = _serialize_point3d(result.positionTwo)

        return {
            "success": True,
            "distance": round(distance_mm, 6),
            "point1": point1,
            "point2": point2,
            "entity1_id": entity1_id,
            "entity2_id": entity2_id,
        }

    except Exception as e:
        if isinstance(e, (EntityNotFoundError, ValidationError)):
            raise

        raise ValidationError(
            "measurement",
            f"Failed to measure distance: {str(e)}",
            suggestion="Ensure both entities support distance measurement."
        )


def measure_angle(
    entity1_id: str,
    entity2_id: str,
) -> Dict[str, Any]:
    """Measure angle between two entities.

    Supports angles between faces, edges, or planar entities.
    Returns the angle in degrees.

    Args:
        entity1_id: ID of the first entity (face or edge)
        entity2_id: ID of the second entity (face or edge)

    Returns:
        Dict with:
            - angle: Angle in degrees (0-180)
            - entity1_id: First entity ID
            - entity2_id: Second entity ID

    Raises:
        EntityNotFoundError: If entity not found
        ValidationError: If angle measurement fails
    """
    app = adsk.core.Application.get()
    measure_mgr = app.measureManager

    # Get entities
    entity1 = _get_entity_by_id(entity1_id)
    entity2 = _get_entity_by_id(entity2_id)

    try:
        # Measure angle between entities
        result = measure_mgr.measureAngle(entity1, entity2)

        if not result:
            raise ValidationError(
                "measurement",
                f"Failed to measure angle between {entity1_id} and {entity2_id}",
                suggestion="Ensure both entities are planar faces or linear edges."
            )

        # Get angle in degrees (Fusion returns radians)
        angle_degrees = math.degrees(result.value)

        return {
            "success": True,
            "angle": round(angle_degrees, 6),
            "entity1_id": entity1_id,
            "entity2_id": entity2_id,
        }

    except Exception as e:
        if isinstance(e, (EntityNotFoundError, ValidationError)):
            raise

        raise ValidationError(
            "measurement",
            f"Failed to measure angle: {str(e)}",
            suggestion="Angle measurement requires planar faces or linear edges."
        )


def check_interference(
    body_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Check for interference (collisions) between bodies.

    Analyzes overlapping volumes between bodies in the design.
    Can check all bodies or a specific subset.

    Args:
        body_ids: Optional list of body IDs to check.
                 If None, checks all bodies in root component.

    Returns:
        Dict with:
            - has_interference: True if any interference found
            - interferences: List of interference details
                - body1: ID of first body
                - body2: ID of second body
                - volume: Interference volume in mm³
            - bodies_checked: Number of bodies analyzed

    Raises:
        EntityNotFoundError: If specified body not found
        ValidationError: If interference check fails
    """
    design = _get_active_design()
    registry = get_registry()
    root = design.rootComponent

    # Collect bodies to check
    bodies_to_check = adsk.core.ObjectCollection.create()

    if body_ids:
        # Check specific bodies
        for body_id in body_ids:
            body = registry.get_body(body_id)
            if not body:
                # Try to find by name
                found = False
                for brep_body in root.bRepBodies:
                    if brep_body.name == body_id:
                        body = brep_body
                        registry.register_body(body)
                        found = True
                        break

                if not found:
                    for occurrence in root.allOccurrences:
                        for brep_body in occurrence.component.bRepBodies:
                            if brep_body.name == body_id:
                                body = brep_body
                                registry.register_body(body)
                                found = True
                                break
                        if found:
                            break

                if not found:
                    available = registry.get_available_body_ids()
                    raise EntityNotFoundError("Body", body_id, available)

            bodies_to_check.add(body)
    else:
        # Check all bodies in root component
        for body in root.bRepBodies:
            bodies_to_check.add(body)
            registry.register_body(body)

        # Also check bodies in occurrences
        for occurrence in root.allOccurrences:
            for body in occurrence.component.bRepBodies:
                bodies_to_check.add(body)
                registry.register_body(body)

    bodies_count = bodies_to_check.count

    if bodies_count < 2:
        return {
            "success": True,
            "has_interference": False,
            "interferences": [],
            "bodies_checked": bodies_count,
            "message": "Need at least 2 bodies to check interference"
        }

    try:
        # Create interference input
        interference_input = design.createInterferenceInput(bodies_to_check)
        interference_input.areCoincidentFacesIncluded = False

        # Run analysis
        results = design.analyzeInterference(interference_input)

        interferences = []

        if results and results.count > 0:
            for i in range(results.count):
                result = results.item(i)

                # Get interfering entities
                entity1 = result.entityOne
                entity2 = result.entityTwo
                interference_body = result.interferenceBody

                # Get entity IDs
                entity1_id = None
                entity2_id = None

                # Try to get body names/IDs
                if hasattr(entity1, 'name'):
                    entity1_id = entity1.name
                elif hasattr(entity1, 'component') and hasattr(entity1.component, 'name'):
                    entity1_id = entity1.component.name

                if hasattr(entity2, 'name'):
                    entity2_id = entity2.name
                elif hasattr(entity2, 'component') and hasattr(entity2.component, 'name'):
                    entity2_id = entity2.component.name

                # Get interference volume (convert from cm³ to mm³)
                volume_mm3 = 0.0
                if interference_body:
                    volume_cm3 = interference_body.volume
                    volume_mm3 = volume_cm3 * 1000.0  # cm³ to mm³

                interferences.append({
                    "body1": entity1_id or "unknown",
                    "body2": entity2_id or "unknown",
                    "volume": round(volume_mm3, 6),
                })

        return {
            "success": True,
            "has_interference": len(interferences) > 0,
            "interferences": interferences,
            "bodies_checked": bodies_count,
        }

    except Exception as e:
        if isinstance(e, (EntityNotFoundError, ValidationError)):
            raise

        raise ValidationError(
            "interference",
            f"Interference analysis failed: {str(e)}",
            suggestion="Ensure all bodies are valid solid bodies."
        )


def get_body_properties(
    body_id: str,
) -> Dict[str, Any]:
    """Get detailed physical properties of a body.

    Returns comprehensive information about a body including
    volume, surface area, center of mass, bounding box, and
    topology counts.

    Args:
        body_id: ID of the body to analyze

    Returns:
        Dict with:
            - volume: Body volume in mm³
            - area: Surface area in mm²
            - center_of_mass: Center of mass point (x, y, z in mm)
            - bounding_box: Bounding box with min/max points and dimensions
            - dimensions: Width, depth, height in mm
            - faces_count: Number of faces
            - edges_count: Number of edges
            - vertices_count: Number of vertices
            - is_solid: True if solid body

    Raises:
        EntityNotFoundError: If body not found
        ValidationError: If property retrieval fails
    """
    registry = get_registry()
    design = _get_active_design()
    root = design.rootComponent

    # Get body
    body = registry.get_body(body_id)

    if not body:
        # Try to find by name
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

    try:
        # Get physical properties
        # Volume in mm³ (Fusion stores in cm³)
        volume_mm3 = body.volume * 1000.0

        # Surface area in mm² (Fusion stores in cm²)
        area_mm2 = body.area * 100.0

        # Is solid
        is_solid = body.isSolid

        # Get center of mass from physical properties
        center_of_mass = {"x": 0.0, "y": 0.0, "z": 0.0}
        physical_props = body.physicalProperties
        if physical_props:
            com = physical_props.centerOfMass
            if com:
                center_of_mass = _serialize_point3d(com)

        # Get bounding box
        bbox = body.boundingBox
        bounding_box = None
        dimensions = None

        if bbox:
            min_point = _serialize_point3d(bbox.minPoint)
            max_point = _serialize_point3d(bbox.maxPoint)

            width = max_point["x"] - min_point["x"]
            depth = max_point["y"] - min_point["y"]
            height = max_point["z"] - min_point["z"]

            bounding_box = {
                "min": [min_point["x"], min_point["y"], min_point["z"]],
                "max": [max_point["x"], max_point["y"], max_point["z"]],
            }

            dimensions = {
                "width": round(width, 6),
                "depth": round(depth, 6),
                "height": round(height, 6),
            }

        # Get topology counts
        faces_count = body.faces.count if body.faces else 0
        edges_count = body.edges.count if body.edges else 0
        vertices_count = body.vertices.count if body.vertices else 0

        return {
            "success": True,
            "properties": {
                "volume": round(volume_mm3, 6),
                "area": round(area_mm2, 6),
                "center_of_mass": center_of_mass,
                "bounding_box": bounding_box,
                "dimensions": dimensions,
                "faces_count": faces_count,
                "edges_count": edges_count,
                "vertices_count": vertices_count,
            },
            "body_id": body_id,
            "is_solid": is_solid,
        }

    except Exception as e:
        if isinstance(e, (EntityNotFoundError, ValidationError)):
            raise

        raise ValidationError(
            "body_properties",
            f"Failed to get body properties: {str(e)}",
            suggestion="Ensure the body is a valid BRep body."
        )


def get_sketch_status(
    sketch_id: str,
) -> Dict[str, Any]:
    """Get the constraint status of a sketch.

    Returns information about whether a sketch is fully constrained,
    the number of under-constrained curves, and profile validity.

    Args:
        sketch_id: ID of the sketch to analyze

    Returns:
        Dict with:
            - is_fully_constrained: True if fully constrained
            - under_constrained_count: Number of under-constrained curves
            - profiles_count: Number of closed profiles
            - curves_count: Number of sketch curves
            - constraints_count: Number of constraints
            - dimensions_count: Number of dimensions
            - has_valid_profiles: True if has at least one profile

    Raises:
        EntityNotFoundError: If sketch not found
        ValidationError: If status retrieval fails
    """
    registry = get_registry()
    design = _get_active_design()
    root = design.rootComponent

    # Get sketch
    sketch = registry.get_sketch(sketch_id)

    if not sketch:
        # Try to find by name
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

    try:
        # Count under-constrained curves
        under_constrained_count = 0
        curves_count = 0

        sketch_curves = sketch.sketchCurves
        if sketch_curves:
            # Count all curves
            for curve_type in [sketch_curves.sketchLines,
                              sketch_curves.sketchCircles,
                              sketch_curves.sketchArcs,
                              sketch_curves.sketchEllipses,
                              sketch_curves.sketchFittedSplines]:
                if curve_type:
                    curves_count += curve_type.count
                    for curve in curve_type:
                        if hasattr(curve, 'isFullyConstrained'):
                            if not curve.isFullyConstrained:
                                under_constrained_count += 1

        # Check if sketch is fully constrained
        is_fully_constrained = under_constrained_count == 0

        # Get profiles count
        profiles_count = sketch.profiles.count if sketch.profiles else 0
        has_valid_profiles = profiles_count > 0

        # Get constraints count
        constraints_count = 0
        if hasattr(sketch, 'geometricConstraints') and sketch.geometricConstraints:
            constraints_count = sketch.geometricConstraints.count

        # Get dimensions count
        dimensions_count = 0
        if hasattr(sketch, 'sketchDimensions') and sketch.sketchDimensions:
            dimensions_count = sketch.sketchDimensions.count

        return {
            "success": True,
            "sketch_id": sketch_id,
            "is_fully_constrained": is_fully_constrained,
            "under_constrained_count": under_constrained_count,
            "profiles_count": profiles_count,
            "curves_count": curves_count,
            "constraints_count": constraints_count,
            "dimensions_count": dimensions_count,
            "has_valid_profiles": has_valid_profiles,
        }

    except Exception as e:
        if isinstance(e, (EntityNotFoundError, ValidationError)):
            raise

        raise ValidationError(
            "sketch_status",
            f"Failed to get sketch status: {str(e)}",
            suggestion="Ensure the sketch exists and is accessible."
        )
