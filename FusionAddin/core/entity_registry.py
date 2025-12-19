"""Entity Registry for stable entity ID tracking.

This module provides a singleton registry that maintains stable ID mappings
for Fusion 360 entities (bodies, sketches, features) across multiple queries.
"""

from typing import Dict, List, Optional, Any
from threading import Lock

# Type alias for Fusion API objects (avoids import at module level)
FusionEntity = Any


class EntityRegistry:
    """Registry for tracking and resolving entity IDs.

    Provides stable ID mappings for Fusion 360 entities. IDs are based on
    entity names when available, otherwise generated using type and index.

    Thread-safe for use across HTTP handler and task execution.
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._lock = Lock()

        # Entity type -> ID -> Fusion object
        self._bodies: Dict[str, FusionEntity] = {}
        self._sketches: Dict[str, FusionEntity] = {}
        self._features: Dict[str, FusionEntity] = {}
        self._components: Dict[str, FusionEntity] = {}
        self._parameters: Dict[str, FusionEntity] = {}
        self._occurrences: Dict[str, FusionEntity] = {}
        self._joints: Dict[str, FusionEntity] = {}

        # Sub-entities (faces, edges, vertices) use composite IDs
        # Format: "{parent_id}_{type}_{index}"
        self._sub_entities: Dict[str, FusionEntity] = {}

        # Track unnamed entity counters for stable ID generation
        self._unnamed_counters: Dict[str, int] = {
            "body": 0,
            "sketch": 0,
            "feature": 0,
            "component": 0,
            "occurrence": 0,
            "joint": 0,
        }

    # --- Body Registration ---

    def register_body(self, body: FusionEntity) -> str:
        """Register a body and return its stable ID.

        Args:
            body: Fusion 360 BRepBody object

        Returns:
            Stable ID for the body (uses name if available)
        """
        with self._lock:
            # Check if already registered by object identity
            for body_id, existing in self._bodies.items():
                if existing is body:
                    return body_id

            # Generate ID from name or counter
            body_id = self._generate_id(body, "body")
            self._bodies[body_id] = body
            return body_id

    def get_body(self, body_id: str) -> Optional[FusionEntity]:
        """Get a body by its ID.

        Args:
            body_id: The body's stable ID

        Returns:
            The Fusion BRepBody object, or None if not found
        """
        with self._lock:
            return self._bodies.get(body_id)

    def get_available_body_ids(self) -> List[str]:
        """Get list of all registered body IDs.

        Returns:
            List of body IDs for error context
        """
        with self._lock:
            return list(self._bodies.keys())

    # --- Sketch Registration ---

    def register_sketch(self, sketch: FusionEntity) -> str:
        """Register a sketch and return its stable ID.

        Args:
            sketch: Fusion 360 Sketch object

        Returns:
            Stable ID for the sketch
        """
        with self._lock:
            for sketch_id, existing in self._sketches.items():
                if existing is sketch:
                    return sketch_id

            sketch_id = self._generate_id(sketch, "sketch")
            self._sketches[sketch_id] = sketch
            return sketch_id

    def get_sketch(self, sketch_id: str) -> Optional[FusionEntity]:
        """Get a sketch by its ID."""
        with self._lock:
            return self._sketches.get(sketch_id)

    def get_available_sketch_ids(self) -> List[str]:
        """Get list of all registered sketch IDs."""
        with self._lock:
            return list(self._sketches.keys())

    # --- Feature Registration ---

    def register_feature(self, feature: FusionEntity) -> str:
        """Register a feature and return its stable ID.

        Args:
            feature: Fusion 360 Feature object

        Returns:
            Stable ID for the feature
        """
        with self._lock:
            for feature_id, existing in self._features.items():
                if existing is feature:
                    return feature_id

            feature_id = self._generate_id(feature, "feature")
            self._features[feature_id] = feature
            return feature_id

    def get_feature(self, feature_id: str) -> Optional[FusionEntity]:
        """Get a feature by its ID."""
        with self._lock:
            return self._features.get(feature_id)

    def get_available_feature_ids(self) -> List[str]:
        """Get list of all registered feature IDs."""
        with self._lock:
            return list(self._features.keys())

    # --- Component Registration ---

    def register_component(self, component: FusionEntity) -> str:
        """Register a component and return its stable ID.

        Args:
            component: Fusion 360 Component object

        Returns:
            Stable ID for the component
        """
        with self._lock:
            for comp_id, existing in self._components.items():
                if existing is component:
                    return comp_id

            comp_id = self._generate_id(component, "component")
            self._components[comp_id] = component
            return comp_id

    def get_component(self, component_id: str) -> Optional[FusionEntity]:
        """Get a component by its ID."""
        with self._lock:
            return self._components.get(component_id)

    def get_available_component_ids(self) -> List[str]:
        """Get list of all registered component IDs."""
        with self._lock:
            return list(self._components.keys())

    # --- Parameter Registration ---

    def register_parameter(self, parameter: FusionEntity) -> str:
        """Register a parameter and return its stable ID.

        Args:
            parameter: Fusion 360 Parameter object

        Returns:
            Stable ID for the parameter (always uses name)
        """
        with self._lock:
            # Parameters always have names
            param_name = getattr(parameter, 'name', None)
            if param_name:
                param_id = param_name
            else:
                param_id = f"param_{len(self._parameters)}"

            self._parameters[param_id] = parameter
            return param_id

    def get_parameter(self, param_id: str) -> Optional[FusionEntity]:
        """Get a parameter by its ID."""
        with self._lock:
            return self._parameters.get(param_id)

    def get_available_parameter_ids(self) -> List[str]:
        """Get list of all registered parameter IDs."""
        with self._lock:
            return list(self._parameters.keys())

    # --- Occurrence Registration ---

    def register_occurrence(self, occurrence: FusionEntity) -> str:
        """Register an occurrence and return its stable ID.

        Args:
            occurrence: Fusion 360 Occurrence object

        Returns:
            Stable ID for the occurrence
        """
        with self._lock:
            for occ_id, existing in self._occurrences.items():
                if existing is occurrence:
                    return occ_id

            occ_id = self._generate_id(occurrence, "occurrence")
            self._occurrences[occ_id] = occurrence
            return occ_id

    def get_occurrence(self, occ_id: str) -> Optional[FusionEntity]:
        """Get an occurrence by its ID."""
        with self._lock:
            return self._occurrences.get(occ_id)

    def get_available_occurrence_ids(self) -> List[str]:
        """Get list of all registered occurrence IDs."""
        with self._lock:
            return list(self._occurrences.keys())

    # --- Joint Registration ---

    def register_joint(self, joint: FusionEntity) -> str:
        """Register a joint and return its stable ID.

        Args:
            joint: Fusion 360 Joint object

        Returns:
            Stable ID for the joint
        """
        with self._lock:
            for joint_id, existing in self._joints.items():
                if existing is joint:
                    return joint_id

            joint_id = self._generate_id(joint, "joint")
            self._joints[joint_id] = joint
            return joint_id

    def get_joint(self, joint_id: str) -> Optional[FusionEntity]:
        """Get a joint by its ID."""
        with self._lock:
            return self._joints.get(joint_id)

    def get_available_joint_ids(self) -> List[str]:
        """Get list of all registered joint IDs."""
        with self._lock:
            return list(self._joints.keys())

    # --- Sub-Entity Registration (Faces, Edges, Vertices) ---

    def register_sub_entity(
        self,
        parent_id: str,
        entity_type: str,
        index: int,
        entity: FusionEntity
    ) -> str:
        """Register a sub-entity (face, edge, vertex) with composite ID.

        Args:
            parent_id: ID of parent body
            entity_type: Type of entity ("face", "edge", "vertex")
            index: Index within parent's collection
            entity: The Fusion API object

        Returns:
            Composite ID in format "{parent_id}_{type}_{index}"
        """
        with self._lock:
            sub_id = f"{parent_id}_{entity_type}_{index}"
            self._sub_entities[sub_id] = entity
            return sub_id

    def get_sub_entity(self, sub_id: str) -> Optional[FusionEntity]:
        """Get a sub-entity by its composite ID."""
        with self._lock:
            return self._sub_entities.get(sub_id)

    # --- General Resolution ---

    def resolve_id(self, entity_id: str) -> Optional[FusionEntity]:
        """Resolve any entity ID to its Fusion object.

        Searches all entity types to find a match.

        Args:
            entity_id: The entity's stable ID

        Returns:
            The Fusion API object, or None if not found
        """
        with self._lock:
            # Check each registry
            if entity_id in self._bodies:
                return self._bodies[entity_id]
            if entity_id in self._sketches:
                return self._sketches[entity_id]
            if entity_id in self._features:
                return self._features[entity_id]
            if entity_id in self._components:
                return self._components[entity_id]
            if entity_id in self._parameters:
                return self._parameters[entity_id]
            if entity_id in self._occurrences:
                return self._occurrences[entity_id]
            if entity_id in self._joints:
                return self._joints[entity_id]
            if entity_id in self._sub_entities:
                return self._sub_entities[entity_id]
            return None

    # --- Lifecycle ---

    def clear(self) -> None:
        """Clear all registered entities.

        Call this when the design changes or add-in restarts.
        """
        with self._lock:
            self._bodies.clear()
            self._sketches.clear()
            self._features.clear()
            self._components.clear()
            self._parameters.clear()
            self._occurrences.clear()
            self._joints.clear()
            self._sub_entities.clear()

            # Reset counters
            for key in self._unnamed_counters:
                self._unnamed_counters[key] = 0

    def refresh_from_design(self, design: FusionEntity) -> None:
        """Refresh registry from current design state.

        Re-registers all entities from the design, maintaining stable IDs
        for named entities while cleaning up stale references.

        Args:
            design: Fusion 360 Design object
        """
        # Clear and re-populate
        self.clear()

        if design is None:
            return

        # Register root component
        root_component = getattr(design, 'rootComponent', None)
        if root_component:
            self._register_component_contents(root_component)

    # --- Private Helpers ---

    def _generate_id(self, entity: FusionEntity, entity_type: str) -> str:
        """Generate stable ID for an entity.

        Uses entity name if available, otherwise generates sequential ID.

        Args:
            entity: Fusion API object
            entity_type: Type string ("body", "sketch", etc.)

        Returns:
            Stable ID string
        """
        # Try to use name property
        name = getattr(entity, 'name', None)
        if name:
            # Use name directly, but ensure uniqueness
            base_id = name
            counter = 0
            entity_id = base_id

            # Get the appropriate registry
            registry = self._get_registry_for_type(entity_type)

            # Ensure uniqueness
            while entity_id in registry:
                counter += 1
                entity_id = f"{base_id}_{counter}"

            return entity_id

        # Generate sequential ID for unnamed entities
        counter = self._unnamed_counters.get(entity_type, 0)
        self._unnamed_counters[entity_type] = counter + 1
        return f"{entity_type}_{counter}"

    def _get_registry_for_type(self, entity_type: str) -> Dict[str, FusionEntity]:
        """Get the appropriate registry dict for entity type."""
        registries = {
            "body": self._bodies,
            "sketch": self._sketches,
            "feature": self._features,
            "component": self._components,
            "parameter": self._parameters,
            "occurrence": self._occurrences,
            "joint": self._joints,
        }
        return registries.get(entity_type, {})

    def _register_component_contents(self, component: FusionEntity) -> None:
        """Register all entities within a component."""
        self.register_component(component)

        # Register bodies
        bodies = getattr(component, 'bRepBodies', None)
        if bodies:
            for body in bodies:
                self.register_body(body)

        # Register sketches
        sketches = getattr(component, 'sketches', None)
        if sketches:
            for sketch in sketches:
                self.register_sketch(sketch)

        # Register features from timeline
        features = getattr(component, 'features', None)
        if features:
            # Iterate through feature collections
            for feature_type in ['extrudeFeatures', 'revolveFeatures', 'sweepFeatures',
                                 'loftFeatures', 'filletFeatures', 'chamferFeatures',
                                 'holeFeatures', 'shellFeatures', 'draftFeatures']:
                feature_collection = getattr(features, feature_type, None)
                if feature_collection:
                    for feature in feature_collection:
                        self.register_feature(feature)

        # Register occurrences and recursively register child components
        occurrences = getattr(component, 'occurrences', None)
        if occurrences:
            for occurrence in occurrences:
                self.register_occurrence(occurrence)
                child_component = getattr(occurrence, 'component', None)
                if child_component:
                    self._register_component_contents(child_component)

        # Register joints
        joints = getattr(component, 'joints', None)
        if joints:
            for joint in joints:
                self.register_joint(joint)


# --- Module-level Singleton ---

_registry: Optional[EntityRegistry] = None
_registry_lock = Lock()


def get_registry() -> EntityRegistry:
    """Get the singleton EntityRegistry instance.

    Returns:
        The global EntityRegistry instance
    """
    global _registry
    with _registry_lock:
        if _registry is None:
            _registry = EntityRegistry()
        return _registry


def reset_registry() -> None:
    """Reset the singleton registry.

    Call this when the design changes or add-in restarts.
    """
    global _registry
    with _registry_lock:
        if _registry:
            _registry.clear()
