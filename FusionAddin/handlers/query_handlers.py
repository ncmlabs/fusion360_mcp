"""Query handlers for Fusion 360 MCP Add-in.

These handlers are called from the main thread via the EventManager
and have full access to the Fusion 360 API.
"""

from typing import Dict, Any, Optional, List
import sys
import os

# Add parent directory to path for imports when running in Fusion
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Fusion 360 API imports
try:
    import adsk.core
    import adsk.fusion
    FUSION_AVAILABLE = True
except ImportError:
    FUSION_AVAILABLE = False

from core.entity_registry import get_registry, reset_registry
from serializers.body_serializer import BodySerializer
from serializers.sketch_serializer import SketchSerializer
from serializers.feature_serializer import FeatureSerializer

# Import shared exceptions
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from shared.exceptions import (
    DesignStateError,
    EntityNotFoundError,
    InvalidParameterError,
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


def _get_component(
    design: Any,
    component_id: Optional[str] = None
) -> Any:
    """Get a component by ID or return root component.

    Args:
        design: Fusion Design object
        component_id: Optional component ID

    Returns:
        Fusion Component object

    Raises:
        EntityNotFoundError: If component not found
    """
    if not component_id:
        return design.rootComponent

    registry = get_registry()
    component = registry.get_component(component_id)

    if not component:
        # Try to find by name
        root = design.rootComponent
        if root.name == component_id:
            return root

        # Search occurrences
        for occurrence in root.allOccurrences:
            if occurrence.component.name == component_id:
                return occurrence.component

        # Not found
        available = registry.get_available_component_ids()
        raise EntityNotFoundError("Component", component_id, available)

    return component


def handle_get_design_state(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get current design state summary.

    Returns design info including name, units, and entity counts.

    Args:
        args: Request arguments (unused)

    Returns:
        Dict with design state information
    """
    design = _get_active_design()
    registry = get_registry()

    # Refresh registry from current design
    registry.refresh_from_design(design)

    # Serialize design info
    serializer = FeatureSerializer(registry)
    design_info = serializer.serialize_design_info(design)

    return {"design": design_info}


def handle_get_bodies(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get all bodies in design or component.

    Args:
        args: Request arguments
            - component_id: Optional component ID to filter bodies

    Returns:
        Dict with list of body summaries
    """
    design = _get_active_design()
    registry = get_registry()

    component_id = args.get("component_id")
    component = _get_component(design, component_id)

    serializer = BodySerializer(registry)
    bodies = []

    # Get all bodies from component
    brep_bodies = component.bRepBodies
    if brep_bodies:
        for body in brep_bodies:
            bodies.append(serializer.serialize_summary(body))

    return {
        "bodies": bodies,
        "total": len(bodies),
        "component_id": component_id,
    }


def handle_get_body_by_id(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get detailed body info by ID.

    Args:
        args: Request arguments
            - body_id: Required body ID
            - include_faces: Optional, include face details
            - include_edges: Optional, include edge details
            - include_vertices: Optional, include vertex details

    Returns:
        Dict with full body information

    Raises:
        InvalidParameterError: If body_id not provided
        EntityNotFoundError: If body not found
    """
    design = _get_active_design()
    registry = get_registry()

    body_id = args.get("body_id")
    if not body_id:
        raise InvalidParameterError(
            "body_id",
            None,
            reason="body_id is required"
        )

    include_faces = args.get("include_faces", False)
    include_edges = args.get("include_edges", False)
    include_vertices = args.get("include_vertices", False)

    # Try to get body from registry
    body = registry.get_body(body_id)

    if not body:
        # Try to find by name in design
        root = design.rootComponent
        for brep_body in root.bRepBodies:
            if brep_body.name == body_id:
                body = brep_body
                registry.register_body(body)
                break

        # Search in all components
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

    serializer = BodySerializer(registry)
    body_data = serializer.serialize_full(
        body,
        include_faces=include_faces,
        include_edges=include_edges,
        include_vertices=include_vertices
    )

    return {"body": body_data}


def handle_get_sketches(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get all sketches in design or component.

    Args:
        args: Request arguments
            - component_id: Optional component ID to filter sketches

    Returns:
        Dict with list of sketch summaries
    """
    design = _get_active_design()
    registry = get_registry()

    component_id = args.get("component_id")
    component = _get_component(design, component_id)

    serializer = SketchSerializer(registry)
    sketches = []

    # Get all sketches from component
    sketch_collection = component.sketches
    if sketch_collection:
        for sketch in sketch_collection:
            sketches.append(serializer.serialize_summary(sketch))

    return {
        "sketches": sketches,
        "total": len(sketches),
        "component_id": component_id,
    }


def handle_get_sketch_by_id(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get detailed sketch info by ID.

    Args:
        args: Request arguments
            - sketch_id: Required sketch ID
            - include_curves: Optional, include curve details (default True)
            - include_constraints: Optional, include constraint details
            - include_dimensions: Optional, include dimension details
            - include_profiles: Optional, include profile details

    Returns:
        Dict with full sketch information

    Raises:
        InvalidParameterError: If sketch_id not provided
        EntityNotFoundError: If sketch not found
    """
    design = _get_active_design()
    registry = get_registry()

    sketch_id = args.get("sketch_id")
    if not sketch_id:
        raise InvalidParameterError(
            "sketch_id",
            None,
            reason="sketch_id is required"
        )

    include_curves = args.get("include_curves", True)
    include_constraints = args.get("include_constraints", True)
    include_dimensions = args.get("include_dimensions", True)
    include_profiles = args.get("include_profiles", False)

    # Try to get sketch from registry
    sketch = registry.get_sketch(sketch_id)

    if not sketch:
        # Try to find by name in design
        root = design.rootComponent
        for sk in root.sketches:
            if sk.name == sketch_id:
                sketch = sk
                registry.register_sketch(sketch)
                break

        # Search in all components
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

    serializer = SketchSerializer(registry)
    sketch_data = serializer.serialize_full(
        sketch,
        include_curves=include_curves,
        include_constraints=include_constraints,
        include_dimensions=include_dimensions,
        include_profiles=include_profiles
    )

    return {"sketch": sketch_data}


def handle_get_parameters(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get all parameters in design.

    Args:
        args: Request arguments
            - user_only: Optional, only return user parameters (default False)
            - favorites_only: Optional, only return favorite parameters

    Returns:
        Dict with list of parameters
    """
    design = _get_active_design()
    registry = get_registry()

    user_only = args.get("user_only", False)
    favorites_only = args.get("favorites_only", False)

    serializer = FeatureSerializer(registry)
    parameters = []

    # Get user parameters
    user_params = design.userParameters
    if user_params:
        for param in user_params:
            param_data = serializer.serialize_parameter(param)
            if favorites_only and not param_data.get("is_favorite"):
                continue
            parameters.append(param_data)

    # Get model parameters if not user_only
    if not user_only:
        # Model parameters are accessed through all parameters
        all_params = design.allParameters
        if all_params:
            for param in all_params:
                # Skip if already added as user parameter
                if "User" in type(param).__name__:
                    continue
                param_data = serializer.serialize_parameter(param)
                if favorites_only and not param_data.get("is_favorite"):
                    continue
                parameters.append(param_data)

    return {
        "parameters": parameters,
        "total": len(parameters),
        "user_only": user_only,
    }


def handle_get_timeline(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get design timeline (feature history).

    Args:
        args: Request arguments
            - include_suppressed: Optional, include suppressed features (default True)
            - include_rolled_back: Optional, include rolled back features (default False)

    Returns:
        Dict with timeline entries
    """
    design = _get_active_design()
    registry = get_registry()

    include_suppressed = args.get("include_suppressed", True)
    include_rolled_back = args.get("include_rolled_back", False)

    serializer = FeatureSerializer(registry)
    timeline_entries = []

    timeline = design.timeline
    if timeline:
        marker_position = timeline.markerPosition

        for timeline_obj in timeline:
            entry = serializer.serialize_timeline_entry(timeline_obj)

            # Filter based on args
            if not include_suppressed and entry.get("is_suppressed"):
                continue
            if not include_rolled_back and entry.get("is_rolled_back"):
                continue

            timeline_entries.append(entry)

        return {
            "timeline": timeline_entries,
            "total": len(timeline_entries),
            "marker_position": marker_position,
        }

    return {
        "timeline": [],
        "total": 0,
        "marker_position": 0,
    }
