"""Assembly operations for Fusion 360 MCP Add-in.

These operations handle component creation, joint creation,
and assembly management using the Fusion 360 API.
"""

from typing import Dict, Any, Optional, List

# Fusion 360 API imports
try:
    import adsk.core
    import adsk.fusion
    FUSION_AVAILABLE = True
except ImportError:
    FUSION_AVAILABLE = False

from core.entity_registry import get_registry
from serializers.component_serializer import ComponentSerializer
from shared.exceptions import (
    DesignStateError,
    EntityNotFoundError,
    FeatureError,
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


def _dict_to_matrix3d(transform_dict: Dict[str, Any]) -> Any:
    """Convert a transform dict to a Fusion Matrix3D.

    Args:
        transform_dict: Dict with 'data' (4x4 array) or 'translation' keys

    Returns:
        adsk.core.Matrix3D object
    """
    matrix = adsk.core.Matrix3D.create()

    if transform_dict is None:
        return matrix

    # If data array is provided, set from array
    data = transform_dict.get('data')
    if data and len(data) == 4:
        # Flatten 4x4 to 16-element array
        flat = []
        for row in data:
            flat.extend(row)
        if len(flat) == 16:
            matrix.setWithArray(flat)
            return matrix

    # If only translation is provided, create translation matrix
    translation = transform_dict.get('translation')
    if translation:
        x = translation.get('x', 0.0)
        y = translation.get('y', 0.0)
        z = translation.get('z', 0.0)
        # Convert mm to cm (Fusion internal units)
        vector = adsk.core.Vector3D.create(x / 10.0, y / 10.0, z / 10.0)
        matrix.translation = vector

    return matrix


# --- Component Operations ---

def create_component(
    name: str,
    transform: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a new component in the design.

    Creates a new component as a child of the root component
    with an optional transform.

    Args:
        name: Name for the new component
        transform: Optional transform dict with 'translation' or 'data'

    Returns:
        Dict with component and occurrence info

    Raises:
        FeatureError: If component creation fails
    """
    design = _get_active_design()
    registry = get_registry()
    root = design.rootComponent

    try:
        # Create transform matrix
        if transform:
            matrix = _dict_to_matrix3d(transform)
        else:
            matrix = adsk.core.Matrix3D.create()

        # Create new occurrence with new component
        occurrence = root.occurrences.addNewComponent(matrix)

        if not occurrence:
            raise FeatureError(
                "create_component",
                "Failed to create component occurrence"
            )

        # Get the new component and set its name
        component = occurrence.component
        component.name = name

        # Register entities
        component_id = registry.register_component(component)
        occurrence_id = registry.register_occurrence(occurrence)

        # Serialize results
        serializer = ComponentSerializer(registry)

        return {
            "success": True,
            "component": serializer.serialize_component_summary(component),
            "occurrence": serializer.serialize_occurrence(occurrence),
            "component_id": component_id,
            "occurrence_id": occurrence_id,
        }

    except Exception as e:
        if isinstance(e, (FeatureError, DesignStateError)):
            raise
        raise FeatureError(
            "create_component",
            f"Failed to create component: {str(e)}"
        )


def get_components() -> Dict[str, Any]:
    """Get all components in the design.

    Returns:
        Dict with list of component summaries

    Raises:
        DesignStateError: If no design is active
    """
    design = _get_active_design()
    registry = get_registry()
    root = design.rootComponent

    serializer = ComponentSerializer(registry)
    components = []

    # Add root component
    components.append(serializer.serialize_component_summary(root))

    # Add all unique components from occurrences
    seen_components = {root}

    def collect_components(parent_component):
        occurrences = parent_component.occurrences
        if occurrences:
            for occ in occurrences:
                comp = occ.component
                if comp and comp not in seen_components:
                    seen_components.add(comp)
                    components.append(serializer.serialize_component_summary(comp))
                    collect_components(comp)

    collect_components(root)

    return {
        "success": True,
        "components": components,
        "total": len(components),
    }


def get_component_by_id(component_id: str) -> Dict[str, Any]:
    """Get detailed component info by ID.

    Args:
        component_id: Component ID to retrieve

    Returns:
        Dict with full component info

    Raises:
        EntityNotFoundError: If component not found
    """
    design = _get_active_design()
    registry = get_registry()

    component = registry.get_component(component_id)
    if not component:
        available = registry.get_available_component_ids()
        raise EntityNotFoundError("Component", component_id, available)

    serializer = ComponentSerializer(registry)

    return {
        "success": True,
        "component": serializer.serialize_component_full(component),
    }


def activate_component(component_id: str) -> Dict[str, Any]:
    """Activate a component for editing.

    Sets the specified component as the active component,
    making it the target for new geometry and features.

    Args:
        component_id: Component ID to activate

    Returns:
        Dict confirming activation

    Raises:
        EntityNotFoundError: If component not found
        FeatureError: If activation fails
    """
    design = _get_active_design()
    registry = get_registry()

    component = registry.get_component(component_id)
    if not component:
        available = registry.get_available_component_ids()
        raise EntityNotFoundError("Component", component_id, available)

    try:
        # Activate the component
        result = design.activateRootComponent() if component.isRootComponent else component.activate()

        if result is False:
            raise FeatureError(
                "activate_component",
                f"Failed to activate component '{component_id}'"
            )

        serializer = ComponentSerializer(registry)

        return {
            "success": True,
            "active_component": serializer.serialize_component_summary(component),
            "component_id": component_id,
        }

    except Exception as e:
        if isinstance(e, (FeatureError, EntityNotFoundError)):
            raise
        raise FeatureError(
            "activate_component",
            f"Failed to activate component: {str(e)}"
        )


# --- Occurrence Operations ---

def get_occurrences(component_id: Optional[str] = None) -> Dict[str, Any]:
    """Get all occurrences in the design or within a component.

    Args:
        component_id: Optional component ID to filter occurrences

    Returns:
        Dict with list of occurrence info

    Raises:
        EntityNotFoundError: If specified component not found
    """
    design = _get_active_design()
    registry = get_registry()
    serializer = ComponentSerializer(registry)

    if component_id:
        component = registry.get_component(component_id)
        if not component:
            available = registry.get_available_component_ids()
            raise EntityNotFoundError("Component", component_id, available)
        occurrences = component.occurrences
    else:
        occurrences = design.rootComponent.allOccurrences

    occurrence_list = serializer.serialize_occurrences_list(occurrences)

    return {
        "success": True,
        "occurrences": occurrence_list,
        "total": len(occurrence_list),
    }


def move_occurrence(
    occurrence_id: str,
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
) -> Dict[str, Any]:
    """Move an occurrence to a new position.

    Applies a translation to the occurrence's transform.
    All values are in millimeters.

    Args:
        occurrence_id: Occurrence ID to move
        x: X translation in mm
        y: Y translation in mm
        z: Z translation in mm

    Returns:
        Dict with updated occurrence info

    Raises:
        EntityNotFoundError: If occurrence not found
        FeatureError: If move fails
    """
    design = _get_active_design()
    registry = get_registry()

    occurrence = registry.get_occurrence(occurrence_id)
    if not occurrence:
        available = registry.get_available_occurrence_ids()
        raise EntityNotFoundError("Occurrence", occurrence_id, available)

    try:
        # Get current transform
        current_transform = occurrence.transform

        # Create translation vector (convert mm to cm)
        translation = adsk.core.Vector3D.create(x / 10.0, y / 10.0, z / 10.0)

        # Create new transform with translation applied
        new_transform = current_transform.copy()
        current_translation = new_transform.translation
        new_translation = adsk.core.Vector3D.create(
            current_translation.x + translation.x,
            current_translation.y + translation.y,
            current_translation.z + translation.z
        )
        new_transform.translation = new_translation

        # Apply transform
        occurrence.transform = new_transform

        serializer = ComponentSerializer(registry)

        return {
            "success": True,
            "occurrence": serializer.serialize_occurrence(occurrence),
            "occurrence_id": occurrence_id,
            "translation": {
                "x": x,
                "y": y,
                "z": z,
            },
        }

    except Exception as e:
        if isinstance(e, (FeatureError, EntityNotFoundError)):
            raise
        raise FeatureError(
            "move_occurrence",
            f"Failed to move occurrence: {str(e)}"
        )


# --- Joint Operations ---

def create_joint(
    geometry1_id: str,
    geometry2_id: str,
    joint_type: str = "rigid",
) -> Dict[str, Any]:
    """Create a joint between two geometry entities.

    Creates an assembly joint connecting two geometry entities
    (faces, edges, or construction geometry).

    Args:
        geometry1_id: First geometry entity ID
        geometry2_id: Second geometry entity ID
        joint_type: Type of joint (rigid, revolute, slider, cylindrical,
                   pin_slot, planar, ball)

    Returns:
        Dict with joint info

    Raises:
        EntityNotFoundError: If geometry entities not found
        InvalidParameterError: If joint type is invalid
        FeatureError: If joint creation fails
    """
    design = _get_active_design()
    registry = get_registry()
    root = design.rootComponent

    # Validate joint type
    valid_types = ["rigid", "revolute", "slider", "cylindrical", "pin_slot", "planar", "ball"]
    if joint_type.lower() not in valid_types:
        raise InvalidParameterError(
            "joint_type",
            joint_type,
            reason=f"Invalid joint type. Must be one of: {', '.join(valid_types)}"
        )

    # Resolve geometry entities
    geometry1 = registry.resolve_id(geometry1_id)
    if not geometry1:
        # Try to find in sub-entities
        geometry1 = registry.get_sub_entity(geometry1_id)

    if not geometry1:
        raise EntityNotFoundError(
            "Geometry",
            geometry1_id,
            ["Check available body, face, edge, or construction geometry IDs"]
        )

    geometry2 = registry.resolve_id(geometry2_id)
    if not geometry2:
        geometry2 = registry.get_sub_entity(geometry2_id)

    if not geometry2:
        raise EntityNotFoundError(
            "Geometry",
            geometry2_id,
            ["Check available body, face, edge, or construction geometry IDs"]
        )

    try:
        # Get the joints collection
        joints = root.joints

        # Create joint geometry input for each entity
        geo1 = adsk.fusion.JointGeometry.createByPoint(geometry1, geometry1.centroid)
        geo2 = adsk.fusion.JointGeometry.createByPoint(geometry2, geometry2.centroid)

        # Create joint input
        joint_input = joints.createInput(geo1, geo2)

        # Set joint type
        joint_type_lower = joint_type.lower()
        if joint_type_lower == "rigid":
            joint_input.setAsRigidJointMotion()
        elif joint_type_lower == "revolute":
            joint_input.setAsRevoluteJointMotion(adsk.fusion.JointDirections.ZAxisJointDirection)
        elif joint_type_lower == "slider":
            joint_input.setAsSliderJointMotion(adsk.fusion.JointDirections.ZAxisJointDirection)
        elif joint_type_lower == "cylindrical":
            joint_input.setAsCylindricalJointMotion(adsk.fusion.JointDirections.ZAxisJointDirection)
        elif joint_type_lower == "pin_slot":
            joint_input.setAsPinSlotJointMotion(
                adsk.fusion.JointDirections.ZAxisJointDirection,
                adsk.fusion.JointDirections.XAxisJointDirection
            )
        elif joint_type_lower == "planar":
            joint_input.setAsPlanarJointMotion(adsk.fusion.JointDirections.ZAxisJointDirection)
        elif joint_type_lower == "ball":
            joint_input.setAsBallJointMotion()

        # Create the joint
        joint = joints.add(joint_input)

        if not joint:
            raise FeatureError(
                "create_joint",
                "Failed to create joint - joints.add() returned None"
            )

        # Register and serialize
        joint_id = registry.register_joint(joint)
        serializer = ComponentSerializer(registry)

        return {
            "success": True,
            "joint": serializer.serialize_joint(joint),
            "joint_id": joint_id,
        }

    except Exception as e:
        if isinstance(e, (FeatureError, EntityNotFoundError, InvalidParameterError)):
            raise
        raise FeatureError(
            "create_joint",
            f"Failed to create joint: {str(e)}"
        )


def create_joint_between_occurrences(
    occurrence1_id: str,
    occurrence2_id: str,
    joint_type: str = "rigid",
) -> Dict[str, Any]:
    """Create a joint between two occurrences.

    Creates an assembly joint using the origins of two occurrences.
    This is a simpler approach when you want to constrain occurrences
    without specifying exact geometry.

    Args:
        occurrence1_id: First occurrence ID
        occurrence2_id: Second occurrence ID
        joint_type: Type of joint (rigid, revolute, slider, cylindrical,
                   pin_slot, planar, ball)

    Returns:
        Dict with joint info

    Raises:
        EntityNotFoundError: If occurrences not found
        InvalidParameterError: If joint type is invalid
        FeatureError: If joint creation fails
    """
    design = _get_active_design()
    registry = get_registry()
    root = design.rootComponent

    # Validate joint type
    valid_types = ["rigid", "revolute", "slider", "cylindrical", "pin_slot", "planar", "ball"]
    if joint_type.lower() not in valid_types:
        raise InvalidParameterError(
            "joint_type",
            joint_type,
            reason=f"Invalid joint type. Must be one of: {', '.join(valid_types)}"
        )

    # Get occurrences
    occurrence1 = registry.get_occurrence(occurrence1_id)
    if not occurrence1:
        available = registry.get_available_occurrence_ids()
        raise EntityNotFoundError("Occurrence", occurrence1_id, available)

    occurrence2 = registry.get_occurrence(occurrence2_id)
    if not occurrence2:
        available = registry.get_available_occurrence_ids()
        raise EntityNotFoundError("Occurrence", occurrence2_id, available)

    try:
        # Get the joints collection
        joints = root.joints

        # Create joint geometry from occurrence origins
        geo1 = adsk.fusion.JointGeometry.createByPoint(occurrence1, adsk.core.Point3D.create(0, 0, 0))
        geo2 = adsk.fusion.JointGeometry.createByPoint(occurrence2, adsk.core.Point3D.create(0, 0, 0))

        # Create joint input
        joint_input = joints.createInput(geo1, geo2)

        # Set joint type
        joint_type_lower = joint_type.lower()
        if joint_type_lower == "rigid":
            joint_input.setAsRigidJointMotion()
        elif joint_type_lower == "revolute":
            joint_input.setAsRevoluteJointMotion(adsk.fusion.JointDirections.ZAxisJointDirection)
        elif joint_type_lower == "slider":
            joint_input.setAsSliderJointMotion(adsk.fusion.JointDirections.ZAxisJointDirection)
        elif joint_type_lower == "cylindrical":
            joint_input.setAsCylindricalJointMotion(adsk.fusion.JointDirections.ZAxisJointDirection)
        elif joint_type_lower == "pin_slot":
            joint_input.setAsPinSlotJointMotion(
                adsk.fusion.JointDirections.ZAxisJointDirection,
                adsk.fusion.JointDirections.XAxisJointDirection
            )
        elif joint_type_lower == "planar":
            joint_input.setAsPlanarJointMotion(adsk.fusion.JointDirections.ZAxisJointDirection)
        elif joint_type_lower == "ball":
            joint_input.setAsBallJointMotion()

        # Create the joint
        joint = joints.add(joint_input)

        if not joint:
            raise FeatureError(
                "create_joint",
                "Failed to create joint - joints.add() returned None"
            )

        # Register and serialize
        joint_id = registry.register_joint(joint)
        serializer = ComponentSerializer(registry)

        return {
            "success": True,
            "joint": serializer.serialize_joint(joint),
            "joint_id": joint_id,
        }

    except Exception as e:
        if isinstance(e, (FeatureError, EntityNotFoundError, InvalidParameterError)):
            raise
        raise FeatureError(
            "create_joint",
            f"Failed to create joint between occurrences: {str(e)}"
        )


def get_joints() -> Dict[str, Any]:
    """Get all joints in the design.

    Returns:
        Dict with list of joint info

    Raises:
        DesignStateError: If no design is active
    """
    design = _get_active_design()
    registry = get_registry()
    root = design.rootComponent

    serializer = ComponentSerializer(registry)

    # Get joints from root component
    joints = root.joints
    joint_list = serializer.serialize_joints_list(joints)

    # Also get as-built joints
    as_built_joints = root.asBuiltJoints
    if as_built_joints:
        for joint in as_built_joints:
            joint_list.append(serializer.serialize_joint(joint))

    return {
        "success": True,
        "joints": joint_list,
        "total": len(joint_list),
    }


def get_joint_by_id(joint_id: str) -> Dict[str, Any]:
    """Get detailed joint info by ID.

    Args:
        joint_id: Joint ID to retrieve

    Returns:
        Dict with joint info

    Raises:
        EntityNotFoundError: If joint not found
    """
    design = _get_active_design()
    registry = get_registry()

    joint = registry.get_joint(joint_id)
    if not joint:
        available = registry.get_available_joint_ids()
        raise EntityNotFoundError("Joint", joint_id, available)

    serializer = ComponentSerializer(registry)

    return {
        "success": True,
        "joint": serializer.serialize_joint(joint),
    }


def get_component_bodies(component_id: str) -> Dict[str, Any]:
    """Get all bodies within a specific component.

    Args:
        component_id: Component ID to get bodies from

    Returns:
        Dict with list of body summaries

    Raises:
        EntityNotFoundError: If component not found
    """
    design = _get_active_design()
    registry = get_registry()

    component = registry.get_component(component_id)
    if not component:
        available = registry.get_available_component_ids()
        raise EntityNotFoundError("Component", component_id, available)

    from serializers.body_serializer import BodySerializer
    body_serializer = BodySerializer(registry)

    bodies = component.bRepBodies
    body_list = []
    if bodies:
        for body in bodies:
            body_list.append(body_serializer.serialize_summary(body))

    return {
        "success": True,
        "bodies": body_list,
        "total": len(body_list),
        "component_id": component_id,
    }
