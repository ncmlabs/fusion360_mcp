"""Validation tools for Fusion 360 MCP Server.

These tools enable AI to verify designs through measurements,
interference detection, and property queries.
"""

from typing import Optional, List
from mcp.server.fastmcp import FastMCP

from ..services.fusion_client import FusionClient
from ..logging import get_logger

logger = get_logger(__name__)


def register_validation_tools(mcp: FastMCP) -> None:
    """Register all validation tools with the MCP server.

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool()
    async def measure_distance(entity1_id: str, entity2_id: str) -> dict:
        """Measure the minimum distance between two entities.

        Calculates the shortest distance between any two geometric entities
        in the design. Supports body-to-body, face-to-face, edge-to-edge,
        and other entity combinations.

        **Use cases:**
        - Verify spacing between components (e.g., "Are these holes 70mm apart?")
        - Check clearances (e.g., "Is there at least 5mm gap?")
        - Measure feature positions (e.g., "How far is the hole from the edge?")

        Args:
            entity1_id: ID of the first entity (body, face, edge, or vertex).
                       Use get_bodies() or get_body_by_id(include_faces=True)
                       to find entity IDs.
            entity2_id: ID of the second entity.

        Returns:
            Dict containing:
            - distance: Minimum distance in mm (accurate to 0.001mm)
            - point1: Closest point on entity1 {x, y, z} in mm
            - point2: Closest point on entity2 {x, y, z} in mm

        Example response:
            {
                "success": true,
                "distance": 70.0,
                "point1": {"x": 15.0, "y": 15.0, "z": 5.0},
                "point2": {"x": 85.0, "y": 15.0, "z": 5.0},
                "entity1_id": "hole_1",
                "entity2_id": "hole_2"
            }
        """
        logger.info(
            "measure_distance called",
            entity1_id=entity1_id,
            entity2_id=entity2_id,
        )
        async with FusionClient() as client:
            return await client.measure_distance(entity1_id, entity2_id)

    @mcp.tool()
    async def measure_angle(entity1_id: str, entity2_id: str) -> dict:
        """Measure the angle between two planar faces or linear edges.

        Calculates the angle between two geometric entities in degrees.
        Works with planar faces and linear edges.

        **Use cases:**
        - Verify face angles (e.g., "Are these faces perpendicular?")
        - Check chamfer angles (e.g., "Is this a 45-degree chamfer?")
        - Measure edge angles (e.g., "What angle do these edges form?")

        Args:
            entity1_id: ID of the first entity (planar face or linear edge).
                       Use get_body_by_id(include_faces=True) to find face IDs.
            entity2_id: ID of the second entity (planar face or linear edge).

        Returns:
            Dict containing:
            - angle: Angle between entities in degrees (0-180)

        Example response:
            {
                "success": true,
                "angle": 90.0,
                "entity1_id": "Body1_face_0",
                "entity2_id": "Body1_face_2"
            }

        Note: Parallel faces return 0 degrees, perpendicular faces return 90 degrees.
        """
        logger.info(
            "measure_angle called",
            entity1_id=entity1_id,
            entity2_id=entity2_id,
        )
        async with FusionClient() as client:
            return await client.measure_angle(entity1_id, entity2_id)

    @mcp.tool()
    async def check_interference(body_ids: Optional[List[str]] = None) -> dict:
        """Detect collisions and overlapping volumes between bodies.

        Analyzes bodies for interference (overlapping geometry).
        This is critical for validating assemblies and ensuring
        parts don't collide.

        **Use cases:**
        - Validate assembly (e.g., "Do any parts collide?")
        - Check fit tolerance (e.g., "Is there clearance between components?")
        - Find design errors (e.g., "Why won't these parts fit together?")

        Args:
            body_ids: Optional list of body IDs to check.
                     If not provided, checks ALL bodies in the design.
                     Use get_bodies() to find available body IDs.

        Returns:
            Dict containing:
            - has_interference: True if any collisions were detected
            - interferences: List of collision details, each with:
                - body1: ID of first colliding body
                - body2: ID of second colliding body
                - volume: Overlap volume in mm³
            - bodies_checked: Number of bodies analyzed

        Example response (no interference):
            {
                "success": true,
                "has_interference": false,
                "interferences": [],
                "bodies_checked": 3
            }

        Example response (interference found):
            {
                "success": true,
                "has_interference": true,
                "interferences": [
                    {
                        "body1": "Body1",
                        "body2": "Body2",
                        "volume": 125.5
                    }
                ],
                "bodies_checked": 2
            }

        Performance note: Checking many bodies can be slow. Filter with
        body_ids when checking specific pairs.
        """
        logger.info("check_interference called", body_ids=body_ids)
        async with FusionClient() as client:
            return await client.check_interference(body_ids)

    @mcp.tool()
    async def get_body_properties(body_id: str) -> dict:
        """Get detailed physical properties of a body.

        Returns comprehensive measurements and physical characteristics
        of a solid body including volume, surface area, mass properties,
        and bounding box dimensions.

        **Use cases:**
        - Verify dimensions (e.g., "Is this box exactly 100x50x10mm?")
        - Check volume (e.g., "What's the volume of this part?")
        - Find center of mass (e.g., "Where is the balance point?")
        - Count topology (e.g., "How many faces does this have?")

        Args:
            body_id: ID of the body to analyze.
                    Use get_bodies() to find available body IDs.

        Returns:
            Dict with properties containing:
            - volume: Body volume in mm³
            - area: Total surface area in mm²
            - center_of_mass: Center of mass point {x, y, z} in mm
            - bounding_box: {min: [x,y,z], max: [x,y,z]} in mm
            - dimensions: {width, depth, height} in mm
            - faces_count: Number of B-Rep faces
            - edges_count: Number of B-Rep edges
            - vertices_count: Number of B-Rep vertices
            - is_solid: True if solid body (vs surface body)

        Example response:
            {
                "success": true,
                "properties": {
                    "volume": 50000.0,
                    "area": 13000.0,
                    "center_of_mass": {"x": 50.0, "y": 25.0, "z": 5.0},
                    "bounding_box": {"min": [0, 0, 0], "max": [100, 50, 10]},
                    "dimensions": {"width": 100.0, "depth": 50.0, "height": 10.0},
                    "faces_count": 6,
                    "edges_count": 12,
                    "vertices_count": 8
                },
                "body_id": "base_plate",
                "is_solid": true
            }

        Units are always in mm, mm², or mm³. Measurements are accurate
        to 0.001mm (1 micron).
        """
        logger.info("get_body_properties called", body_id=body_id)
        async with FusionClient() as client:
            return await client.get_body_properties(body_id)

    @mcp.tool()
    async def get_sketch_status(sketch_id: str) -> dict:
        """Get the constraint status of a sketch.

        Returns information about whether a sketch is fully constrained
        (all geometry locked in position) and profile validity for
        feature creation.

        **Use cases:**
        - Check if sketch is ready for extrusion (e.g., "Can I extrude this?")
        - Debug constraint issues (e.g., "Why is the sketch moving?")
        - Verify sketch completeness (e.g., "Are there closed profiles?")

        A fully constrained sketch has all geometry position locked by
        dimensions and geometric constraints. Under-constrained curves
        can still move, which may cause unexpected results in features.

        Args:
            sketch_id: ID of the sketch to analyze.
                      Use get_sketches() to find available sketch IDs.

        Returns:
            Dict containing:
            - is_fully_constrained: True if all curves are constrained
            - under_constrained_count: Number of movable curves
            - profiles_count: Number of closed profile regions
            - curves_count: Total number of sketch curves
            - constraints_count: Number of geometric constraints
            - dimensions_count: Number of dimensional constraints
            - has_valid_profiles: True if at least one profile exists

        Example response (well-defined sketch):
            {
                "success": true,
                "sketch_id": "Sketch1",
                "is_fully_constrained": true,
                "under_constrained_count": 0,
                "profiles_count": 1,
                "curves_count": 4,
                "constraints_count": 8,
                "dimensions_count": 2,
                "has_valid_profiles": true
            }

        Example response (under-constrained sketch):
            {
                "success": true,
                "sketch_id": "Sketch2",
                "is_fully_constrained": false,
                "under_constrained_count": 2,
                "profiles_count": 0,
                "curves_count": 3,
                "constraints_count": 1,
                "dimensions_count": 0,
                "has_valid_profiles": false
            }

        Tip: A sketch needs closed profiles (profiles_count > 0) for
        extrude/revolve operations. has_valid_profiles indicates readiness.
        """
        logger.info("get_sketch_status called", sketch_id=sketch_id)
        async with FusionClient() as client:
            return await client.get_sketch_status(sketch_id)

    logger.info("Validation tools registered")
