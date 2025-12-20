"""Body serializer for Fusion 360 B-Rep entities.

Converts Fusion 360 BRepBody, BRepFace, BRepEdge, and BRepVertex objects
to JSON-serializable dictionaries matching Server Pydantic models.

All dimensions are returned in millimeters (mm), areas in mm², volumes in mm³.
"""

from typing import Dict, Any, List, Optional, TYPE_CHECKING
from .base import BaseSerializer, FusionObject, cm_to_mm


# Additional unit conversion functions
def cm2_to_mm2(value: float) -> float:
    """Convert cm² to mm²."""
    return round(value * 100.0, 6)


def cm3_to_mm3(value: float) -> float:
    """Convert cm³ to mm³."""
    return round(value * 1000.0, 6)

if TYPE_CHECKING:
    from core.entity_registry import EntityRegistry


class BodySerializer(BaseSerializer):
    """Serializer for B-Rep body entities.

    Handles serialization of bodies, faces, edges, and vertices
    from Fusion 360's B-Rep representation.
    """

    # Face type mapping from Fusion SurfaceType enum
    FACE_TYPE_MAP = {
        0: "planar",      # PlaneSurfaceType
        1: "cylindrical", # CylinderSurfaceType
        2: "conical",     # ConeSurfaceType
        3: "spherical",   # SphereSurfaceType
        4: "toroidal",    # TorusSurfaceType
        5: "spline",      # NurbsSurfaceType
    }

    # Edge type mapping from Fusion Curve3DType enum
    EDGE_TYPE_MAP = {
        0: "line",        # Line3D
        1: "arc",         # Arc3D
        2: "circle",      # Circle3D
        3: "ellipse",     # Ellipse3D
        4: "elliptical_arc",  # EllipticalArc3D
        5: "spline",      # NurbsCurve3D
    }

    def serialize_summary(self, body: FusionObject) -> Dict[str, Any]:
        """Serialize body to lightweight summary dict.

        Returns data matching BodySummary Pydantic model.

        Args:
            body: Fusion BRepBody object

        Returns:
            Dict with id, name, is_solid, bounding_box, volume, faces_count
        """
        body_id = self.registry.register_body(body)

        # Get bounding box
        bbox = self.safe_get(body, 'boundingBox')
        bounding_box = self.serialize_bounding_box(bbox)

        # Get physical properties (convert cm³ to mm³)
        volume = cm3_to_mm3(self.safe_get(body, 'volume', 0.0))
        is_solid = self.safe_get(body, 'isSolid', True)

        # Count faces
        faces = self.safe_get(body, 'faces')
        faces_count = faces.count if faces else 0

        return {
            "id": body_id,
            "name": self.safe_get(body, 'name', body_id),
            "is_solid": is_solid,
            "bounding_box": bounding_box,
            "volume": volume,
            "faces_count": faces_count,
        }

    def serialize_full(
        self,
        body: FusionObject,
        include_faces: bool = False,
        include_edges: bool = False,
        include_vertices: bool = False
    ) -> Dict[str, Any]:
        """Serialize body to full detail dict.

        Returns data matching Body Pydantic model.

        Args:
            body: Fusion BRepBody object
            include_faces: Include detailed face information
            include_edges: Include detailed edge information
            include_vertices: Include detailed vertex information

        Returns:
            Dict with full body details including topology when requested
        """
        body_id = self.registry.register_body(body)

        # Get bounding box
        bbox = self.safe_get(body, 'boundingBox')
        bounding_box = self.serialize_bounding_box(bbox)

        # Get physical properties (convert cm³ to mm³, cm² to mm²)
        volume = cm3_to_mm3(self.safe_get(body, 'volume', 0.0))
        area = cm2_to_mm2(self.safe_get(body, 'area', 0.0))
        is_solid = self.safe_get(body, 'isSolid', True)
        is_visible = self.safe_get(body, 'isVisible', True)

        # Get topology counts
        faces_coll = self.safe_get(body, 'faces')
        edges_coll = self.safe_get(body, 'edges')
        vertices_coll = self.safe_get(body, 'vertices')

        faces_count = faces_coll.count if faces_coll else 0
        edges_count = edges_coll.count if edges_coll else 0
        vertices_count = vertices_coll.count if vertices_coll else 0

        # Get center of mass if available
        center_of_mass = None
        physical_props = self.safe_get(body, 'physicalProperties')
        if physical_props:
            com = self.safe_get(physical_props, 'centerOfMass')
            if com:
                center_of_mass = self.serialize_point3d(com)

        # Get parent component ID
        component_id = None
        parent_component = self.safe_get(body, 'parentComponent')
        if parent_component:
            component_id = self.registry.register_component(parent_component)

        # Build result
        result = {
            "id": body_id,
            "name": self.safe_get(body, 'name', body_id),
            "is_solid": is_solid,
            "is_visible": is_visible,
            "bounding_box": bounding_box,
            "volume": volume,
            "area": area,
            "center_of_mass": center_of_mass,
            "faces_count": faces_count,
            "edges_count": edges_count,
            "vertices_count": vertices_count,
            "component_id": component_id,
        }

        # Include detailed topology if requested
        if include_faces and faces_coll:
            result["faces"] = [
                self.serialize_face(face, body_id, idx)
                for idx, face in enumerate(faces_coll)
            ]

        if include_edges and edges_coll:
            result["edges"] = [
                self.serialize_edge(edge, body_id, idx)
                for idx, edge in enumerate(edges_coll)
            ]

        if include_vertices and vertices_coll:
            result["vertices"] = [
                self.serialize_vertex(vertex, body_id, idx)
                for idx, vertex in enumerate(vertices_coll)
            ]

        return result

    def serialize_face(
        self,
        face: FusionObject,
        parent_body_id: str,
        index: int
    ) -> Dict[str, Any]:
        """Serialize a B-Rep face.

        Args:
            face: Fusion BRepFace object
            parent_body_id: ID of parent body
            index: Face index in parent's collection

        Returns:
            Dict matching Face Pydantic model
        """
        face_id = self.registry.register_sub_entity(
            parent_body_id, "face", index, face
        )

        # Get face geometry type
        geometry = self.safe_get(face, 'geometry')
        surface_type = 5  # Default to spline
        if geometry:
            surface_type = self.safe_get(geometry, 'surfaceType', 5)

        face_type = self.FACE_TYPE_MAP.get(surface_type, "spline")

        # Get area (convert cm² to mm²)
        area = cm2_to_mm2(self.safe_get(face, 'area', 0.0))

        # Get normal at centroid (evaluator method)
        normal = {"x": 0.0, "y": 0.0, "z": 1.0}
        centroid = {"x": 0.0, "y": 0.0, "z": 0.0}

        evaluator = self.safe_get(face, 'evaluator')
        if evaluator:
            # Get centroid via parametric center
            try:
                param_result = evaluator.parametricRange()
                if param_result:
                    # Get center of parameter range
                    u_range = param_result.minParameter.x, param_result.maxParameter.x
                    v_range = param_result.minParameter.y, param_result.maxParameter.y
                    u_mid = (u_range[0] + u_range[1]) / 2
                    v_mid = (v_range[0] + v_range[1]) / 2

                    # Evaluate point at center
                    import adsk.core
                    param = adsk.core.Point2D.create(u_mid, v_mid)
                    point_result = evaluator.getPointAtParameter(param)
                    if point_result[0]:
                        centroid = self.serialize_point3d(point_result[1])

                    # Get normal at center
                    normal_result = evaluator.getNormalAtParameter(param)
                    if normal_result[0]:
                        normal = self.serialize_vector3d(normal_result[1])
            except:
                pass

        # Get centroid via alternative method if above failed
        if centroid == {"x": 0.0, "y": 0.0, "z": 0.0}:
            centroid_point = self.safe_get(face, 'centroid')
            if centroid_point:
                centroid = self.serialize_point3d(centroid_point)

        # Determine if planar
        is_planar = face_type == "planar"

        # Get bounding edges
        edge_ids = []
        edges = self.safe_get(face, 'edges')
        if edges:
            for idx, edge in enumerate(edges):
                # Find this edge's index in parent body
                edge_ids.append(f"{parent_body_id}_edge_{idx}")

        result = {
            "id": face_id,
            "face_type": face_type,
            "area": area,
            "normal": normal,
            "centroid": centroid,
            "edge_ids": edge_ids,
            "is_planar": is_planar,
        }

        # Add type-specific properties
        if face_type == "cylindrical" and geometry:
            axis = self.safe_get(geometry, 'axis')
            if axis:
                result["axis"] = self.serialize_vector3d(axis)
            result["radius"] = cm_to_mm(self.safe_get(geometry, 'radius', 0.0))

        if face_type == "conical" and geometry:
            axis = self.safe_get(geometry, 'axis')
            if axis:
                result["axis"] = self.serialize_vector3d(axis)

        return result

    def serialize_edge(
        self,
        edge: FusionObject,
        parent_body_id: str,
        index: int
    ) -> Dict[str, Any]:
        """Serialize a B-Rep edge.

        Args:
            edge: Fusion BRepEdge object
            parent_body_id: ID of parent body
            index: Edge index in parent's collection

        Returns:
            Dict matching Edge Pydantic model
        """
        edge_id = self.registry.register_sub_entity(
            parent_body_id, "edge", index, edge
        )

        # Get edge geometry type
        geometry = self.safe_get(edge, 'geometry')
        curve_type = 5  # Default to spline
        if geometry:
            curve_type = self.safe_get(geometry, 'curveType', 5)

        edge_type = self.EDGE_TYPE_MAP.get(curve_type, "spline")

        # Get length (convert cm to mm)
        length = cm_to_mm(self.safe_get(edge, 'length', 0.0))

        # Get start/end vertices
        start_vertex = self.safe_get(edge, 'startVertex')
        end_vertex = self.safe_get(edge, 'endVertex')

        # Determine vertex IDs based on their index in parent body
        start_vertex_id = ""
        end_vertex_id = ""

        try:
            body = self.safe_get(edge, 'body')
            if body:
                vertices = self.safe_get(body, 'vertices')
                if vertices and start_vertex:
                    for idx, v in enumerate(vertices):
                        if v == start_vertex:
                            start_vertex_id = f"{parent_body_id}_vertex_{idx}"
                            break
                if vertices and end_vertex:
                    for idx, v in enumerate(vertices):
                        if v == end_vertex:
                            end_vertex_id = f"{parent_body_id}_vertex_{idx}"
                            break
        except:
            pass

        # Check if closed (loop edge)
        is_closed = start_vertex == end_vertex if (start_vertex and end_vertex) else False

        result = {
            "id": edge_id,
            "edge_type": edge_type,
            "start_vertex_id": start_vertex_id,
            "end_vertex_id": end_vertex_id,
            "length": length,
            "is_closed": is_closed,
        }

        # Add type-specific properties for arcs/circles
        if edge_type in ("arc", "circle") and geometry:
            center = self.safe_get(geometry, 'center')
            if center:
                result["center"] = self.serialize_point3d(center)
            result["radius"] = cm_to_mm(self.safe_get(geometry, 'radius', 0.0))

        return result

    def serialize_vertex(
        self,
        vertex: FusionObject,
        parent_body_id: str,
        index: int
    ) -> Dict[str, Any]:
        """Serialize a B-Rep vertex.

        Args:
            vertex: Fusion BRepVertex object
            parent_body_id: ID of parent body
            index: Vertex index in parent's collection

        Returns:
            Dict matching Vertex Pydantic model
        """
        vertex_id = self.registry.register_sub_entity(
            parent_body_id, "vertex", index, vertex
        )

        # Get geometry (point)
        geometry = self.safe_get(vertex, 'geometry')
        position = self.serialize_point3d(geometry)

        return {
            "id": vertex_id,
            "position": position,
        }
