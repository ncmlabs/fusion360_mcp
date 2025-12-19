"""Component and assembly serializer for Fusion 360 API objects.

Provides serialization methods for components, occurrences, and joints.
"""

from typing import Dict, Any, List, TYPE_CHECKING

from .base import BaseSerializer, FusionObject

if TYPE_CHECKING:
    from core.entity_registry import EntityRegistry


class ComponentSerializer(BaseSerializer):
    """Serializer for component and assembly entities.

    Handles serialization of:
    - Components (definition containers)
    - Occurrences (component instances)
    - Joints (assembly constraints)
    """

    def serialize_component_summary(self, component: FusionObject) -> Dict[str, Any]:
        """Serialize a component to a summary dict.

        Args:
            component: Fusion Component object

        Returns:
            Dict with component summary info
        """
        comp_id = self.registry.register_component(component)

        # Get content counts
        bodies = getattr(component, 'bRepBodies', None)
        sketches = getattr(component, 'sketches', None)
        occurrences = getattr(component, 'occurrences', None)
        features = getattr(component, 'features', None)

        bodies_count = bodies.count if bodies else 0
        sketches_count = sketches.count if sketches else 0
        occurrences_count = occurrences.count if occurrences else 0

        # Count features
        features_count = 0
        if features:
            for feature_type in ['extrudeFeatures', 'revolveFeatures', 'sweepFeatures',
                                 'loftFeatures', 'filletFeatures', 'chamferFeatures',
                                 'holeFeatures', 'shellFeatures', 'draftFeatures']:
                feature_collection = getattr(features, feature_type, None)
                if feature_collection:
                    features_count += feature_collection.count

        # Get body and sketch IDs
        body_ids = []
        if bodies:
            for body in bodies:
                body_ids.append(self.registry.register_body(body))

        sketch_ids = []
        if sketches:
            for sketch in sketches:
                sketch_ids.append(self.registry.register_sketch(sketch))

        return {
            "id": comp_id,
            "name": self.safe_get(component, 'name', comp_id),
            "is_root": self.safe_get(component, 'isRootComponent', False),
            "is_active": self._is_component_active(component),
            "bodies_count": bodies_count,
            "sketches_count": sketches_count,
            "occurrences_count": occurrences_count,
            "features_count": features_count,
            "body_ids": body_ids,
            "sketch_ids": sketch_ids,
            "parent_id": self._get_parent_id(component),
        }

    def serialize_component_full(self, component: FusionObject) -> Dict[str, Any]:
        """Serialize a component with full details.

        Args:
            component: Fusion Component object

        Returns:
            Dict with full component info including bounding box
        """
        summary = self.serialize_component_summary(component)

        # Add bounding box if available
        bbox = getattr(component, 'boundingBox', None)
        if bbox:
            summary["bounding_box"] = self.serialize_bounding_box(bbox)

        # Add occurrence IDs
        occurrences = getattr(component, 'occurrences', None)
        occurrence_ids = []
        if occurrences:
            for occ in occurrences:
                occurrence_ids.append(self.registry.register_occurrence(occ))
        summary["occurrence_ids"] = occurrence_ids

        return summary

    def serialize_occurrence(self, occurrence: FusionObject) -> Dict[str, Any]:
        """Serialize an occurrence (component instance).

        Args:
            occurrence: Fusion Occurrence object

        Returns:
            Dict with occurrence info including transform
        """
        occ_id = self.registry.register_occurrence(occurrence)

        # Get component reference
        component = getattr(occurrence, 'component', None)
        component_id = None
        if component:
            component_id = self.registry.register_component(component)

        # Get transform
        transform = getattr(occurrence, 'transform', None)

        return {
            "id": occ_id,
            "name": self.safe_get(occurrence, 'name', occ_id),
            "component_id": component_id,
            "transform": self.serialize_matrix3d(transform),
            "is_visible": self.safe_get(occurrence, 'isVisible', True),
            "is_grounded": self.safe_get(occurrence, 'isGrounded', False),
        }

    def serialize_joint(self, joint: FusionObject) -> Dict[str, Any]:
        """Serialize an assembly joint.

        Args:
            joint: Fusion Joint object

        Returns:
            Dict with joint info including type and connected occurrences
        """
        joint_id = self.registry.register_joint(joint)

        # Determine joint type from class name or jointMotion property
        joint_type = self._get_joint_type(joint)

        # Get connected occurrences
        occ1_id = None
        occ2_id = None

        # Try to get occurrence references
        occurrence_one = getattr(joint, 'occurrenceOne', None)
        occurrence_two = getattr(joint, 'occurrenceTwo', None)

        if occurrence_one:
            occ1_id = self.registry.register_occurrence(occurrence_one)
        if occurrence_two:
            occ2_id = self.registry.register_occurrence(occurrence_two)

        # If occurrences not directly available, try geometry
        if not occ1_id or not occ2_id:
            geometry_or_origin_one = getattr(joint, 'geometryOrOriginOne', None)
            geometry_or_origin_two = getattr(joint, 'geometryOrOriginTwo', None)

            if geometry_or_origin_one:
                entity_one = getattr(geometry_or_origin_one, 'entityOne', None)
                if entity_one:
                    occ_one = getattr(entity_one, 'assemblyContext', None)
                    if occ_one:
                        occ1_id = self.registry.register_occurrence(occ_one)

            if geometry_or_origin_two:
                entity_two = getattr(geometry_or_origin_two, 'entityOne', None)
                if entity_two:
                    occ_two = getattr(entity_two, 'assemblyContext', None)
                    if occ_two:
                        occ2_id = self.registry.register_occurrence(occ_two)

        return {
            "id": joint_id,
            "name": self.safe_get(joint, 'name', joint_id),
            "joint_type": joint_type,
            "occurrence1_id": occ1_id,
            "occurrence2_id": occ2_id,
            "is_suppressed": self.safe_get(joint, 'isSuppressed', False),
        }

    def serialize_joints_list(self, joints: Any) -> List[Dict[str, Any]]:
        """Serialize a collection of joints.

        Args:
            joints: Fusion JointList or iterable of joints

        Returns:
            List of joint dicts
        """
        result = []
        if joints:
            for joint in joints:
                result.append(self.serialize_joint(joint))
        return result

    def serialize_occurrences_list(self, occurrences: Any) -> List[Dict[str, Any]]:
        """Serialize a collection of occurrences.

        Args:
            occurrences: Fusion OccurrenceList or iterable

        Returns:
            List of occurrence dicts
        """
        result = []
        if occurrences:
            for occ in occurrences:
                result.append(self.serialize_occurrence(occ))
        return result

    def serialize_components_list(self, components: Any) -> List[Dict[str, Any]]:
        """Serialize a collection of components.

        Args:
            components: Iterable of Component objects

        Returns:
            List of component summary dicts
        """
        result = []
        if components:
            for comp in components:
                result.append(self.serialize_component_summary(comp))
        return result

    # --- Private Helpers ---

    def _is_component_active(self, component: FusionObject) -> bool:
        """Check if component is the active component.

        Args:
            component: Fusion Component object

        Returns:
            True if this is the active component
        """
        try:
            # Get the design and check activeComponent
            parent_design = getattr(component, 'parentDesign', None)
            if parent_design:
                active = getattr(parent_design, 'activeComponent', None)
                return active is component
        except Exception:
            pass
        return False

    def _get_parent_id(self, component: FusionObject) -> str:
        """Get the parent component ID.

        Args:
            component: Fusion Component object

        Returns:
            Parent component ID or None for root
        """
        try:
            # Root component has no parent
            if self.safe_get(component, 'isRootComponent', False):
                return None

            # Try to get parent occurrence's component
            parent_design = getattr(component, 'parentDesign', None)
            if parent_design:
                root = getattr(parent_design, 'rootComponent', None)
                if root:
                    return self.registry.register_component(root)
        except Exception:
            pass
        return None

    def _get_joint_type(self, joint: FusionObject) -> str:
        """Determine the joint type string.

        Args:
            joint: Fusion Joint object

        Returns:
            Joint type string (rigid, revolute, slider, etc.)
        """
        # Try jointMotion property first
        joint_motion = getattr(joint, 'jointMotion', None)
        if joint_motion:
            motion_type = getattr(joint_motion, 'jointType', None)
            if motion_type is not None:
                # Map Fusion joint type enum to string
                type_map = {
                    0: "rigid",       # RigidJointType
                    1: "revolute",    # RevoluteJointType
                    2: "slider",      # SliderJointType
                    3: "cylindrical", # CylindricalJointType
                    4: "pin_slot",    # PinSlotJointType
                    5: "planar",      # PlanarJointType
                    6: "ball",        # BallJointType
                }
                return type_map.get(motion_type, "rigid")

        # Fallback: infer from class name
        class_name = type(joint).__name__
        if "Rigid" in class_name:
            return "rigid"
        elif "Revolute" in class_name:
            return "revolute"
        elif "Slider" in class_name:
            return "slider"
        elif "Cylindrical" in class_name:
            return "cylindrical"
        elif "PinSlot" in class_name:
            return "pin_slot"
        elif "Planar" in class_name:
            return "planar"
        elif "Ball" in class_name:
            return "ball"

        return "rigid"  # Default
