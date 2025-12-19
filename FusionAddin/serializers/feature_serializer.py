"""Feature serializer for Fusion 360 feature and timeline entities.

Converts Fusion 360 Feature, Parameter, and Timeline objects
to JSON-serializable dictionaries matching Server Pydantic models.
"""

from typing import Dict, Any, List, Optional, TYPE_CHECKING
from .base import BaseSerializer, FusionObject

if TYPE_CHECKING:
    from core.entity_registry import EntityRegistry


class FeatureSerializer(BaseSerializer):
    """Serializer for feature and timeline entities.

    Handles serialization of features, parameters, and timeline entries
    from Fusion 360's parametric modeling system.
    """

    # Feature type mapping from class names
    FEATURE_TYPE_MAP = {
        "ExtrudeFeature": "extrude",
        "RevolveFeature": "revolve",
        "SweepFeature": "sweep",
        "LoftFeature": "loft",
        "FilletFeature": "fillet",
        "ChamferFeature": "chamfer",
        "HoleFeature": "hole",
        "ShellFeature": "shell",
        "DraftFeature": "draft",
        "OffsetFeature": "offset",
        "ThickenFeature": "thicken",
        "CombineFeature": "combine",
        "SplitBodyFeature": "split_body",
        "SplitFaceFeature": "split_face",
        "MoveFeature": "move",
        "CopyFeature": "copy",
        "MirrorFeature": "mirror",
        "PatternFeature": "pattern",
        "RectangularPatternFeature": "rectangular_pattern",
        "CircularPatternFeature": "circular_pattern",
        "ThreadFeature": "thread",
        "RibFeature": "rib",
        "WebFeature": "web",
        "BoxFeature": "box",
        "CylinderFeature": "cylinder",
        "SphereFeature": "sphere",
        "TorusFeature": "torus",
        "CoilFeature": "coil",
        "PipeFeature": "pipe",
        "BaseFeature": "base",
        "Sketch": "sketch",
        "ConstructionPlane": "construction_plane",
        "ConstructionAxis": "construction_axis",
        "ConstructionPoint": "construction_point",
    }

    # Extent type mapping
    EXTENT_TYPE_MAP = {
        0: "one_side",
        1: "two_sides",
        2: "symmetric",
        3: "to_entity",
        4: "all",
    }

    def serialize_parameter(self, parameter: FusionObject) -> Dict[str, Any]:
        """Serialize a parameter to dict.

        Args:
            parameter: Fusion Parameter object (UserParameter or ModelParameter)

        Returns:
            Dict matching Parameter Pydantic model
        """
        param_id = self.registry.register_parameter(parameter)

        # Get value and expression
        value = self.safe_get(parameter, 'value', 0.0)
        expression = self.safe_get(parameter, 'expression', str(value))

        # Get unit
        unit = self.safe_get(parameter, 'unit', '')

        # Determine if user or model parameter
        is_user_parameter = "User" in type(parameter).__name__

        # Get comment if available
        comment = self.safe_get(parameter, 'comment', '')

        # Check if it's a favorite
        is_favorite = self.safe_get(parameter, 'isFavorite', False)

        return {
            "id": param_id,
            "name": self.safe_get(parameter, 'name', param_id),
            "value": value,
            "expression": expression,
            "unit": unit,
            "is_user_parameter": is_user_parameter,
            "comment": comment,
            "is_favorite": is_favorite,
        }

    def serialize_timeline_entry(self, timeline_obj: FusionObject) -> Dict[str, Any]:
        """Serialize a timeline object to dict.

        Args:
            timeline_obj: Fusion TimelineObject

        Returns:
            Dict with timeline entry information
        """
        # Get the entity this timeline object represents
        entity = self.safe_get(timeline_obj, 'entity')
        entity_type = type(entity).__name__ if entity else "Unknown"

        # Map to feature type
        feature_type = self.FEATURE_TYPE_MAP.get(entity_type, entity_type.lower())

        # Get name
        name = ""
        if entity:
            name = self.safe_get(entity, 'name', '')

        # Get timeline index
        index = self.safe_get(timeline_obj, 'index', 0)

        # Check suppression status
        is_suppressed = self.safe_get(timeline_obj, 'isSuppressed', False)

        # Check if it's a group
        is_group = self.safe_get(timeline_obj, 'isGroup', False)

        # Check if rolled back
        is_rolled_back = self.safe_get(timeline_obj, 'isRolledBack', False)

        # Check health status
        health_state = self.safe_get(timeline_obj, 'healthState', 0)
        # 0 = ErrorFeatureHealthState, 1 = WarningFeatureHealthState, 2 = HealthyFeatureHealthState
        health_map = {0: "error", 1: "warning", 2: "healthy"}
        health = health_map.get(health_state, "unknown")

        # Get parent group index if in a group
        parent_group_index = None
        parent_group = self.safe_get(timeline_obj, 'parentGroup')
        if parent_group:
            parent_group_index = self.safe_get(parent_group, 'index')

        return {
            "index": index,
            "name": name,
            "feature_type": feature_type,
            "is_suppressed": is_suppressed,
            "is_group": is_group,
            "is_rolled_back": is_rolled_back,
            "health_state": health,
            "parent_group_index": parent_group_index,
        }

    def serialize_feature(
        self,
        feature: FusionObject,
        include_inputs: bool = False,
        include_outputs: bool = False
    ) -> Dict[str, Any]:
        """Serialize a feature to dict.

        Args:
            feature: Fusion Feature object
            include_inputs: Include feature input details
            include_outputs: Include feature output details (created bodies, etc.)

        Returns:
            Dict matching Feature Pydantic model
        """
        feature_id = self.registry.register_feature(feature)

        # Get feature type
        entity_type = type(feature).__name__
        feature_type = self.FEATURE_TYPE_MAP.get(entity_type, entity_type.lower())

        # Get name
        name = self.safe_get(feature, 'name', feature_id)

        # Check suppression
        is_suppressed = self.safe_get(feature, 'isSuppressed', False)

        # Get timeline object for health status
        timeline_obj = self.safe_get(feature, 'timelineObject')
        health_state = "healthy"
        timeline_index = None
        if timeline_obj:
            health_code = self.safe_get(timeline_obj, 'healthState', 2)
            health_map = {0: "error", 1: "warning", 2: "healthy"}
            health_state = health_map.get(health_code, "unknown")
            timeline_index = self.safe_get(timeline_obj, 'index')

        # Get parent component
        component_id = None
        parent_component = self.safe_get(feature, 'parentComponent')
        if parent_component:
            component_id = self.registry.register_component(parent_component)

        result = {
            "id": feature_id,
            "name": name,
            "feature_type": feature_type,
            "is_suppressed": is_suppressed,
            "health_state": health_state,
            "timeline_index": timeline_index,
            "component_id": component_id,
        }

        # Include inputs if requested
        if include_inputs:
            result["inputs"] = self._serialize_feature_inputs(feature, feature_type)

        # Include outputs if requested
        if include_outputs:
            result["outputs"] = self._serialize_feature_outputs(feature)

        return result

    def _serialize_feature_inputs(
        self,
        feature: FusionObject,
        feature_type: str
    ) -> Dict[str, Any]:
        """Serialize feature inputs based on type."""
        inputs = {}

        # Common inputs
        if hasattr(feature, 'operation'):
            operation = self.safe_get(feature, 'operation')
            # Map operation enum to string
            op_map = {
                0: "join",
                1: "cut",
                2: "intersect",
                3: "new_body",
                4: "new_component",
            }
            inputs["operation"] = op_map.get(operation, "unknown")

        # Type-specific inputs
        if feature_type == "extrude":
            inputs.update(self._serialize_extrude_inputs(feature))
        elif feature_type == "revolve":
            inputs.update(self._serialize_revolve_inputs(feature))
        elif feature_type in ("fillet", "chamfer"):
            inputs.update(self._serialize_edge_feature_inputs(feature))

        return inputs

    def _serialize_extrude_inputs(self, feature: FusionObject) -> Dict[str, Any]:
        """Serialize extrude feature inputs."""
        inputs = {}

        # Get extent type
        extent_type = self.safe_get(feature, 'extentType')
        if extent_type is not None:
            inputs["extent_type"] = self.EXTENT_TYPE_MAP.get(extent_type, "unknown")

        # Get extent one (distance)
        extent_one = self.safe_get(feature, 'extentOne')
        if extent_one:
            distance = self.safe_get(extent_one, 'distance')
            if distance:
                inputs["distance"] = self.safe_get(distance, 'value', 0.0)

        # Get taper angle if available
        taper_angle = self.safe_get(feature, 'taperAngleOne')
        if taper_angle:
            inputs["taper_angle"] = self.safe_get(taper_angle, 'value', 0.0)

        return inputs

    def _serialize_revolve_inputs(self, feature: FusionObject) -> Dict[str, Any]:
        """Serialize revolve feature inputs."""
        inputs = {}

        # Get angle
        angle = self.safe_get(feature, 'angle')
        if angle:
            inputs["angle"] = self.safe_get(angle, 'value', 0.0)

        # Get axis
        axis = self.safe_get(feature, 'axis')
        if axis:
            # Try to get axis type
            inputs["axis_type"] = type(axis).__name__

        return inputs

    def _serialize_edge_feature_inputs(self, feature: FusionObject) -> Dict[str, Any]:
        """Serialize fillet/chamfer feature inputs."""
        inputs = {}

        # Get edges
        edges = self.safe_get(feature, 'edges')
        if edges:
            inputs["edges_count"] = edges.count

        # Get radius/distance for fillet
        radius = self.safe_get(feature, 'radius')
        if radius:
            inputs["radius"] = self.safe_get(radius, 'value', 0.0)

        # Get distance for chamfer
        distance = self.safe_get(feature, 'distance')
        if distance:
            inputs["distance"] = self.safe_get(distance, 'value', 0.0)

        return inputs

    def _serialize_feature_outputs(self, feature: FusionObject) -> Dict[str, Any]:
        """Serialize feature outputs (created/modified bodies)."""
        outputs = {}

        # Get created bodies
        bodies = self.safe_get(feature, 'bodies')
        if bodies:
            outputs["bodies"] = [
                self.registry.register_body(body)
                for body in bodies
            ]

        # Get created faces
        faces = self.safe_get(feature, 'faces')
        if faces:
            outputs["faces_count"] = faces.count

        return outputs

    def serialize_design_info(self, design: FusionObject) -> Dict[str, Any]:
        """Serialize design state/info.

        Args:
            design: Fusion Design object

        Returns:
            Dict matching DesignInfo Pydantic model
        """
        # Get design name
        name = self.safe_get(design, 'rootComponent')
        if name:
            name = self.safe_get(name, 'name', 'Untitled')
        else:
            name = 'Untitled'

        # Get units
        units_manager = self.safe_get(design, 'unitsManager')
        units = "mm"
        if units_manager:
            # Get default length unit
            default_unit = self.safe_get(units_manager, 'defaultLengthUnits', '')
            units = default_unit if default_unit else "mm"

        # Count entities
        root_component = self.safe_get(design, 'rootComponent')
        bodies_count = 0
        sketches_count = 0
        components_count = 1  # Root component

        if root_component:
            # Count bodies in root
            bodies = self.safe_get(root_component, 'bRepBodies')
            if bodies:
                bodies_count = bodies.count

            # Count sketches in root
            sketches = self.safe_get(root_component, 'sketches')
            if sketches:
                sketches_count = sketches.count

            # Count all components (including nested)
            all_occurrences = self.safe_get(root_component, 'allOccurrences')
            if all_occurrences:
                components_count += all_occurrences.count

        # Get timeline count
        timeline = self.safe_get(design, 'timeline')
        timeline_count = 0
        if timeline:
            timeline_count = timeline.count

        # Get active component
        active_component_id = None
        active_component = self.safe_get(design, 'activeComponent')
        if active_component:
            active_component_id = self.registry.register_component(active_component)

        return {
            "name": name,
            "units": units,
            "bodies_count": bodies_count,
            "sketches_count": sketches_count,
            "components_count": components_count,
            "timeline_count": timeline_count,
            "active_component_id": active_component_id,
        }
