"""Sketch serializer for Fusion 360 sketch entities.

Converts Fusion 360 Sketch, SketchCurve, SketchConstraint, and Profile objects
to JSON-serializable dictionaries matching Server Pydantic models.

All dimensions are returned in millimeters (mm).
"""

from typing import Dict, Any, List, Optional, TYPE_CHECKING
from .base import BaseSerializer, FusionObject, cm_to_mm


# Length unit detection
LENGTH_UNITS = {'mm', 'cm', 'm', 'in', 'ft'}


def is_length_unit(unit: str) -> bool:
    """Check if unit is a length unit (needs conversion)."""
    if not unit:
        return False
    return unit.lower() in LENGTH_UNITS

if TYPE_CHECKING:
    from core.entity_registry import EntityRegistry


class SketchSerializer(BaseSerializer):
    """Serializer for sketch entities.

    Handles serialization of sketches, curves, constraints, and profiles
    from Fusion 360's sketch system.
    """

    # Curve type mapping
    CURVE_TYPE_MAP = {
        "SketchLine": "line",
        "SketchArc": "arc",
        "SketchCircle": "circle",
        "SketchEllipse": "ellipse",
        "SketchFittedSpline": "spline",
        "SketchFixedSpline": "spline",
        "SketchConicCurve": "conic",
        "SketchPoint": "point",
    }

    # Constraint type mapping
    CONSTRAINT_TYPE_MAP = {
        "coincidentConstraint": "coincident",
        "collinearConstraint": "collinear",
        "concentricConstraint": "concentric",
        "equalConstraint": "equal",
        "fixConstraint": "fixed",
        "horizontalConstraint": "horizontal",
        "midPointConstraint": "midpoint",
        "parallelConstraint": "parallel",
        "perpendicularConstraint": "perpendicular",
        "smoothConstraint": "smooth",
        "symmetryConstraint": "symmetry",
        "tangentConstraint": "tangent",
        "verticalConstraint": "vertical",
    }

    def serialize_summary(self, sketch: FusionObject) -> Dict[str, Any]:
        """Serialize sketch to lightweight summary dict.

        Returns data matching SketchSummary Pydantic model.

        Args:
            sketch: Fusion Sketch object

        Returns:
            Dict with id, name, plane, is_fully_constrained, curves_count, profiles_count
        """
        sketch_id = self.registry.register_sketch(sketch)

        # Get reference plane info
        reference_plane = self.safe_get(sketch, 'referencePlane')
        plane_info = self._serialize_reference_plane(reference_plane)

        # Check constraint status
        is_fully_constrained = self.safe_get(sketch, 'isFullyConstrained', False)

        # Count curves
        curves = self.safe_get(sketch, 'sketchCurves')
        curves_count = 0
        if curves:
            # Count all curve types
            for curve_type in ['sketchLines', 'sketchArcs', 'sketchCircles',
                              'sketchEllipses', 'sketchFittedSplines']:
                coll = self.safe_get(curves, curve_type)
                if coll:
                    curves_count += coll.count

        # Count profiles
        profiles = self.safe_get(sketch, 'profiles')
        profiles_count = profiles.count if profiles else 0

        return {
            "id": sketch_id,
            "name": self.safe_get(sketch, 'name', sketch_id),
            "plane": plane_info,
            "is_fully_constrained": is_fully_constrained,
            "curves_count": curves_count,
            "profiles_count": profiles_count,
        }

    def serialize_full(
        self,
        sketch: FusionObject,
        include_curves: bool = True,
        include_constraints: bool = True,
        include_dimensions: bool = True,
        include_profiles: bool = False
    ) -> Dict[str, Any]:
        """Serialize sketch to full detail dict.

        Returns data matching Sketch Pydantic model.

        Args:
            sketch: Fusion Sketch object
            include_curves: Include detailed curve information
            include_constraints: Include constraint information
            include_dimensions: Include dimension information
            include_profiles: Include profile information

        Returns:
            Dict with full sketch details
        """
        sketch_id = self.registry.register_sketch(sketch)

        # Get reference plane info
        reference_plane = self.safe_get(sketch, 'referencePlane')
        plane_info = self._serialize_reference_plane(reference_plane)

        # Check constraint status
        is_fully_constrained = self.safe_get(sketch, 'isFullyConstrained', False)
        is_visible = self.safe_get(sketch, 'isVisible', True)

        # Get transform
        transform = self.safe_get(sketch, 'transform')
        transform_data = self.serialize_matrix3d(transform) if transform else None

        # Get parent component
        component_id = None
        parent_component = self.safe_get(sketch, 'parentComponent')
        if parent_component:
            component_id = self.registry.register_component(parent_component)

        result = {
            "id": sketch_id,
            "name": self.safe_get(sketch, 'name', sketch_id),
            "plane": plane_info,
            "is_fully_constrained": is_fully_constrained,
            "is_visible": is_visible,
            "transform": transform_data,
            "component_id": component_id,
        }

        # Include curves
        if include_curves:
            result["curves"] = self._serialize_all_curves(sketch, sketch_id)

        # Include constraints
        if include_constraints:
            result["constraints"] = self._serialize_all_constraints(sketch, sketch_id)

        # Include dimensions
        if include_dimensions:
            result["dimensions"] = self._serialize_all_dimensions(sketch, sketch_id)

        # Include profiles
        if include_profiles:
            profiles = self.safe_get(sketch, 'profiles')
            if profiles:
                result["profiles"] = [
                    self._serialize_profile(profile, sketch_id, idx)
                    for idx, profile in enumerate(profiles)
                ]

        return result

    def _serialize_reference_plane(self, plane: FusionObject) -> Dict[str, Any]:
        """Serialize reference plane to dict."""
        if plane is None:
            return {"type": "unknown", "origin": {"x": 0, "y": 0, "z": 0}}

        # Get plane type name
        plane_type = type(plane).__name__

        # Try to get geometry
        result = {"type": plane_type}

        # For construction planes
        if hasattr(plane, 'geometry'):
            geometry = plane.geometry
            if geometry:
                origin = self.safe_get(geometry, 'origin')
                normal = self.safe_get(geometry, 'normal')
                if origin:
                    result["origin"] = self.serialize_point3d(origin)
                if normal:
                    result["normal"] = self.serialize_vector3d(normal)

        return result

    def _serialize_all_curves(
        self,
        sketch: FusionObject,
        sketch_id: str
    ) -> List[Dict[str, Any]]:
        """Serialize all curves in a sketch."""
        curves = []
        sketch_curves = self.safe_get(sketch, 'sketchCurves')

        if not sketch_curves:
            return curves

        curve_index = 0

        # Lines
        lines = self.safe_get(sketch_curves, 'sketchLines')
        if lines:
            for line in lines:
                curves.append(self._serialize_curve(line, sketch_id, curve_index, "line"))
                curve_index += 1

        # Arcs
        arcs = self.safe_get(sketch_curves, 'sketchArcs')
        if arcs:
            for arc in arcs:
                curves.append(self._serialize_curve(arc, sketch_id, curve_index, "arc"))
                curve_index += 1

        # Circles
        circles = self.safe_get(sketch_curves, 'sketchCircles')
        if circles:
            for circle in circles:
                curves.append(self._serialize_curve(circle, sketch_id, curve_index, "circle"))
                curve_index += 1

        # Ellipses
        ellipses = self.safe_get(sketch_curves, 'sketchEllipses')
        if ellipses:
            for ellipse in ellipses:
                curves.append(self._serialize_curve(ellipse, sketch_id, curve_index, "ellipse"))
                curve_index += 1

        # Splines
        splines = self.safe_get(sketch_curves, 'sketchFittedSplines')
        if splines:
            for spline in splines:
                curves.append(self._serialize_curve(spline, sketch_id, curve_index, "spline"))
                curve_index += 1

        return curves

    def _serialize_curve(
        self,
        curve: FusionObject,
        sketch_id: str,
        index: int,
        curve_type: str
    ) -> Dict[str, Any]:
        """Serialize a single sketch curve."""
        curve_id = self.registry.register_sub_entity(sketch_id, "curve", index, curve)

        result = {
            "id": curve_id,
            "curve_type": curve_type,
            "is_construction": self.safe_get(curve, 'isConstruction', False),
            "is_fixed": self.safe_get(curve, 'isFixed', False),
        }

        # Type-specific properties
        if curve_type == "line":
            start_point = self.safe_get(curve, 'startSketchPoint')
            end_point = self.safe_get(curve, 'endSketchPoint')
            if start_point:
                result["start_point"] = self.serialize_point3d(
                    self.safe_get(start_point, 'geometry')
                )
            if end_point:
                result["end_point"] = self.serialize_point3d(
                    self.safe_get(end_point, 'geometry')
                )
            result["length"] = cm_to_mm(self.safe_get(curve, 'length', 0.0))

        elif curve_type == "circle":
            center_point = self.safe_get(curve, 'centerSketchPoint')
            if center_point:
                result["center"] = self.serialize_point3d(
                    self.safe_get(center_point, 'geometry')
                )
            result["radius"] = cm_to_mm(self.safe_get(curve, 'radius', 0.0))

        elif curve_type == "arc":
            center_point = self.safe_get(curve, 'centerSketchPoint')
            if center_point:
                result["center"] = self.serialize_point3d(
                    self.safe_get(center_point, 'geometry')
                )
            result["radius"] = cm_to_mm(self.safe_get(curve, 'radius', 0.0))
            start_point = self.safe_get(curve, 'startSketchPoint')
            end_point = self.safe_get(curve, 'endSketchPoint')
            if start_point:
                result["start_point"] = self.serialize_point3d(
                    self.safe_get(start_point, 'geometry')
                )
            if end_point:
                result["end_point"] = self.serialize_point3d(
                    self.safe_get(end_point, 'geometry')
                )

        elif curve_type == "ellipse":
            center_point = self.safe_get(curve, 'centerSketchPoint')
            if center_point:
                result["center"] = self.serialize_point3d(
                    self.safe_get(center_point, 'geometry')
                )
            result["major_axis_radius"] = cm_to_mm(self.safe_get(curve, 'majorAxisRadius', 0.0))
            result["minor_axis_radius"] = cm_to_mm(self.safe_get(curve, 'minorAxisRadius', 0.0))

        return result

    def _serialize_all_constraints(
        self,
        sketch: FusionObject,
        sketch_id: str
    ) -> List[Dict[str, Any]]:
        """Serialize all constraints in a sketch."""
        constraints = []
        sketch_constraints = self.safe_get(sketch, 'geometricConstraints')

        if not sketch_constraints:
            return constraints

        constraint_index = 0

        # Iterate through constraint collections
        for constraint_attr in dir(sketch_constraints):
            if constraint_attr.endswith('Constraints'):
                coll = self.safe_get(sketch_constraints, constraint_attr)
                if coll and hasattr(coll, '__iter__'):
                    constraint_type = self.CONSTRAINT_TYPE_MAP.get(
                        constraint_attr.replace('s', '', 1),  # Remove plural 's'
                        constraint_attr
                    )
                    for constraint in coll:
                        constraints.append(
                            self._serialize_constraint(
                                constraint, sketch_id, constraint_index, constraint_type
                            )
                        )
                        constraint_index += 1

        return constraints

    def _serialize_constraint(
        self,
        constraint: FusionObject,
        sketch_id: str,
        index: int,
        constraint_type: str
    ) -> Dict[str, Any]:
        """Serialize a single sketch constraint."""
        constraint_id = f"{sketch_id}_constraint_{index}"

        return {
            "id": constraint_id,
            "constraint_type": constraint_type,
            "is_deletable": self.safe_get(constraint, 'isDeletable', True),
        }

    def _serialize_all_dimensions(
        self,
        sketch: FusionObject,
        sketch_id: str
    ) -> List[Dict[str, Any]]:
        """Serialize all dimensions in a sketch."""
        dimensions = []
        sketch_dimensions = self.safe_get(sketch, 'sketchDimensions')

        if not sketch_dimensions:
            return dimensions

        for idx, dim in enumerate(sketch_dimensions):
            dimensions.append(self._serialize_dimension(dim, sketch_id, idx))

        return dimensions

    def _serialize_dimension(
        self,
        dimension: FusionObject,
        sketch_id: str,
        index: int
    ) -> Dict[str, Any]:
        """Serialize a single sketch dimension."""
        dimension_id = f"{sketch_id}_dimension_{index}"

        # Get parameter value
        parameter = self.safe_get(dimension, 'parameter')
        value = 0.0
        expression = ""
        name = ""
        unit = ""

        if parameter:
            value = self.safe_get(parameter, 'value', 0.0)
            expression = self.safe_get(parameter, 'expression', str(value))
            name = self.safe_get(parameter, 'name', dimension_id)
            unit = self.safe_get(parameter, 'unit', '')

            # Convert value from cm to mm for length units (not angles)
            if is_length_unit(unit):
                value = cm_to_mm(value)

        # Determine dimension type from class name
        dim_type = type(dimension).__name__.replace('Sketch', '').replace('Dimension', '').lower()

        return {
            "id": dimension_id,
            "dimension_type": dim_type,
            "name": name,
            "value": value,
            "expression": expression,
            "is_driven": self.safe_get(dimension, 'isDriven', False),
        }

    def _serialize_profile(
        self,
        profile: FusionObject,
        sketch_id: str,
        index: int
    ) -> Dict[str, Any]:
        """Serialize a sketch profile."""
        profile_id = f"{sketch_id}_profile_{index}"

        # Get profile loops
        loops = []
        profile_loops = self.safe_get(profile, 'profileLoops')
        if profile_loops:
            for loop_idx, loop in enumerate(profile_loops):
                loops.append({
                    "is_outer": self.safe_get(loop, 'isOuter', False),
                    "curve_count": self.safe_get(loop, 'profileCurves', []),
                })

        # Get area if available
        area_props = self.safe_get(profile, 'areaProperties')
        area = 0.0
        centroid = None
        if area_props:
            area = self.safe_get(area_props, 'area', 0.0)
            centroid_point = self.safe_get(area_props, 'centroid')
            if centroid_point:
                centroid = self.serialize_point3d(centroid_point)

        return {
            "id": profile_id,
            "loops_count": len(loops),
            "area": area,
            "centroid": centroid,
        }
