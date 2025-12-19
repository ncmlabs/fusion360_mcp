"""Query tools for Fusion 360 MCP Server.

These tools enable AI to query the current Fusion 360 design state,
bodies, sketches, parameters, and timeline.
"""

from typing import Optional
from mcp.server.fastmcp import FastMCP

from ..services.fusion_client import FusionClient
from ..logging import get_logger

logger = get_logger(__name__)


def register_query_tools(mcp: FastMCP) -> None:
    """Register all query tools with the MCP server.

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool()
    async def get_design_state() -> dict:
        """Get the current Fusion 360 design state.

        Returns comprehensive design information including:
        - Design name and units (mm, cm, in, etc.)
        - Total count of bodies, sketches, and components
        - Timeline feature count
        - Active component ID

        **Use this first** to understand the current design context before
        making any modifications. This gives you an overview of what exists
        in the design.

        Returns:
            Dict containing design state information

        Example response:
            {
                "name": "MyDesign",
                "units": "mm",
                "bodies_count": 3,
                "sketches_count": 2,
                "components_count": 1,
                "timeline_count": 5,
                "active_component_id": "RootComponent"
            }
        """
        logger.info("get_design_state called")
        async with FusionClient() as client:
            return await client.get_design_state()

    @mcp.tool()
    async def get_bodies(component_id: Optional[str] = None) -> dict:
        """Get all bodies in the design or a specific component.

        Lists all solid and surface bodies with their key properties.
        Use this to understand what geometry exists before modifying it.

        Args:
            component_id: Optional component ID to filter bodies.
                         If not provided, returns bodies from root component.

        Returns:
            Dict containing:
            - bodies: List of body summaries with id, name, volume, bounding_box
            - total: Total count of bodies
            - component_id: The component that was queried

        Each body summary includes:
        - id: Unique identifier for referencing this body in other operations
        - name: Display name of the body
        - is_solid: True if solid body, False if surface body
        - bounding_box: Spatial extent with min/max points
        - volume: Body volume in mm^3
        - faces_count: Number of faces

        Example response:
            {
                "bodies": [
                    {
                        "id": "Body1",
                        "name": "Body1",
                        "is_solid": true,
                        "bounding_box": {
                            "min_point": {"x": 0, "y": 0, "z": 0},
                            "max_point": {"x": 100, "y": 50, "z": 10}
                        },
                        "volume": 50000.0,
                        "faces_count": 6
                    }
                ],
                "total": 1,
                "component_id": null
            }
        """
        logger.info("get_bodies called", component_id=component_id)
        async with FusionClient() as client:
            bodies = await client.get_bodies(component_id)
            return {
                "bodies": bodies,
                "total": len(bodies),
                "component_id": component_id,
            }

    @mcp.tool()
    async def get_body_by_id(
        body_id: str,
        include_faces: bool = False,
        include_edges: bool = False,
    ) -> dict:
        """Get detailed information about a specific body.

        Retrieves comprehensive body data including topology details
        when requested. Use this when you need detailed information
        about a specific body for modifications or measurements.

        Args:
            body_id: The body ID (from get_bodies). This is required.
            include_faces: Include face geometry details (type, area, normal).
                          Set to True when you need to select faces for operations.
            include_edges: Include edge geometry details (type, length).
                          Set to True when you need to select edges for fillets/chamfers.

        Returns:
            Dict with full body information including:
            - All summary fields (name, volume, bounding_box)
            - faces_count, edges_count, vertices_count
            - center_of_mass: Center of mass point
            - area: Total surface area in mm^2
            - component_id: Parent component ID
            - Optional faces array with type, area, normal for each face
            - Optional edges array with type, length for each edge

        Use include_faces/include_edges only when needed, as they add
        significant data to the response.

        Example response (with include_faces=True):
            {
                "id": "Body1",
                "name": "Body1",
                "is_solid": true,
                "volume": 50000.0,
                "area": 13000.0,
                "faces_count": 6,
                "edges_count": 12,
                "vertices_count": 8,
                "faces": [
                    {
                        "id": "Body1_face_0",
                        "face_type": "planar",
                        "area": 5000.0,
                        "normal": {"x": 0, "y": 0, "z": 1}
                    }
                ]
            }
        """
        logger.info(
            "get_body_by_id called",
            body_id=body_id,
            include_faces=include_faces,
            include_edges=include_edges,
        )
        async with FusionClient() as client:
            return await client.get_body_by_id(
                body_id,
                include_faces=include_faces,
                include_edges=include_edges,
            )

    @mcp.tool()
    async def get_sketches(component_id: Optional[str] = None) -> dict:
        """Get all sketches in the design or a specific component.

        Lists all sketches with their key properties. Sketches are
        2D drawings that define profiles for features like extrusions.

        Args:
            component_id: Optional component ID to filter sketches.
                         If not provided, returns sketches from root component.

        Returns:
            Dict containing:
            - sketches: List of sketch summaries
            - total: Total count of sketches
            - component_id: The component that was queried

        Each sketch summary includes:
        - id: Unique identifier for the sketch
        - name: Display name of the sketch
        - plane: Reference plane information
        - is_fully_constrained: True if all geometry is constrained
        - curves_count: Number of sketch curves
        - profiles_count: Number of closed profiles (regions)

        Example response:
            {
                "sketches": [
                    {
                        "id": "Sketch1",
                        "name": "Sketch1",
                        "is_fully_constrained": true,
                        "curves_count": 4,
                        "profiles_count": 1
                    }
                ],
                "total": 1
            }
        """
        logger.info("get_sketches called", component_id=component_id)
        async with FusionClient() as client:
            sketches = await client.get_sketches(component_id)
            return {
                "sketches": sketches,
                "total": len(sketches),
                "component_id": component_id,
            }

    @mcp.tool()
    async def get_sketch_by_id(
        sketch_id: str,
        include_curves: bool = True,
        include_constraints: bool = True,
        include_dimensions: bool = True,
        include_profiles: bool = False,
    ) -> dict:
        """Get detailed information about a specific sketch.

        Retrieves comprehensive sketch data including geometry,
        constraints, and dimensions. Use this when you need to
        understand or modify a specific sketch.

        Args:
            sketch_id: The sketch ID (from get_sketches). Required.
            include_curves: Include curve geometry details (default True).
            include_constraints: Include constraint details (default True).
            include_dimensions: Include dimension details (default True).
            include_profiles: Include profile details for extrusion.

        Returns:
            Dict with full sketch information including:
            - All summary fields (name, plane, constraint status)
            - curves: Array of sketch curves with geometry
            - constraints: Array of geometric constraints
            - dimensions: Array of dimensions with values
            - profiles: Array of closed profile regions (if requested)

        Example response:
            {
                "id": "Sketch1",
                "name": "Sketch1",
                "is_fully_constrained": true,
                "curves": [
                    {
                        "id": "Sketch1_curve_0",
                        "curve_type": "line",
                        "start_point": {"x": 0, "y": 0, "z": 0},
                        "end_point": {"x": 100, "y": 0, "z": 0},
                        "length": 100.0
                    }
                ],
                "dimensions": [
                    {
                        "id": "Sketch1_dimension_0",
                        "dimension_type": "linear",
                        "value": 100.0,
                        "expression": "100 mm"
                    }
                ]
            }
        """
        logger.info(
            "get_sketch_by_id called",
            sketch_id=sketch_id,
            include_curves=include_curves,
        )
        async with FusionClient() as client:
            return await client.get_sketch_by_id(
                sketch_id,
                include_curves=include_curves,
                include_constraints=include_constraints,
                include_dimensions=include_dimensions,
                include_profiles=include_profiles,
            )

    @mcp.tool()
    async def get_parameters(user_only: bool = False) -> dict:
        """Get all parameters in the design.

        Retrieves model and user parameters. Parameters drive dimensions
        and can be modified to update the design parametrically.

        Args:
            user_only: If True, only return user-defined parameters.
                      Model parameters (created by features) are excluded.

        Returns:
            Dict containing:
            - parameters: List of parameter objects
            - total: Total count of parameters

        Each parameter includes:
        - id: Parameter name (used as identifier)
        - name: Display name
        - value: Current value in internal units
        - expression: Value expression (may include units or formulas)
        - unit: Unit of measurement
        - is_user_parameter: True if user-created
        - comment: Optional description
        - is_favorite: True if marked as favorite

        Example response:
            {
                "parameters": [
                    {
                        "id": "width",
                        "name": "width",
                        "value": 100.0,
                        "expression": "100 mm",
                        "unit": "mm",
                        "is_user_parameter": true
                    },
                    {
                        "id": "d1",
                        "name": "d1",
                        "value": 50.0,
                        "expression": "width / 2",
                        "unit": "mm",
                        "is_user_parameter": false
                    }
                ],
                "total": 2
            }
        """
        logger.info("get_parameters called", user_only=user_only)
        async with FusionClient() as client:
            parameters = await client.get_parameters(user_only=user_only)
            return {
                "parameters": parameters,
                "total": len(parameters),
                "user_only": user_only,
            }

    @mcp.tool()
    async def get_timeline() -> dict:
        """Get the design timeline (feature history).

        Retrieves the ordered list of features that created the design.
        The timeline shows the parametric history and can be used to
        understand how the design was built.

        Returns:
            Dict containing:
            - timeline: List of timeline entries in creation order
            - total: Total count of timeline entries
            - marker_position: Current timeline marker position

        Each timeline entry includes:
        - index: Position in timeline (0-based)
        - name: Feature name
        - feature_type: Type of feature (extrude, revolve, etc.)
        - is_suppressed: True if feature is suppressed
        - is_group: True if this is a group
        - is_rolled_back: True if rolled back past this feature
        - health_state: "healthy", "warning", or "error"
        - parent_group_index: Index of parent group (if in a group)

        Example response:
            {
                "timeline": [
                    {
                        "index": 0,
                        "name": "Sketch1",
                        "feature_type": "sketch",
                        "is_suppressed": false,
                        "health_state": "healthy"
                    },
                    {
                        "index": 1,
                        "name": "Extrusion1",
                        "feature_type": "extrude",
                        "is_suppressed": false,
                        "health_state": "healthy"
                    }
                ],
                "total": 2,
                "marker_position": 2
            }
        """
        logger.info("get_timeline called")
        async with FusionClient() as client:
            return await client.get_timeline()

    logger.info("Query tools registered")
