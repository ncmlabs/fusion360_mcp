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

    # --- Phase 7b: Sketch Patterns & Operations ---

    @mcp.tool()
    async def sketch_mirror(
        sketch_id: str,
        curve_ids: List[str],
        mirror_line_id: str,
    ) -> dict:
        """Mirror sketch entities across a line.

        Creates mirrored copies of the specified curves across a mirror line,
        useful for creating symmetric geometry.

        Args:
            sketch_id: ID of the sketch containing the curves.
            curve_ids: List of curve IDs to mirror. Get these from draw_* operations
                      or get_sketch_by_id.
            mirror_line_id: ID of the line to mirror across. Must be a SketchLine
                           (not a circle or arc).

        Returns:
            Dict containing:
            - success: True if mirror succeeded
            - mirrored_curves: List of new curve IDs created
            - original_curves: Original curve IDs that were mirrored
            - mirror_line_id: The mirror line used
            - sketch_id: The sketch ID
            - profiles_count: Number of closed profiles in sketch

        Example:
            # Draw a rectangle and mirror it across a vertical centerline
            sketch = await create_sketch(plane="XY")
            sketch_id = sketch["sketch"]["id"]

            # Draw rectangle on left side
            rect = await draw_rectangle(sketch_id=sketch_id, x1=-50, y1=0, x2=-10, y2=30)

            # Draw vertical centerline
            line = await draw_line(sketch_id=sketch_id, start_x=0, start_y=-10, end_x=0, end_y=40)

            # Mirror rectangle across centerline
            result = await sketch_mirror(
                sketch_id=sketch_id,
                curve_ids=rect["curves"],
                mirror_line_id=line["curve"]["id"]
            )
        """
        logger.info(
            "sketch_mirror called",
            sketch_id=sketch_id,
            curve_count=len(curve_ids),
            mirror_line_id=mirror_line_id,
        )
        async with FusionClient() as client:
            return await client.sketch_mirror(
                sketch_id=sketch_id,
                curve_ids=curve_ids,
                mirror_line_id=mirror_line_id,
            )

    @mcp.tool()
    async def sketch_circular_pattern(
        sketch_id: str,
        curve_ids: List[str],
        count: int,
        center_x: float = 0.0,
        center_y: float = 0.0,
        total_angle: float = 360.0,
    ) -> dict:
        """Create a circular pattern of sketch entities.

        Copies the specified curves in a circular array around a center point.
        Commonly used for bolt hole patterns, gear teeth, and radial features.

        **Coordinates in millimeters (mm), angles in degrees.**

        Args:
            sketch_id: ID of the sketch containing the curves.
            curve_ids: List of curve IDs to pattern.
            count: Total number of instances (including original). Must be 2-360.
            center_x: Pattern center X coordinate in mm. Default 0.
            center_y: Pattern center Y coordinate in mm. Default 0.
            total_angle: Total angle span in degrees. Default 360 (full circle).
                        Use smaller values for partial patterns.

        Returns:
            Dict containing:
            - success: True if pattern succeeded
            - pattern_curves: List of new curve IDs created (excludes original)
            - original_curves: The original curve IDs
            - pattern: Pattern info with type, center, count, angles
            - sketch_id: The sketch ID
            - profiles_count: Number of closed profiles

        Example:
            # Create a 6-hole bolt pattern
            sketch = await create_sketch(plane="XY")
            sketch_id = sketch["sketch"]["id"]

            # Draw one mounting hole
            hole = await draw_circle(sketch_id=sketch_id, center_x=40, center_y=0, radius=3)

            # Create 6-hole pattern around origin
            result = await sketch_circular_pattern(
                sketch_id=sketch_id,
                curve_ids=[hole["curve"]["id"]],
                center_x=0, center_y=0,
                count=6
            )

            # Create partial pattern (180 degrees, 4 instances)
            result = await sketch_circular_pattern(
                sketch_id=sketch_id,
                curve_ids=[hole["curve"]["id"]],
                count=4,
                total_angle=180
            )
        """
        logger.info(
            "sketch_circular_pattern called",
            sketch_id=sketch_id,
            curve_count=len(curve_ids),
            center_x=center_x,
            center_y=center_y,
            count=count,
            total_angle=total_angle,
        )
        async with FusionClient() as client:
            return await client.sketch_circular_pattern(
                sketch_id=sketch_id,
                curve_ids=curve_ids,
                center_x=center_x,
                center_y=center_y,
                count=count,
                total_angle=total_angle,
            )

    @mcp.tool()
    async def sketch_rectangular_pattern(
        sketch_id: str,
        curve_ids: List[str],
        x_count: int,
        y_count: int,
        x_spacing: float,
        y_spacing: float,
    ) -> dict:
        """Create a rectangular pattern of sketch entities.

        Copies the specified curves in a rectangular grid array.
        Commonly used for mounting holes, ventilation patterns, and grid layouts.

        **All dimensions in millimeters (mm).**

        Args:
            sketch_id: ID of the sketch containing the curves.
            curve_ids: List of curve IDs to pattern.
            x_count: Number of columns. Must be >= 1.
            y_count: Number of rows. Must be >= 1.
            x_spacing: Column spacing in mm (horizontal distance between copies).
            y_spacing: Row spacing in mm (vertical distance between copies).

        Returns:
            Dict containing:
            - success: True if pattern succeeded
            - pattern_curves: List of new curve IDs created (excludes original)
            - original_curves: The original curve IDs
            - pattern: Pattern info with type, counts, spacing, total_instances
            - sketch_id: The sketch ID
            - profiles_count: Number of closed profiles

        Example:
            # Create a 4x3 grid of mounting slots
            sketch = await create_sketch(plane="XY")
            sketch_id = sketch["sketch"]["id"]

            # Draw one slot
            slot = await draw_slot(
                sketch_id=sketch_id,
                center_x=0, center_y=0,
                length=15, width=5
            )

            # Create 4x3 pattern with 25mm horizontal and 20mm vertical spacing
            result = await sketch_rectangular_pattern(
                sketch_id=sketch_id,
                curve_ids=slot["curves"],
                x_count=4,
                y_count=3,
                x_spacing=25,
                y_spacing=20
            )
        """
        logger.info(
            "sketch_rectangular_pattern called",
            sketch_id=sketch_id,
            curve_count=len(curve_ids),
            x_count=x_count,
            y_count=y_count,
            x_spacing=x_spacing,
            y_spacing=y_spacing,
        )
        async with FusionClient() as client:
            return await client.sketch_rectangular_pattern(
                sketch_id=sketch_id,
                curve_ids=curve_ids,
                x_count=x_count,
                y_count=y_count,
                x_spacing=x_spacing,
                y_spacing=y_spacing,
            )

    @mcp.tool()
    async def project_geometry(
        sketch_id: str,
        entity_ids: List[str],
        project_type: str = "standard",
    ) -> dict:
        """Project edges or faces from 3D bodies onto a sketch.

        Projects existing 3D geometry onto the sketch plane, creating reference
        curves that can be used for further sketch operations. Useful for creating
        features that reference existing geometry.

        Args:
            sketch_id: ID of the target sketch.
            entity_ids: List of entity IDs to project. Can be:
                       - Edge IDs (e.g., "Body1_edge_0")
                       - Face IDs (e.g., "Body1_face_0")
                       - Body IDs (e.g., "body_0") - projects all edges
            project_type: Type of projection:
                         - "standard": Regular projection (default)
                         - "cut_edges": Project only edges that intersect the
                           sketch plane (silhouette edges)

        Returns:
            Dict containing:
            - success: True if projection succeeded
            - projected_curves: List of new curve IDs created
            - source_entities: The entities that were projected
            - project_type: The projection type used
            - sketch_id: The sketch ID
            - curves_created: Number of curves created

        Example:
            # Create a box, then project its top face edges onto a new sketch
            box = await create_box(width=50, depth=30, height=20)
            body_id = box["body"]["id"]

            # Get body details to find top face
            body = await get_body_by_id(body_id=body_id, include_faces=True)

            # Create a new sketch at Z=25 (above the box)
            sketch = await create_sketch(plane="XY", offset=25)
            sketch_id = sketch["sketch"]["id"]

            # Project the box edges onto the new sketch
            result = await project_geometry(
                sketch_id=sketch_id,
                entity_ids=[body_id]
            )
        """
        logger.info(
            "project_geometry called",
            sketch_id=sketch_id,
            entity_count=len(entity_ids),
            project_type=project_type,
        )
        async with FusionClient() as client:
            return await client.project_geometry(
                sketch_id=sketch_id,
                entity_ids=entity_ids,
                project_type=project_type,
            )

    @mcp.tool()
    async def add_sketch_text(
        sketch_id: str,
        text: str,
        height: float,
        x: float = 0.0,
        y: float = 0.0,
        font_name: Optional[str] = None,
        is_bold: bool = False,
        is_italic: bool = False,
    ) -> dict:
        """Add text to a sketch for engraving or embossing.

        Creates sketch text that generates profiles suitable for extrusion,
        enabling engraved or embossed text on parts. Useful for part numbers,
        logos, labels, and decorative text.

        **All dimensions in millimeters (mm).**

        Args:
            sketch_id: ID of the target sketch.
            text: Text content to add. Cannot be empty.
            height: Text height in mm. Must be positive. This is the height
                   of capital letters.
            x: Text position X coordinate in mm. Default 0. This is the
               left edge of the text.
            y: Text position Y coordinate in mm. Default 0. This is the
               top edge of the text.
            font_name: Optional font name. Uses system default if not specified.
                      Common fonts: "Arial", "Times New Roman", "Courier New"
            is_bold: Make text bold. Default False.
            is_italic: Make text italic. Default False.

        Returns:
            Dict containing:
            - success: True if text was created
            - text: Text info with content, position, height, font settings
            - curves: List of curve IDs created (text outlines)
            - sketch_id: The sketch ID
            - profiles_count: Number of closed profiles (for extrusion)

        Example:
            # Add a part number to a sketch for engraving
            sketch = await create_sketch(plane="XY")
            sketch_id = sketch["sketch"]["id"]

            result = await add_sketch_text(
                sketch_id=sketch_id,
                text="PART-001",
                height=5,
                x=10, y=10,
                font_name="Arial",
                is_bold=True
            )

            # Extrude the text as a cut for engraving
            await extrude(
                sketch_id=sketch_id,
                distance=0.5,
                direction="negative",
                operation="cut"
            )
        """
        logger.info(
            "add_sketch_text called",
            sketch_id=sketch_id,
            text=text,
            height=height,
            x=x,
            y=y,
            font_name=font_name,
            is_bold=is_bold,
            is_italic=is_italic,
        )
        async with FusionClient() as client:
            return await client.add_sketch_text(
                sketch_id=sketch_id,
                text=text,
                x=x,
                y=y,
                height=height,
                font_name=font_name,
                is_bold=is_bold,
                is_italic=is_italic,
            )

    # --- Phase 7c: Sketch Constraints & Dimensions ---

    @mcp.tool()
    async def add_constraint_horizontal(
        sketch_id: str,
        curve_id: str,
    ) -> dict:
        """Add a horizontal constraint to a line.

        Constrains a line to be horizontal (parallel to the sketch X axis).
        The line will maintain its length but rotate to become horizontal.

        **Use for:** Ensuring edges are aligned with the X axis, creating
        level surfaces, maintaining horizontal alignment.

        Args:
            sketch_id: ID of the sketch containing the line.
            curve_id: ID of the line to constrain. Must be a SketchLine
                     (not a circle or arc).

        Returns:
            Dict containing:
            - success: True if constraint was added
            - constraint: Constraint info with id, type, curve_id
            - sketch_id: The sketch ID
            - sketch_status: Current constraint status including
              is_fully_constrained, under_constrained_count

        Example:
            # Draw a rectangle and make the top edge horizontal
            sketch = await create_sketch(plane="XY")
            sketch_id = sketch["sketch"]["id"]

            rect = await draw_rectangle(sketch_id=sketch_id, x1=0, y1=0, x2=50, y2=30)

            # Get line IDs from rectangle (4 lines)
            # Constrain top edge to be horizontal
            result = await add_constraint_horizontal(
                sketch_id=sketch_id,
                curve_id=rect["curves"][0]  # Top edge
            )
        """
        logger.info(
            "add_constraint_horizontal called",
            sketch_id=sketch_id,
            curve_id=curve_id,
        )
        async with FusionClient() as client:
            return await client.add_constraint_horizontal(
                sketch_id=sketch_id,
                curve_id=curve_id,
            )

    @mcp.tool()
    async def add_constraint_vertical(
        sketch_id: str,
        curve_id: str,
    ) -> dict:
        """Add a vertical constraint to a line.

        Constrains a line to be vertical (parallel to the sketch Y axis).
        The line will maintain its length but rotate to become vertical.

        **Use for:** Ensuring edges are aligned with the Y axis, creating
        upright surfaces, maintaining vertical alignment.

        Args:
            sketch_id: ID of the sketch containing the line.
            curve_id: ID of the line to constrain. Must be a SketchLine
                     (not a circle or arc).

        Returns:
            Dict containing:
            - success: True if constraint was added
            - constraint: Constraint info with id, type, curve_id
            - sketch_id: The sketch ID
            - sketch_status: Current constraint status

        Example:
            # Draw a rectangle and make a side edge vertical
            sketch = await create_sketch(plane="XY")
            sketch_id = sketch["sketch"]["id"]

            rect = await draw_rectangle(sketch_id=sketch_id, x1=0, y1=0, x2=50, y2=30)

            # Constrain left edge to be vertical
            result = await add_constraint_vertical(
                sketch_id=sketch_id,
                curve_id=rect["curves"][1]  # Left edge
            )
        """
        logger.info(
            "add_constraint_vertical called",
            sketch_id=sketch_id,
            curve_id=curve_id,
        )
        async with FusionClient() as client:
            return await client.add_constraint_vertical(
                sketch_id=sketch_id,
                curve_id=curve_id,
            )

    @mcp.tool()
    async def add_constraint_coincident(
        sketch_id: str,
        entity1_id: str,
        entity2_id: str,
    ) -> dict:
        """Add a coincident constraint between two entities.

        Makes two points occupy the same location, or places a point on a curve.
        This is fundamental for connecting sketch geometry.

        **Use for:** Connecting line endpoints, placing points on curves,
        ensuring geometry meets at specific locations.

        Args:
            sketch_id: ID of the sketch containing the entities.
            entity1_id: ID of the first entity (point or curve endpoint).
            entity2_id: ID of the second entity (point or curve).

        Returns:
            Dict containing:
            - success: True if constraint was added
            - constraint: Constraint info with id, type, entity IDs
            - sketch_id: The sketch ID
            - sketch_status: Current constraint status

        Example:
            # Connect two lines at their endpoints
            sketch = await create_sketch(plane="XY")
            sketch_id = sketch["sketch"]["id"]

            line1 = await draw_line(sketch_id=sketch_id, start_x=0, start_y=0, end_x=50, end_y=0)
            line2 = await draw_line(sketch_id=sketch_id, start_x=50, start_y=0, end_x=50, end_y=30)

            # Make endpoint of line1 coincident with startpoint of line2
            # (The lines already share this point from drawing)
        """
        logger.info(
            "add_constraint_coincident called",
            sketch_id=sketch_id,
            entity1_id=entity1_id,
            entity2_id=entity2_id,
        )
        async with FusionClient() as client:
            return await client.add_constraint_coincident(
                sketch_id=sketch_id,
                entity1_id=entity1_id,
                entity2_id=entity2_id,
            )

    @mcp.tool()
    async def add_constraint_perpendicular(
        sketch_id: str,
        curve1_id: str,
        curve2_id: str,
    ) -> dict:
        """Add a perpendicular constraint between two lines.

        Makes two lines perpendicular (at exactly 90 degrees to each other).
        One or both lines will rotate to achieve perpendicularity.

        **Use for:** Creating right angles, L-shaped brackets, rectangular
        features, ensuring orthogonal alignment.

        Args:
            sketch_id: ID of the sketch containing the lines.
            curve1_id: ID of the first line.
            curve2_id: ID of the second line.

        Returns:
            Dict containing:
            - success: True if constraint was added
            - constraint: Constraint info with id, type, curve IDs
            - sketch_id: The sketch ID
            - sketch_status: Current constraint status

        Example:
            # Create two lines and make them perpendicular
            sketch = await create_sketch(plane="XY")
            sketch_id = sketch["sketch"]["id"]

            line1 = await draw_line(sketch_id=sketch_id, start_x=0, start_y=0, end_x=50, end_y=0)
            line2 = await draw_line(sketch_id=sketch_id, start_x=0, start_y=0, end_x=0, end_y=30)

            result = await add_constraint_perpendicular(
                sketch_id=sketch_id,
                curve1_id=line1["curve"]["id"],
                curve2_id=line2["curve"]["id"]
            )
        """
        logger.info(
            "add_constraint_perpendicular called",
            sketch_id=sketch_id,
            curve1_id=curve1_id,
            curve2_id=curve2_id,
        )
        async with FusionClient() as client:
            return await client.add_constraint_perpendicular(
                sketch_id=sketch_id,
                curve1_id=curve1_id,
                curve2_id=curve2_id,
            )

    @mcp.tool()
    async def add_constraint_parallel(
        sketch_id: str,
        curve1_id: str,
        curve2_id: str,
    ) -> dict:
        """Add a parallel constraint between two lines.

        Makes two lines parallel (same direction). One or both lines will
        rotate to achieve parallelism while maintaining their lengths.

        **Use for:** Creating parallel edges, maintaining consistent spacing,
        ensuring features remain aligned in the same direction.

        Args:
            sketch_id: ID of the sketch containing the lines.
            curve1_id: ID of the first line.
            curve2_id: ID of the second line.

        Returns:
            Dict containing:
            - success: True if constraint was added
            - constraint: Constraint info with id, type, curve IDs
            - sketch_id: The sketch ID
            - sketch_status: Current constraint status

        Example:
            # Create two parallel lines (like rails)
            sketch = await create_sketch(plane="XY")
            sketch_id = sketch["sketch"]["id"]

            line1 = await draw_line(sketch_id=sketch_id, start_x=0, start_y=0, end_x=100, end_y=0)
            line2 = await draw_line(sketch_id=sketch_id, start_x=0, start_y=20, end_x=100, end_y=20)

            result = await add_constraint_parallel(
                sketch_id=sketch_id,
                curve1_id=line1["curve"]["id"],
                curve2_id=line2["curve"]["id"]
            )
        """
        logger.info(
            "add_constraint_parallel called",
            sketch_id=sketch_id,
            curve1_id=curve1_id,
            curve2_id=curve2_id,
        )
        async with FusionClient() as client:
            return await client.add_constraint_parallel(
                sketch_id=sketch_id,
                curve1_id=curve1_id,
                curve2_id=curve2_id,
            )

    @mcp.tool()
    async def add_constraint_tangent(
        sketch_id: str,
        curve1_id: str,
        curve2_id: str,
    ) -> dict:
        """Add a tangent constraint between two curves.

        Makes two curves tangent (smooth transition) at their connection point.
        Commonly used for smooth transitions between lines and arcs.

        **Use for:** Creating smooth curves, filleted corners, cam profiles,
        transitions between straight and curved segments.

        Args:
            sketch_id: ID of the sketch containing the curves.
            curve1_id: ID of the first curve (line, arc, or circle).
            curve2_id: ID of the second curve (line, arc, or circle).

        Returns:
            Dict containing:
            - success: True if constraint was added
            - constraint: Constraint info with id, type, curve IDs
            - sketch_id: The sketch ID
            - sketch_status: Current constraint status

        Example:
            # Create a line tangent to a circle
            sketch = await create_sketch(plane="XY")
            sketch_id = sketch["sketch"]["id"]

            circle = await draw_circle(sketch_id=sketch_id, center_x=0, center_y=0, radius=20)
            line = await draw_line(sketch_id=sketch_id, start_x=20, start_y=0, end_x=50, end_y=10)

            result = await add_constraint_tangent(
                sketch_id=sketch_id,
                curve1_id=circle["curve"]["id"],
                curve2_id=line["curve"]["id"]
            )
        """
        logger.info(
            "add_constraint_tangent called",
            sketch_id=sketch_id,
            curve1_id=curve1_id,
            curve2_id=curve2_id,
        )
        async with FusionClient() as client:
            return await client.add_constraint_tangent(
                sketch_id=sketch_id,
                curve1_id=curve1_id,
                curve2_id=curve2_id,
            )

    @mcp.tool()
    async def add_constraint_equal(
        sketch_id: str,
        curve1_id: str,
        curve2_id: str,
    ) -> dict:
        """Add an equal constraint between two curves.

        Makes two curves equal in size (same length for lines, same radius
        for circles/arcs). Changing one will change the other.

        **Use for:** Ensuring symmetric features, matching hole sizes,
        creating uniform spacing, maintaining equal dimensions.

        Args:
            sketch_id: ID of the sketch containing the curves.
            curve1_id: ID of the first curve.
            curve2_id: ID of the second curve. Must be same type as curve1.

        Returns:
            Dict containing:
            - success: True if constraint was added
            - constraint: Constraint info with id, type, curve IDs
            - sketch_id: The sketch ID
            - sketch_status: Current constraint status

        Example:
            # Create two circles with equal radius
            sketch = await create_sketch(plane="XY")
            sketch_id = sketch["sketch"]["id"]

            circle1 = await draw_circle(sketch_id=sketch_id, center_x=-30, center_y=0, radius=15)
            circle2 = await draw_circle(sketch_id=sketch_id, center_x=30, center_y=0, radius=10)

            # Make circles equal - circle2 will resize to match circle1
            result = await add_constraint_equal(
                sketch_id=sketch_id,
                curve1_id=circle1["curve"]["id"],
                curve2_id=circle2["curve"]["id"]
            )
        """
        logger.info(
            "add_constraint_equal called",
            sketch_id=sketch_id,
            curve1_id=curve1_id,
            curve2_id=curve2_id,
        )
        async with FusionClient() as client:
            return await client.add_constraint_equal(
                sketch_id=sketch_id,
                curve1_id=curve1_id,
                curve2_id=curve2_id,
            )

    @mcp.tool()
    async def add_constraint_concentric(
        sketch_id: str,
        curve1_id: str,
        curve2_id: str,
    ) -> dict:
        """Add a concentric constraint between two circles or arcs.

        Makes two circles or arcs share the same center point.
        Useful for creating rings, washers, and nested circular features.

        **Use for:** Creating concentric circles, rings, washers, nested
        holes, features that must share a common center.

        Args:
            sketch_id: ID of the sketch containing the curves.
            curve1_id: ID of the first circle or arc.
            curve2_id: ID of the second circle or arc.

        Returns:
            Dict containing:
            - success: True if constraint was added
            - constraint: Constraint info with id, type, curve IDs
            - sketch_id: The sketch ID
            - sketch_status: Current constraint status

        Example:
            # Create concentric circles (like a washer)
            sketch = await create_sketch(plane="XY")
            sketch_id = sketch["sketch"]["id"]

            outer = await draw_circle(sketch_id=sketch_id, center_x=0, center_y=0, radius=20)
            inner = await draw_circle(sketch_id=sketch_id, center_x=5, center_y=5, radius=8)

            # Make circles concentric - inner will move to share center
            result = await add_constraint_concentric(
                sketch_id=sketch_id,
                curve1_id=outer["curve"]["id"],
                curve2_id=inner["curve"]["id"]
            )
        """
        logger.info(
            "add_constraint_concentric called",
            sketch_id=sketch_id,
            curve1_id=curve1_id,
            curve2_id=curve2_id,
        )
        async with FusionClient() as client:
            return await client.add_constraint_concentric(
                sketch_id=sketch_id,
                curve1_id=curve1_id,
                curve2_id=curve2_id,
            )

    @mcp.tool()
    async def add_constraint_fix(
        sketch_id: str,
        entity_id: str,
    ) -> dict:
        """Fix a point or curve in place.

        Fixes the entity at its current position so it cannot move during
        constraint solving. Useful for anchoring geometry.

        **Use for:** Anchoring reference points, preventing geometry from
        moving, establishing fixed positions for subsequent constraints.

        Args:
            sketch_id: ID of the sketch containing the entity.
            entity_id: ID of the point or curve to fix.

        Returns:
            Dict containing:
            - success: True if constraint was added
            - constraint: Constraint info with id, type, entity_id
            - sketch_id: The sketch ID
            - sketch_status: Current constraint status

        Example:
            # Fix the origin point of a rectangle
            sketch = await create_sketch(plane="XY")
            sketch_id = sketch["sketch"]["id"]

            rect = await draw_rectangle(sketch_id=sketch_id, x1=0, y1=0, x2=50, y2=30)

            # Fix one corner of the rectangle
            result = await add_constraint_fix(
                sketch_id=sketch_id,
                entity_id=rect["curves"][0]  # Fix first line
            )
        """
        logger.info(
            "add_constraint_fix called",
            sketch_id=sketch_id,
            entity_id=entity_id,
        )
        async with FusionClient() as client:
            return await client.add_constraint_fix(
                sketch_id=sketch_id,
                entity_id=entity_id,
            )

    @mcp.tool()
    async def add_dimension(
        sketch_id: str,
        dimension_type: str,
        entity1_id: str,
        value: float,
        entity2_id: Optional[str] = None,
        text_position_x: Optional[float] = None,
        text_position_y: Optional[float] = None,
    ) -> dict:
        """Add a dimensional constraint to a sketch.

        Adds a driving dimension that controls geometry size. Changing the
        dimension value will update the geometry. This is the primary way
        to create parametric, precisely-sized sketches.

        **Values in mm for distance/radius/diameter, degrees for angle.**

        Args:
            sketch_id: ID of the sketch.
            dimension_type: Type of dimension:
                - "distance": Distance between two entities or line length
                - "radius": Radius of a circle or arc
                - "diameter": Diameter of a circle or arc
                - "angle": Angle between two lines
            entity1_id: ID of the first entity.
            value: Dimension value in mm (distance/radius/diameter) or
                  degrees (angle). Must be positive for non-angle types.
            entity2_id: ID of second entity. Required for:
                       - distance between two separate entities
                       - angle between two lines
                       Not needed for:
                       - line length (uses line endpoints)
                       - radius/diameter (uses circle/arc)
            text_position_x: Optional X position for dimension text in mm.
            text_position_y: Optional Y position for dimension text in mm.

        Returns:
            Dict containing:
            - success: True if dimension was added
            - dimension: Dimension info with id, type, entity IDs,
              requested_value, actual_value, parameter_name
            - sketch_id: The sketch ID
            - sketch_status: Current constraint status

        Example:
            # Add dimensions to a rectangle to make it exactly 50x30mm
            sketch = await create_sketch(plane="XY")
            sketch_id = sketch["sketch"]["id"]

            rect = await draw_rectangle(sketch_id=sketch_id, x1=0, y1=0, x2=40, y2=25)
            # rect["curves"] contains 4 line IDs

            # Add horizontal dimension (width = 50mm)
            await add_dimension(
                sketch_id=sketch_id,
                dimension_type="distance",
                entity1_id=rect["curves"][0],  # Top line
                value=50
            )

            # Add vertical dimension (height = 30mm)
            await add_dimension(
                sketch_id=sketch_id,
                dimension_type="distance",
                entity1_id=rect["curves"][1],  # Left line
                value=30
            )

            # Add radius dimension to a circle
            circle = await draw_circle(sketch_id=sketch_id, center_x=25, center_y=15, radius=8)
            await add_dimension(
                sketch_id=sketch_id,
                dimension_type="diameter",
                entity1_id=circle["curve"]["id"],
                value=20  # 20mm diameter (10mm radius)
            )

            # Add angle dimension between two lines
            await add_dimension(
                sketch_id=sketch_id,
                dimension_type="angle",
                entity1_id=rect["curves"][0],
                entity2_id=rect["curves"][1],
                value=90  # 90 degrees
            )
        """
        logger.info(
            "add_dimension called",
            sketch_id=sketch_id,
            dimension_type=dimension_type,
            entity1_id=entity1_id,
            value=value,
            entity2_id=entity2_id,
        )
        async with FusionClient() as client:
            return await client.add_dimension(
                sketch_id=sketch_id,
                dimension_type=dimension_type,
                entity1_id=entity1_id,
                value=value,
                entity2_id=entity2_id,
                text_position_x=text_position_x,
                text_position_y=text_position_y,
            )

    logger.info("Creation tools registered")
