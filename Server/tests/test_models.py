"""Unit tests for Pydantic models."""

import pytest
import math
from fusion360_mcp_server.models import (
    # Geometry
    Point3D, Vector3D, BoundingBox, Matrix3D, PlaneSpec,
    # Body
    Body, Face, Edge, Vertex, BodySummary, FaceType, EdgeType,
    # Sketch
    Sketch, SketchCurve, Profile, SketchSummary, SketchCurveType,
    # Feature
    Feature, Parameter, Timeline, TimelineEntry, FeatureType,
    # Design State
    DesignState, DesignInfo, Component,
)


class TestPoint3D:
    """Tests for Point3D model."""

    def test_creation_default(self):
        """Test default Point3D creation."""
        p = Point3D()
        assert p.x == 0.0
        assert p.y == 0.0
        assert p.z == 0.0

    def test_creation_with_values(self):
        """Test Point3D creation with values."""
        p = Point3D(x=1.0, y=2.0, z=3.0)
        assert p.x == 1.0
        assert p.y == 2.0
        assert p.z == 3.0

    def test_to_tuple(self):
        """Test Point3D to_tuple method."""
        p = Point3D(x=1.0, y=2.0, z=3.0)
        assert p.to_tuple() == (1.0, 2.0, 3.0)

    def test_distance_to_same_point(self):
        """Test distance to same point is 0."""
        p = Point3D(x=5.0, y=5.0, z=5.0)
        assert p.distance_to(p) == 0.0

    def test_distance_to_other_point(self):
        """Test distance calculation (3-4-5 triangle)."""
        p1 = Point3D(x=0, y=0, z=0)
        p2 = Point3D(x=3, y=4, z=0)
        assert p1.distance_to(p2) == 5.0

    def test_distance_3d(self):
        """Test 3D distance calculation."""
        p1 = Point3D(x=0, y=0, z=0)
        p2 = Point3D(x=1, y=2, z=2)
        assert p1.distance_to(p2) == 3.0

    def test_serialization(self):
        """Test Point3D serialization."""
        p = Point3D(x=1.0, y=2.0, z=3.0)
        data = p.model_dump()
        assert data == {"x": 1.0, "y": 2.0, "z": 3.0}

    def test_deserialization(self):
        """Test Point3D deserialization."""
        data = {"x": 1.0, "y": 2.0, "z": 3.0}
        p = Point3D.model_validate(data)
        assert p.x == 1.0
        assert p.y == 2.0
        assert p.z == 3.0


class TestVector3D:
    """Tests for Vector3D model."""

    def test_magnitude_unit_vector(self):
        """Test magnitude of unit vector."""
        v = Vector3D(x=1, y=0, z=0)
        assert v.magnitude == 1.0

    def test_magnitude_3_4_5(self):
        """Test magnitude calculation."""
        v = Vector3D(x=3, y=4, z=0)
        assert v.magnitude == 5.0

    def test_normalize_unit_vector(self):
        """Test normalizing already unit vector."""
        v = Vector3D(x=1, y=0, z=0)
        n = v.normalize()
        assert n.x == 1.0
        assert n.y == 0.0
        assert n.z == 0.0

    def test_normalize_arbitrary_vector(self):
        """Test normalizing arbitrary vector."""
        v = Vector3D(x=10, y=0, z=0)
        n = v.normalize()
        assert n.x == 1.0
        assert n.magnitude == pytest.approx(1.0)

    def test_normalize_zero_vector(self):
        """Test normalizing zero vector returns zero vector."""
        v = Vector3D(x=0, y=0, z=0)
        n = v.normalize()
        assert n.x == 0
        assert n.y == 0
        assert n.z == 0

    def test_dot_product_perpendicular(self):
        """Test dot product of perpendicular vectors."""
        v1 = Vector3D(x=1, y=0, z=0)
        v2 = Vector3D(x=0, y=1, z=0)
        assert v1.dot(v2) == 0.0

    def test_dot_product_parallel(self):
        """Test dot product of parallel vectors."""
        v1 = Vector3D(x=1, y=0, z=0)
        v2 = Vector3D(x=2, y=0, z=0)
        assert v1.dot(v2) == 2.0

    def test_cross_product(self):
        """Test cross product of X and Y gives Z."""
        v1 = Vector3D(x=1, y=0, z=0)
        v2 = Vector3D(x=0, y=1, z=0)
        cross = v1.cross(v2)
        assert cross.x == 0
        assert cross.y == 0
        assert cross.z == 1

    def test_scalar_multiplication(self):
        """Test scalar multiplication."""
        v = Vector3D(x=1, y=2, z=3)
        result = v * 2
        assert result.x == 2
        assert result.y == 4
        assert result.z == 6


class TestBoundingBox:
    """Tests for BoundingBox model."""

    def test_dimensions(self):
        """Test bounding box dimensions calculation."""
        bb = BoundingBox(
            min_point=Point3D(x=0, y=0, z=0),
            max_point=Point3D(x=100, y=50, z=10)
        )
        assert bb.dimensions.x == 100
        assert bb.dimensions.y == 50
        assert bb.dimensions.z == 10

    def test_center(self):
        """Test bounding box center calculation."""
        bb = BoundingBox(
            min_point=Point3D(x=0, y=0, z=0),
            max_point=Point3D(x=100, y=50, z=10)
        )
        assert bb.center.x == 50
        assert bb.center.y == 25
        assert bb.center.z == 5

    def test_volume(self):
        """Test bounding box volume calculation."""
        bb = BoundingBox(
            min_point=Point3D(x=0, y=0, z=0),
            max_point=Point3D(x=100, y=50, z=10)
        )
        assert bb.volume == 50000.0

    def test_contains_inside_point(self):
        """Test point inside bounding box."""
        bb = BoundingBox(
            min_point=Point3D(x=0, y=0, z=0),
            max_point=Point3D(x=10, y=10, z=10)
        )
        assert bb.contains(Point3D(x=5, y=5, z=5)) is True

    def test_contains_outside_point(self):
        """Test point outside bounding box."""
        bb = BoundingBox(
            min_point=Point3D(x=0, y=0, z=0),
            max_point=Point3D(x=10, y=10, z=10)
        )
        assert bb.contains(Point3D(x=15, y=5, z=5)) is False

    def test_contains_boundary_point(self):
        """Test point on boundary."""
        bb = BoundingBox(
            min_point=Point3D(x=0, y=0, z=0),
            max_point=Point3D(x=10, y=10, z=10)
        )
        assert bb.contains(Point3D(x=10, y=10, z=10)) is True

    def test_intersects_overlapping(self):
        """Test overlapping bounding boxes."""
        bb1 = BoundingBox(
            min_point=Point3D(x=0, y=0, z=0),
            max_point=Point3D(x=10, y=10, z=10)
        )
        bb2 = BoundingBox(
            min_point=Point3D(x=5, y=5, z=5),
            max_point=Point3D(x=15, y=15, z=15)
        )
        assert bb1.intersects(bb2) is True

    def test_intersects_separate(self):
        """Test non-overlapping bounding boxes."""
        bb1 = BoundingBox(
            min_point=Point3D(x=0, y=0, z=0),
            max_point=Point3D(x=10, y=10, z=10)
        )
        bb2 = BoundingBox(
            min_point=Point3D(x=20, y=20, z=20),
            max_point=Point3D(x=30, y=30, z=30)
        )
        assert bb1.intersects(bb2) is False

    def test_serialization_roundtrip(self):
        """Test bounding box serialization and deserialization."""
        bb = BoundingBox(
            min_point=Point3D(x=0, y=0, z=0),
            max_point=Point3D(x=100, y=50, z=10)
        )
        data = bb.model_dump()
        bb2 = BoundingBox.model_validate(data)
        assert bb2.min_point.x == 0
        assert bb2.max_point.x == 100


class TestMatrix3D:
    """Tests for Matrix3D model."""

    def test_identity(self):
        """Test identity matrix."""
        m = Matrix3D.identity()
        assert m.elements[0][0] == 1
        assert m.elements[1][1] == 1
        assert m.elements[2][2] == 1
        assert m.elements[3][3] == 1
        assert m.elements[0][1] == 0

    def test_translation(self):
        """Test translation matrix."""
        m = Matrix3D.translation(10, 20, 30)
        p = Point3D(x=0, y=0, z=0)
        result = m.transform_point(p)
        assert result.x == 10
        assert result.y == 20
        assert result.z == 30

    def test_validate_matrix_size_invalid(self):
        """Test that invalid matrix size raises error."""
        with pytest.raises(ValueError):
            Matrix3D(elements=[[1, 0], [0, 1]])  # 2x2 instead of 4x4


class TestPlaneSpec:
    """Tests for PlaneSpec model."""

    def test_default_xy_plane(self):
        """Test default XY plane."""
        p = PlaneSpec()
        assert p.plane_type == "XY"
        assert p.offset == 0.0

    def test_plane_with_offset(self):
        """Test plane with offset."""
        p = PlaneSpec(plane_type="XY", offset=10.0)
        assert p.offset == 10.0

    def test_get_normal_xy(self):
        """Test XY plane normal."""
        p = PlaneSpec(plane_type="XY")
        n = p.get_normal()
        assert n.z == 1

    def test_get_normal_yz(self):
        """Test YZ plane normal."""
        p = PlaneSpec(plane_type="YZ")
        n = p.get_normal()
        assert n.x == 1

    def test_get_normal_xz(self):
        """Test XZ plane normal."""
        p = PlaneSpec(plane_type="XZ")
        n = p.get_normal()
        assert n.y == 1

    def test_invalid_plane_type(self):
        """Test invalid plane type raises error."""
        with pytest.raises(ValueError):
            PlaneSpec(plane_type="INVALID")

    def test_face_reference_plane(self):
        """Test face reference plane type is valid."""
        p = PlaneSpec(plane_type="face_001")
        assert p.plane_type == "face_001"


class TestBody:
    """Tests for Body model."""

    def test_body_creation(self):
        """Test body creation."""
        body = Body(
            id="body_001",
            name="test_body",
            is_solid=True,
            bounding_box=BoundingBox(
                min_point=Point3D(x=0, y=0, z=0),
                max_point=Point3D(x=100, y=50, z=10)
            ),
            volume=50000.0,
            area=13000.0,
            faces_count=6,
            edges_count=12,
            vertices_count=8
        )
        assert body.id == "body_001"
        assert body.name == "test_body"
        assert body.volume == 50000.0

    def test_body_serialization_roundtrip(self):
        """Test body serialization and deserialization."""
        body = Body(
            id="body_001",
            name="test_body",
            is_solid=True,
            bounding_box=BoundingBox(
                min_point=Point3D(x=0, y=0, z=0),
                max_point=Point3D(x=100, y=50, z=10)
            ),
            volume=50000.0,
        )
        data = body.model_dump()
        body2 = Body.model_validate(data)
        assert body2.id == body.id
        assert body2.name == body.name


class TestSketch:
    """Tests for Sketch model."""

    def test_sketch_creation(self):
        """Test sketch creation."""
        sketch = Sketch(
            id="sketch_001",
            name="Sketch1",
            plane=PlaneSpec(plane_type="XY"),
            is_fully_constrained=True,
            curves_count=4,
            profiles_count=1
        )
        assert sketch.id == "sketch_001"
        assert sketch.name == "Sketch1"
        assert sketch.is_fully_constrained is True

    def test_sketch_curve_line(self):
        """Test sketch curve line creation."""
        curve = SketchCurve(
            id="curve_001",
            curve_type=SketchCurveType.LINE,
            start_point=Point3D(x=0, y=0, z=0),
            end_point=Point3D(x=100, y=0, z=0),
            length=100.0
        )
        assert curve.curve_type == SketchCurveType.LINE
        assert curve.length == 100.0


class TestFeature:
    """Tests for Feature model."""

    def test_parameter_creation(self):
        """Test parameter creation."""
        param = Parameter(
            name="width",
            expression="100 mm",
            value=100.0,
            unit="mm",
            is_user_parameter=True
        )
        assert param.name == "width"
        assert param.value == 100.0
        assert param.is_user_parameter is True

    def test_timeline_entry(self):
        """Test timeline entry creation."""
        entry = TimelineEntry(
            index=0,
            feature_id="Sketch1",
            name="Sketch1",
            feature_type=FeatureType.SKETCH,
            is_suppressed=False
        )
        assert entry.index == 0
        assert entry.feature_type == FeatureType.SKETCH

    def test_feature_creation(self):
        """Test feature creation."""
        feature = Feature(
            id="Extrude1",
            name="Extrude1",
            feature_type=FeatureType.EXTRUDE,
            timeline_index=1,
            is_suppressed=False,
            is_healthy=True
        )
        assert feature.id == "Extrude1"
        assert feature.feature_type == FeatureType.EXTRUDE


class TestDesignState:
    """Tests for DesignState model."""

    def test_design_info_creation(self):
        """Test design info creation."""
        info = DesignInfo(
            name="TestDesign",
            units="mm",
            bodies_count=3,
            sketches_count=2
        )
        assert info.name == "TestDesign"
        assert info.bodies_count == 3

    def test_component_creation(self):
        """Test component creation."""
        comp = Component(
            id="root",
            name="RootComponent",
            is_root=True,
            is_active=True,
            bodies_count=3
        )
        assert comp.is_root is True
        assert comp.bodies_count == 3

    def test_design_state_aggregation(self):
        """Test full design state."""
        state = DesignState(
            design=DesignInfo(
                name="TestDesign",
                units="mm",
                bodies_count=1
            ),
            root_component=Component(
                id="root",
                name="Root",
                is_root=True,
                bodies_count=1
            ),
            bodies=[
                BodySummary(
                    id="body_001",
                    name="plate",
                    is_solid=True,
                    bounding_box=BoundingBox(
                        min_point=Point3D(x=0, y=0, z=0),
                        max_point=Point3D(x=100, y=50, z=10)
                    ),
                    volume=50000.0
                )
            ]
        )
        assert state.design.name == "TestDesign"
        assert len(state.bodies) == 1
        assert state.bodies[0].name == "plate"

    def test_design_state_serialization_roundtrip(self):
        """Test design state serialization."""
        state = DesignState(
            design=DesignInfo(name="Test", units="mm"),
            root_component=Component(id="root", name="Root", is_root=True)
        )
        data = state.model_dump()
        state2 = DesignState.model_validate(data)
        assert state2.design.name == "Test"
