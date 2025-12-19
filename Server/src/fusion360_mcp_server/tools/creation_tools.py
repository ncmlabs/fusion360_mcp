"""Creation tools for Fusion 360 MCP Server.

These tools enable AI to create geometry, sketches, and features
in Fusion 360 designs. All dimensions are in millimeters (mm).
"""

from typing import Optional, List
from mcp.server.fastmcp import FastMCP

from ..services.fusion_client import FusionClient
from ..logging import get_logger

logger = get_logger(__name__)


def register_creation_tools(mcp: FastMCP) -> None:
    """Register all creation tools with the MCP server.

    Args:
        mcp: FastMCP server instance
    """

    # --- Body Creation Tools ---

    @mcp.tool()
    async def create_box(
        width: float,
        depth: float,
        height: float,
        x: float = 0.0,
        y: float = 0.0,
        z: float = 0.0,
        name: Optional[str] = None,
        plane: str = "XY",
    ) -> dict:
        """Create a box (rectangular prism) in the design.

        Creates a solid box by sketching a rectangle and extruding it.
        The box is centered at the specified (x, y) position on the
        chosen construction plane.

        **All dimensions are in millimeters (mm).**

        Args:
            width: Box width in mm (X direction on XY plane). Must be positive.
            depth: Box depth in mm (Y direction on XY plane). Must be positive.
            height: Box height in mm (extrusion direction). Must be positive.
            x: X position of box center in mm. Default 0.
            y: Y position of box center in mm. Default 0.
            z: Z offset from the construction plane in mm. Default 0.
            name: Optional name for the created body. If not provided,
                  Fusion 360 will auto-generate a name like "Body1".
            plane: Construction plane for the base sketch.
                   Options: "XY" (default), "YZ", "XZ"

        Returns:
            Dict containing:
            - success: True if box was created
            - body: Body information including id, name, bounding_box, volume
            - feature: Feature information including id and type

        Example:
            # Create a 100x50x10mm base plate
            result = await create_box(width=100, depth=50, height=10, name="base_plate")

            # Create a box offset in Z
            result = await create_box(width=20, depth=20, height=30, z=10)

            # Create a box on the XZ plane (vertical)
            result = await create_box(width=50, depth=30, height=20, plane="XZ")
        """
        logger.info(
            "create_box called",
            width=width,
            depth=depth,
            height=height,
            x=x,
            y=y,
            z=z,
            name=name,
            plane=plane,
        )
        async with FusionClient() as client:
            return await client.create_box(
                width=width,
                depth=depth,
                height=height,
                x=x,
                y=y,
                z=z,
                name=name,
                plane=plane,
            )

    @mcp.tool()
    async def create_cylinder(
        radius: float,
        height: float,
        x: float = 0.0,
        y: float = 0.0,
        z: float = 0.0,
        name: Optional[str] = None,
        plane: str = "XY",
    ) -> dict:
        """Create a cylinder in the design.

        Creates a solid cylinder by sketching a circle and extruding it.
        The cylinder is centered at the specified (x, y) position.

        **All dimensions are in millimeters (mm).**

        Args:
            radius: Cylinder radius in mm. Must be positive.
            height: Cylinder height in mm (extrusion distance). Must be positive.
            x: X position of cylinder center in mm. Default 0.
            y: Y position of cylinder center in mm. Default 0.
            z: Z offset from the construction plane in mm. Default 0.
            name: Optional name for the created body.
            plane: Construction plane for the base circle.
                   Options: "XY" (default), "YZ", "XZ"

        Returns:
            Dict containing:
            - success: True if cylinder was created
            - body: Body information including id, name, bounding_box, volume
            - feature: Feature information including id and type

        Example:
            # Create a cylinder with 25mm radius and 50mm height
            result = await create_cylinder(radius=25, height=50, name="shaft")

            # Create an offset cylinder
            result = await create_cylinder(radius=10, height=20, x=50, y=50)
        """
        logger.info(
            "create_cylinder called",
            radius=radius,
            height=height,
            x=x,
            y=y,
            z=z,
            name=name,
            plane=plane,
        )
        async with FusionClient() as client:
            return await client.create_cylinder(
                radius=radius,
                height=height,
                x=x,
                y=y,
                z=z,
                name=name,
                plane=plane,
            )

    # --- Sketch Creation Tools ---

    @mcp.tool()
    async def create_sketch(
        plane: str = "XY",
        name: Optional[str] = None,
        offset: float = 0.0,
    ) -> dict:
        """Create a new sketch on a construction plane.

        Creates an empty sketch that you can then draw geometry into
        using draw_line, draw_circle, draw_rectangle, and draw_arc.

        Args:
            plane: Construction plane for the sketch.
                   Options: "XY" (default), "YZ", "XZ", or a face_id reference
            name: Optional name for the sketch.
            offset: Offset from the plane in mm. Use for sketching at a
                   specific Z height (for XY plane). Default 0.

        Returns:
            Dict containing:
            - success: True if sketch was created
            - sketch: Sketch information including id, name, plane info

        Example:
            # Create a sketch on the XY plane
            result = await create_sketch(plane="XY", name="base_profile")
            sketch_id = result["sketch"]["id"]

            # Create an offset sketch at Z=10mm
            result = await create_sketch(plane="XY", offset=10)
        """
        logger.info(
            "create_sketch called",
            plane=plane,
            name=name,
            offset=offset,
        )
        async with FusionClient() as client:
            return await client.create_sketch(plane=plane, name=name, offset=offset)

    @mcp.tool()
    async def draw_line(
        sketch_id: str,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
    ) -> dict:
        """Draw a line in a sketch.

        **All coordinates are in millimeters (mm).**

        Args:
            sketch_id: ID of the sketch to draw in. Get this from create_sketch
                      or get_sketches.
            start_x: Start point X coordinate in mm.
            start_y: Start point Y coordinate in mm.
            end_x: End point X coordinate in mm.
            end_y: End point Y coordinate in mm.

        Returns:
            Dict containing:
            - success: True if line was drawn
            - curve: Curve information including id, type, start_point, end_point, length
            - sketch_id: The sketch the line was added to

        Example:
            # Draw a horizontal line
            result = await draw_line(
                sketch_id="Sketch1",
                start_x=0, start_y=0,
                end_x=100, end_y=0
            )
        """
        logger.info(
            "draw_line called",
            sketch_id=sketch_id,
            start_x=start_x,
            start_y=start_y,
            end_x=end_x,
            end_y=end_y,
        )
        async with FusionClient() as client:
            return await client.draw_line(
                sketch_id=sketch_id,
                start_x=start_x,
                start_y=start_y,
                end_x=end_x,
                end_y=end_y,
            )

    @mcp.tool()
    async def draw_circle(
        sketch_id: str,
        center_x: float,
        center_y: float,
        radius: float,
    ) -> dict:
        """Draw a circle in a sketch.

        Creates a closed circular profile that can be extruded.

        **All dimensions are in millimeters (mm).**

        Args:
            sketch_id: ID of the sketch to draw in.
            center_x: Center X coordinate in mm.
            center_y: Center Y coordinate in mm.
            radius: Circle radius in mm. Must be positive.

        Returns:
            Dict containing:
            - success: True if circle was drawn
            - curve: Curve information including id, type, center, radius
            - sketch_id: The sketch the circle was added to
            - profiles_count: Number of closed profiles in the sketch

        Example:
            # Draw a circle at origin with 25mm radius
            result = await draw_circle(
                sketch_id="Sketch1",
                center_x=0, center_y=0,
                radius=25
            )
        """
        logger.info(
            "draw_circle called",
            sketch_id=sketch_id,
            center_x=center_x,
            center_y=center_y,
            radius=radius,
        )
        async with FusionClient() as client:
            return await client.draw_circle(
                sketch_id=sketch_id,
                center_x=center_x,
                center_y=center_y,
                radius=radius,
            )

    @mcp.tool()
    async def draw_rectangle(
        sketch_id: str,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ) -> dict:
        """Draw a rectangle in a sketch using two corner points.

        Creates a closed rectangular profile that can be extruded.

        **All coordinates are in millimeters (mm).**

        Args:
            sketch_id: ID of the sketch to draw in.
            x1: First corner X coordinate in mm.
            y1: First corner Y coordinate in mm.
            x2: Opposite corner X coordinate in mm.
            y2: Opposite corner Y coordinate in mm.

        Returns:
            Dict containing:
            - success: True if rectangle was drawn
            - curves: List of curve IDs for the 4 lines
            - rectangle: Rectangle info with corners, width, height
            - sketch_id: The sketch the rectangle was added to
            - profiles_count: Number of closed profiles in the sketch

        Example:
            # Draw a 100x50mm rectangle
            result = await draw_rectangle(
                sketch_id="Sketch1",
                x1=-50, y1=-25,
                x2=50, y2=25
            )
        """
        logger.info(
            "draw_rectangle called",
            sketch_id=sketch_id,
            x1=x1,
            y1=y1,
            x2=x2,
            y2=y2,
        )
        async with FusionClient() as client:
            return await client.draw_rectangle(
                sketch_id=sketch_id,
                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,
            )

    @mcp.tool()
    async def draw_arc(
        sketch_id: str,
        center_x: float,
        center_y: float,
        radius: float,
        start_angle: float,
        end_angle: float,
    ) -> dict:
        """Draw an arc in a sketch.

        Creates an arc from start_angle to end_angle, measured counterclockwise
        from the positive X axis.

        **Dimensions in mm, angles in degrees.**

        Args:
            sketch_id: ID of the sketch to draw in.
            center_x: Center X coordinate in mm.
            center_y: Center Y coordinate in mm.
            radius: Arc radius in mm. Must be positive.
            start_angle: Start angle in degrees (0 = positive X axis).
            end_angle: End angle in degrees (counterclockwise from start).

        Returns:
            Dict containing:
            - success: True if arc was drawn
            - curve: Curve information including id, type, center, radius, angles
            - sketch_id: The sketch the arc was added to

        Example:
            # Draw a quarter circle arc (90 degrees)
            result = await draw_arc(
                sketch_id="Sketch1",
                center_x=0, center_y=0,
                radius=50,
                start_angle=0, end_angle=90
            )
        """
        logger.info(
            "draw_arc called",
            sketch_id=sketch_id,
            center_x=center_x,
            center_y=center_y,
            radius=radius,
            start_angle=start_angle,
            end_angle=end_angle,
        )
        async with FusionClient() as client:
            return await client.draw_arc(
                sketch_id=sketch_id,
                center_x=center_x,
                center_y=center_y,
                radius=radius,
                start_angle=start_angle,
                end_angle=end_angle,
            )

    # --- Advanced Sketch Geometry Tools ---

    @mcp.tool()
    async def draw_polygon(
        sketch_id: str,
        radius: float,
        sides: int,
        center_x: float = 0.0,
        center_y: float = 0.0,
        rotation_angle: float = 0.0,
    ) -> dict:
        """Draw a regular polygon in a sketch.

        Creates a regular polygon (triangle, square, pentagon, hexagon, etc.)
        by calculating vertices on a circumscribed circle and connecting them.

        **All dimensions in millimeters (mm), angles in degrees.**

        Args:
            sketch_id: ID of the sketch to draw in.
            radius: Circumscribed circle radius in mm (distance from center to vertex).
                   Must be positive.
            sides: Number of sides (3-64). Examples: 3=triangle, 4=square,
                  5=pentagon, 6=hexagon, 8=octagon.
            center_x: Center X coordinate in mm. Default 0.
            center_y: Center Y coordinate in mm. Default 0.
            rotation_angle: Rotation angle in degrees. Default 0 (first vertex
                           points in positive X direction).

        Returns:
            Dict containing:
            - success: True if polygon was created
            - curves: List of curve IDs for the polygon edges
            - polygon: Polygon info with center, radius, sides, side_length,
                      apothem, perimeter, area
            - sketch_id: The sketch the polygon was added to
            - profiles_count: Number of closed profiles in the sketch

        Example:
            # Draw a hexagon with 20mm radius
            result = await draw_polygon(
                sketch_id="Sketch1",
                radius=20,
                sides=6
            )

            # Draw a rotated octagon
            result = await draw_polygon(
                sketch_id="Sketch1",
                center_x=50, center_y=50,
                radius=15,
                sides=8,
                rotation_angle=22.5
            )
        """
        logger.info(
            "draw_polygon called",
            sketch_id=sketch_id,
            center_x=center_x,
            center_y=center_y,
            radius=radius,
            sides=sides,
            rotation_angle=rotation_angle,
        )
        async with FusionClient() as client:
            return await client.draw_polygon(
                sketch_id=sketch_id,
                center_x=center_x,
                center_y=center_y,
                radius=radius,
                sides=sides,
                rotation_angle=rotation_angle,
            )

    @mcp.tool()
    async def draw_ellipse(
        sketch_id: str,
        major_radius: float,
        minor_radius: float,
        center_x: float = 0.0,
        center_y: float = 0.0,
        rotation_angle: float = 0.0,
    ) -> dict:
        """Draw an ellipse in a sketch.

        Creates an ellipse (oval) with specified major and minor radii.

        **All dimensions in millimeters (mm), angles in degrees.**

        Args:
            sketch_id: ID of the sketch to draw in.
            major_radius: Major axis radius in mm (longest radius). Must be positive.
            minor_radius: Minor axis radius in mm (shortest radius). Must be positive
                         and less than or equal to major_radius.
            center_x: Center X coordinate in mm. Default 0.
            center_y: Center Y coordinate in mm. Default 0.
            rotation_angle: Rotation of major axis in degrees. Default 0
                           (major axis along positive X).

        Returns:
            Dict containing:
            - success: True if ellipse was created
            - curve: Curve info with id, type, center, radii, perimeter, area
            - sketch_id: The sketch the ellipse was added to
            - profiles_count: Number of closed profiles in the sketch

        Example:
            # Draw an ellipse with 30mm x 20mm radii
            result = await draw_ellipse(
                sketch_id="Sketch1",
                major_radius=30,
                minor_radius=20
            )

            # Draw a 45-degree rotated ellipse
            result = await draw_ellipse(
                sketch_id="Sketch1",
                center_x=50, center_y=0,
                major_radius=25,
                minor_radius=15,
                rotation_angle=45
            )
        """
        logger.info(
            "draw_ellipse called",
            sketch_id=sketch_id,
            center_x=center_x,
            center_y=center_y,
            major_radius=major_radius,
            minor_radius=minor_radius,
            rotation_angle=rotation_angle,
        )
        async with FusionClient() as client:
            return await client.draw_ellipse(
                sketch_id=sketch_id,
                center_x=center_x,
                center_y=center_y,
                major_radius=major_radius,
                minor_radius=minor_radius,
                rotation_angle=rotation_angle,
            )

    @mcp.tool()
    async def draw_slot(
        sketch_id: str,
        length: float,
        width: float,
        center_x: float = 0.0,
        center_y: float = 0.0,
        slot_type: str = "overall",
        rotation_angle: float = 0.0,
    ) -> dict:
        """Draw a slot shape (rounded rectangle/oblong) in a sketch.

        Creates a slot by drawing two parallel lines connected by two
        semicircular arcs. Commonly used for mounting holes and adjustable
        fastener positions.

        **All dimensions in millimeters (mm), angles in degrees.**

        Args:
            sketch_id: ID of the sketch to draw in.
            length: Slot length in mm. Interpretation depends on slot_type.
            width: Slot width in mm (diameter of the rounded ends). Must be positive.
            center_x: Center X coordinate in mm. Default 0.
            center_y: Center Y coordinate in mm. Default 0.
            slot_type: How to interpret the length parameter:
                      - "overall": length is total slot length (default)
                      - "center_to_center": length is distance between arc centers
            rotation_angle: Rotation angle in degrees. Default 0 (horizontal slot).

        Returns:
            Dict containing:
            - success: True if slot was created
            - curves: List of curve IDs (2 lines + 2 arcs)
            - slot: Slot info with overall_length, center_to_center, width,
                   perimeter, area
            - sketch_id: The sketch the slot was added to
            - profiles_count: Number of closed profiles in the sketch

        Example:
            # Draw a horizontal 30mm x 8mm slot
            result = await draw_slot(
                sketch_id="Sketch1",
                length=30,
                width=8
            )

            # Draw a vertical slot using center-to-center measurement
            result = await draw_slot(
                sketch_id="Sketch1",
                center_x=50, center_y=0,
                length=20,
                width=6,
                slot_type="center_to_center",
                rotation_angle=90
            )
        """
        logger.info(
            "draw_slot called",
            sketch_id=sketch_id,
            center_x=center_x,
            center_y=center_y,
            length=length,
            width=width,
            slot_type=slot_type,
            rotation_angle=rotation_angle,
        )
        async with FusionClient() as client:
            return await client.draw_slot(
                sketch_id=sketch_id,
                center_x=center_x,
                center_y=center_y,
                length=length,
                width=width,
                slot_type=slot_type,
                rotation_angle=rotation_angle,
            )

    @mcp.tool()
    async def draw_spline(
        sketch_id: str,
        points: List[dict],
        is_closed: bool = False,
    ) -> dict:
        """Draw a spline (smooth curve) through control points in a sketch.

        Creates a fitted spline that passes smoothly through all specified
        points. Useful for organic shapes and smooth contours.

        **All coordinates in millimeters (mm).**

        Args:
            sketch_id: ID of the sketch to draw in.
            points: List of point dicts with 'x' and 'y' coordinates in mm.
                   Must have at least 2 points (3 for closed spline).
                   Example: [{"x": 0, "y": 0}, {"x": 10, "y": 5}, {"x": 20, "y": 0}]
            is_closed: If True, create a closed spline loop. Default False.
                      Closed splines require at least 3 points.

        Returns:
            Dict containing:
            - success: True if spline was created
            - curve: Curve info with id, type, points, point_count, is_closed
            - sketch_id: The sketch the spline was added to
            - profiles_count: Number of closed profiles (for closed splines)

        Example:
            # Draw an open spline through 4 points
            result = await draw_spline(
                sketch_id="Sketch1",
                points=[
                    {"x": 0, "y": 0},
                    {"x": 20, "y": 15},
                    {"x": 40, "y": -10},
                    {"x": 60, "y": 5}
                ]
            )

            # Draw a closed spline (organic shape)
            result = await draw_spline(
                sketch_id="Sketch1",
                points=[
                    {"x": 0, "y": 20},
                    {"x": 20, "y": 0},
                    {"x": 0, "y": -20},
                    {"x": -20, "y": 0}
                ],
                is_closed=True
            )
        """
        logger.info(
            "draw_spline called",
            sketch_id=sketch_id,
            point_count=len(points) if points else 0,
            is_closed=is_closed,
        )
        async with FusionClient() as client:
            return await client.draw_spline(
                sketch_id=sketch_id,
                points=points,
                is_closed=is_closed,
            )

    @mcp.tool()
    async def draw_point(
        sketch_id: str,
        x: float,
        y: float,
        is_construction: bool = False,
    ) -> dict:
        """Draw a point in a sketch.

        Creates a sketch point that can be used as a reference for dimensions,
        constraints, or as construction geometry for parametric designs.

        **All coordinates in millimeters (mm).**

        Args:
            sketch_id: ID of the sketch to draw in.
            x: X coordinate in mm.
            y: Y coordinate in mm.
            is_construction: If True, mark as construction geometry. Default False.
                            Construction geometry is used for reference but doesn't
                            appear in profiles for extrusion.

        Returns:
            Dict containing:
            - success: True if point was created
            - point: Point info with id, position, is_construction
            - sketch_id: The sketch the point was added to

        Example:
            # Draw a reference point at the origin
            result = await draw_point(
                sketch_id="Sketch1",
                x=0, y=0
            )

            # Draw a construction point for alignment
            result = await draw_point(
                sketch_id="Sketch1",
                x=50, y=50,
                is_construction=True
            )
        """
        logger.info(
            "draw_point called",
            sketch_id=sketch_id,
            x=x,
            y=y,
            is_construction=is_construction,
        )
        async with FusionClient() as client:
            return await client.draw_point(
                sketch_id=sketch_id,
                x=x,
                y=y,
                is_construction=is_construction,
            )

    # --- Feature Creation Tools ---

    @mcp.tool()
    async def extrude(
        sketch_id: str,
        distance: float,
        direction: str = "positive",
        operation: str = "new_body",
        profile_index: int = 0,
        name: Optional[str] = None,
    ) -> dict:
        """Extrude a sketch profile to create 3D geometry.

        Takes a closed profile from a sketch and extrudes it perpendicular
        to the sketch plane.

        **Distance in millimeters (mm).**

        Args:
            sketch_id: ID of the sketch containing the profile.
            distance: Extrusion distance in mm. Must be positive.
            direction: Extrusion direction relative to sketch normal.
                      - "positive": Extrude in positive normal direction (default)
                      - "negative": Extrude in negative normal direction
                      - "symmetric": Extrude equally in both directions
            operation: How to combine with existing bodies.
                      - "new_body": Create a new body (default)
                      - "join": Add to existing body
                      - "cut": Subtract from existing body
                      - "intersect": Keep only intersection
            profile_index: Index of the profile to extrude (0-based).
                          Use 0 for the first/only profile.
            name: Optional name for the created body.

        Returns:
            Dict containing:
            - success: True if extrusion succeeded
            - feature: Feature information including id and type
            - bodies: List of created/modified bodies

        Example:
            # Create a sketch, draw a circle, and extrude it
            sketch = await create_sketch(plane="XY", name="circle_sketch")
            await draw_circle(sketch_id=sketch["sketch"]["id"], center_x=0, center_y=0, radius=25)
            result = await extrude(sketch_id=sketch["sketch"]["id"], distance=50)

            # Cut a hole using extrude with cut operation
            result = await extrude(
                sketch_id="hole_sketch",
                distance=20,
                operation="cut"
            )
        """
        logger.info(
            "extrude called",
            sketch_id=sketch_id,
            distance=distance,
            direction=direction,
            operation=operation,
            profile_index=profile_index,
            name=name,
        )
        async with FusionClient() as client:
            return await client.extrude(
                sketch_id=sketch_id,
                distance=distance,
                direction=direction,
                operation=operation,
                profile_index=profile_index,
                name=name,
            )

    @mcp.tool()
    async def revolve(
        sketch_id: str,
        axis: str,
        angle: float = 360.0,
        operation: str = "new_body",
        profile_index: int = 0,
        name: Optional[str] = None,
    ) -> dict:
        """Revolve a sketch profile around an axis.

        Creates a solid of revolution by rotating a sketch profile
        around an axis.

        **Angle in degrees.**

        Args:
            sketch_id: ID of the sketch containing the profile.
            axis: Axis to revolve around.
                  - "X": X construction axis
                  - "Y": Y construction axis
                  - "Z": Z construction axis
            angle: Revolution angle in degrees. 360 for full revolution (default).
            operation: How to combine with existing bodies.
                      - "new_body": Create a new body (default)
                      - "join": Add to existing body
                      - "cut": Subtract from existing body
                      - "intersect": Keep only intersection
            profile_index: Index of the profile to revolve (0-based).
            name: Optional name for the created body.

        Returns:
            Dict containing:
            - success: True if revolve succeeded
            - feature: Feature information
            - bodies: List of created/modified bodies

        Example:
            # Create a sphere by revolving a semicircle
            # First draw a semicircle profile, then:
            result = await revolve(sketch_id="sphere_profile", axis="Y", angle=360)
        """
        logger.info(
            "revolve called",
            sketch_id=sketch_id,
            axis=axis,
            angle=angle,
            operation=operation,
            profile_index=profile_index,
            name=name,
        )
        async with FusionClient() as client:
            return await client.revolve(
                sketch_id=sketch_id,
                axis=axis,
                angle=angle,
                operation=operation,
                profile_index=profile_index,
                name=name,
            )

    @mcp.tool()
    async def fillet(
        body_id: str,
        edge_ids: List[str],
        radius: float,
    ) -> dict:
        """Apply fillet (rounded edge) to body edges.

        Rounds the specified edges with the given radius.

        **Radius in millimeters (mm).**

        Args:
            body_id: ID of the body containing the edges.
            edge_ids: List of edge IDs to fillet. Get these from
                     get_body_by_id with include_edges=True.
            radius: Fillet radius in mm. Must be positive.

        Returns:
            Dict containing:
            - success: True if fillet succeeded
            - feature: Feature information
            - radius: Applied radius

        Example:
            # Get edges from a body
            body = await get_body_by_id(body_id="Body1", include_edges=True)

            # Apply 2mm fillet to all edges
            result = await fillet(
                body_id="Body1",
                edge_ids=[e["id"] for e in body["edges"]],
                radius=2
            )
        """
        logger.info(
            "fillet called",
            body_id=body_id,
            edge_ids=edge_ids,
            radius=radius,
        )
        async with FusionClient() as client:
            return await client.fillet(
                body_id=body_id,
                edge_ids=edge_ids,
                radius=radius,
            )

    @mcp.tool()
    async def chamfer(
        body_id: str,
        edge_ids: List[str],
        distance: float,
        distance2: Optional[float] = None,
    ) -> dict:
        """Apply chamfer (beveled edge) to body edges.

        Bevels the specified edges at the given distance(s).

        **Distance in millimeters (mm).**

        Args:
            body_id: ID of the body containing the edges.
            edge_ids: List of edge IDs to chamfer.
            distance: Chamfer distance in mm. Must be positive.
            distance2: Optional second distance for asymmetric chamfer.
                      If provided, creates an asymmetric chamfer with
                      different distances on each face.

        Returns:
            Dict containing:
            - success: True if chamfer succeeded
            - feature: Feature information
            - distance: Applied distance(s)

        Example:
            # Apply 1mm chamfer to edges
            result = await chamfer(
                body_id="Body1",
                edge_ids=["Body1_edge_0", "Body1_edge_1"],
                distance=1
            )

            # Asymmetric chamfer (1mm x 2mm)
            result = await chamfer(
                body_id="Body1",
                edge_ids=["Body1_edge_0"],
                distance=1,
                distance2=2
            )
        """
        logger.info(
            "chamfer called",
            body_id=body_id,
            edge_ids=edge_ids,
            distance=distance,
            distance2=distance2,
        )
        async with FusionClient() as client:
            return await client.chamfer(
                body_id=body_id,
                edge_ids=edge_ids,
                distance=distance,
                distance2=distance2,
            )

    @mcp.tool()
    async def create_hole(
        diameter: float,
        depth: float,
        body_id: Optional[str] = None,
        face_id: Optional[str] = None,
        x: float = 0.0,
        y: float = 0.0,
        name: Optional[str] = None,
        hole_type: str = "simple",
    ) -> dict:
        """Create a hole in a body.

        Creates a cylindrical hole at the specified position.

        **All dimensions in millimeters (mm).**

        Args:
            diameter: Hole diameter in mm. Must be positive.
            depth: Hole depth in mm. Must be positive.
            body_id: ID of the body to drill into.
                    Either body_id or face_id must be provided.
            face_id: ID of the face to place the hole on.
                    Overrides body_id if both are provided.
            x: X position of hole center in mm on the face.
            y: Y position of hole center in mm on the face.
            name: Optional name for the hole feature.
            hole_type: Type of hole.
                      - "simple": Plain cylindrical hole (default)
                      - "countersink": Hole with countersink
                      - "counterbore": Hole with counterbore

        Returns:
            Dict containing:
            - success: True if hole was created
            - feature: Feature information including hole details
            - body_id: ID of the body the hole was made in

        Example:
            # Create a 6.5mm diameter, 10mm deep hole
            result = await create_hole(
                body_id="base_plate",
                diameter=6.5,
                depth=10,
                x=15, y=15
            )

            # Create a countersink hole for a screw
            result = await create_hole(
                body_id="cover_plate",
                diameter=5,
                depth=20,
                hole_type="countersink"
            )
        """
        logger.info(
            "create_hole called",
            diameter=diameter,
            depth=depth,
            body_id=body_id,
            face_id=face_id,
            x=x,
            y=y,
            name=name,
            hole_type=hole_type,
        )
        async with FusionClient() as client:
            return await client.create_hole(
                diameter=diameter,
                depth=depth,
                body_id=body_id,
                face_id=face_id,
                x=x,
                y=y,
                name=name,
                hole_type=hole_type,
            )

    logger.info("Creation tools registered")
