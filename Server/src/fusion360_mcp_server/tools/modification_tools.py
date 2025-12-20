"""Modification tools for Fusion 360 MCP Server.

These tools enable AI to modify existing geometry in Fusion 360 designs -
move, rotate, modify parameters, delete entities, and edit sketches.

All dimensions are in millimeters (mm).

IMPORTANT: Move and rotate operations use defineAsTranslate/defineAsRotate
which preserve parametric relationships in the design.
"""

from typing import Dict, Any
from mcp.server.fastmcp import FastMCP

from ..services.fusion_client import FusionClient
from ..logging import get_logger

logger = get_logger(__name__)


def register_modification_tools(mcp: FastMCP) -> None:
    """Register all modification tools with the MCP server.

    Args:
        mcp: FastMCP server instance
    """

    # --- Move/Rotate Tools ---

    @mcp.tool()
    async def move_body(
        body_id: str,
        x: float = 0.0,
        y: float = 0.0,
        z: float = 0.0,
    ) -> dict:
        """Move a body by translation.

        Translates a body by the specified offset in X, Y, Z directions.
        This creates a Move feature in the timeline and **preserves parametric
        relationships** using defineAsTranslate internally.

        **All dimensions are in millimeters (mm).**

        Args:
            body_id: ID of the body to move. Get this from get_bodies() or
                     the body_id returned when creating geometry.
            x: Translation in X direction in mm. Default 0.
            y: Translation in Y direction in mm. Default 0.
            z: Translation in Z direction in mm. Default 0.
               At least one of x, y, z must be non-zero.

        Returns:
            Dict containing:
            - success: True if move succeeded
            - feature: Move feature info (id, type, translation vector)
            - new_position: Updated bounding box of the body

        Example:
            # Move a body 10mm in X direction
            result = await move_body(body_id="base_plate", x=10)

            # Move a body diagonally
            result = await move_body(body_id="bracket", x=50, y=25, z=10)

        Note:
            This operation is parametric - changing the source body's
            dimensions will update the moved result automatically.
        """
        logger.info(
            "move_body called",
            body_id=body_id,
            x=x,
            y=y,
            z=z,
        )
        async with FusionClient() as client:
            return await client.move_body(
                body_id=body_id,
                x=x,
                y=y,
                z=z,
            )

    @mcp.tool()
    async def rotate_body(
        body_id: str,
        axis: str,
        angle: float,
        origin_x: float = 0.0,
        origin_y: float = 0.0,
        origin_z: float = 0.0,
    ) -> dict:
        """Rotate a body around an axis.

        Rotates a body by the specified angle around an axis passing through
        the origin point. This creates a Move feature in the timeline and
        **preserves parametric relationships** using defineAsRotate internally.

        **Angle is in degrees, positions are in millimeters (mm).**

        Args:
            body_id: ID of the body to rotate. Get this from get_bodies() or
                     the body_id returned when creating geometry.
            axis: Axis to rotate around. Options: "X", "Y", "Z".
            angle: Rotation angle in degrees. Positive = counter-clockwise
                   when looking down the axis toward the origin.
            origin_x: X coordinate of rotation axis origin in mm. Default 0.
            origin_y: Y coordinate of rotation axis origin in mm. Default 0.
            origin_z: Z coordinate of rotation axis origin in mm. Default 0.

        Returns:
            Dict containing:
            - success: True if rotation succeeded
            - feature: Move feature info (id, type, rotation details)
            - new_position: Updated bounding box of the body

        Example:
            # Rotate a body 45 degrees around Z axis
            result = await rotate_body(body_id="bracket", axis="Z", angle=45)

            # Rotate around Z axis at point (50, 50, 0)
            result = await rotate_body(
                body_id="handle",
                axis="Z",
                angle=90,
                origin_x=50,
                origin_y=50
            )

        Note:
            This operation is parametric - changing the source body's
            dimensions will update the rotated result automatically.
        """
        logger.info(
            "rotate_body called",
            body_id=body_id,
            axis=axis,
            angle=angle,
            origin_x=origin_x,
            origin_y=origin_y,
            origin_z=origin_z,
        )
        async with FusionClient() as client:
            return await client.rotate_body(
                body_id=body_id,
                axis=axis,
                angle=angle,
                origin_x=origin_x,
                origin_y=origin_y,
                origin_z=origin_z,
            )

    # --- Feature Modification Tools ---

    @mcp.tool()
    async def modify_feature(
        feature_id: str,
        parameters: Dict[str, Any],
    ) -> dict:
        """Modify feature parameters.

        Changes the parameters of an existing feature like extrusion distance,
        fillet radius, chamfer distance, or revolve angle. The design updates
        automatically to reflect the new values.

        **Dimension values are in millimeters (mm), angles in degrees.**

        Args:
            feature_id: ID of the feature to modify. Get this from get_timeline()
                        or from the feature_id returned when creating features.
            parameters: Dict of parameter names to new values.
                        Supported parameters by feature type:
                        - ExtrudeFeature: {"distance": float} - extrusion distance in mm
                        - FilletFeature: {"radius": float} - fillet radius in mm
                        - ChamferFeature: {"distance": float} - chamfer distance in mm
                        - RevolveFeature: {"angle": float} - revolution angle in degrees

        Returns:
            Dict containing:
            - success: True if modification succeeded
            - feature: Feature info (id, type)
            - changes: Dict with old and new values for each modified parameter

        Example:
            # Change extrusion distance to 20mm
            result = await modify_feature(
                feature_id="Extrude1",
                parameters={"distance": 20}
            )

            # Change fillet radius to 5mm
            result = await modify_feature(
                feature_id="Fillet1",
                parameters={"radius": 5}
            )

        Note:
            This is a powerful way to iterate on designs - change dimensions
            without recreating features. The timeline history is preserved.
        """
        logger.info(
            "modify_feature called",
            feature_id=feature_id,
            parameters=parameters,
        )
        async with FusionClient() as client:
            return await client.modify_feature(
                feature_id=feature_id,
                parameters=parameters,
            )

    @mcp.tool()
    async def update_parameter(
        name: str,
        expression: str,
    ) -> dict:
        """Update a parameter value.

        Changes a design parameter to a new value. Parameters can be user-defined
        or Fusion 360 model parameters. Use expressions for dynamic values.

        **Supports unit expressions like "50 mm" or math like "d1 * 2".**

        Args:
            name: Parameter name. Get available names from get_parameters().
            expression: New value as an expression string.
                        Examples:
                        - "50 mm" - explicit value with unit
                        - "25.4 in" - value in inches
                        - "d1 * 2" - expression referencing another parameter
                        - "width / 2" - expression with parameter reference

        Returns:
            Dict containing:
            - success: True if update succeeded
            - parameter: Parameter info (name, unit)
            - changes: Dict with old and new expression and value

        Example:
            # Set a parameter to 50mm
            result = await update_parameter(name="height", expression="50 mm")

            # Set using an expression
            result = await update_parameter(name="depth", expression="width / 2")

        Note:
            This is the recommended way to change design dimensions because
            it updates all features that depend on the parameter.
        """
        logger.info(
            "update_parameter called",
            name=name,
            expression=expression,
        )
        async with FusionClient() as client:
            return await client.update_parameter(
                name=name,
                expression=expression,
            )

    # --- Delete Tools ---

    @mcp.tool()
    async def delete_body(
        body_id: str,
    ) -> dict:
        """Delete a body from the design.

        Removes a body using a Remove feature, which preserves timeline history.
        The body will no longer appear in the design, but the removal can be
        undone or rolled back in the timeline.

        Args:
            body_id: ID of the body to delete. Get this from get_bodies().

        Returns:
            Dict containing:
            - success: True if deletion succeeded
            - deleted: Info about the deleted body (id, name, type)
            - feature: The Remove feature that was created

        Example:
            # Delete a body by ID
            result = await delete_body(body_id="old_part")

            # Delete a body created earlier
            result = await delete_body(body_id=box_result["body"]["id"])

        Note:
            This creates a Remove feature in the timeline rather than
            completely erasing the body. Use delete_feature to remove
            features from the timeline entirely.
        """
        logger.info(
            "delete_body called",
            body_id=body_id,
        )
        async with FusionClient() as client:
            return await client.delete_body(body_id=body_id)

    @mcp.tool()
    async def delete_feature(
        feature_id: str,
    ) -> dict:
        """Delete a feature from the timeline.

        Removes a feature from the design timeline. This is a more permanent
        operation than delete_body - the feature is completely removed.

        **Warning:** Dependent features may be affected or deleted as well.

        Args:
            feature_id: ID of the feature to delete. Get this from get_timeline().

        Returns:
            Dict containing:
            - success: True if deletion succeeded
            - deleted: Info about the deleted feature (id, name, type)
            - affected_features: List of features that were affected (if any)
            - warning: Message about dependent features (if applicable)

        Example:
            # Delete a feature by ID
            result = await delete_feature(feature_id="Fillet1")

            # Delete the extrusion that created a body
            result = await delete_feature(feature_id="Extrude1")

        Note:
            Features later in the timeline that depend on this feature
            may fail or be deleted. Check affected_features in the response.
        """
        logger.info(
            "delete_feature called",
            feature_id=feature_id,
        )
        async with FusionClient() as client:
            return await client.delete_feature(feature_id=feature_id)

    # --- Sketch Edit Tools ---

    @mcp.tool()
    async def edit_sketch(
        sketch_id: str,
        curve_id: str,
        properties: Dict[str, Any],
    ) -> dict:
        """Edit a sketch curve.

        Modifies properties of an existing sketch curve like line endpoints,
        circle center/radius, or arc parameters. The design updates automatically.

        **All positions and dimensions are in millimeters (mm).**

        Args:
            sketch_id: ID of the sketch containing the curve.
                       Get this from get_sketches().
            curve_id: ID of the curve to modify. Format is typically
                      "{sketch_id}_{type}_{index}" like "Sketch1_line_0".
                      Get available curves from get_sketch_by_id() with
                      include_curves=True.
            properties: Dict of properties to modify. Available properties
                        depend on curve type:
                        - Lines: {"start_x", "start_y", "end_x", "end_y"}
                        - Circles: {"center_x", "center_y", "radius"}
                        - Arcs: {"center_x", "center_y"}

        Returns:
            Dict containing:
            - success: True if edit succeeded
            - sketch_id: ID of the modified sketch
            - curve_id: ID of the modified curve
            - curve_type: Type of the curve (SketchLine, SketchCircle, etc.)
            - changes: Dict with old and new values for each modified property

        Example:
            # Move a line endpoint
            result = await edit_sketch(
                sketch_id="Sketch1",
                curve_id="Sketch1_line_0",
                properties={"end_x": 100, "end_y": 50}
            )

            # Change a circle's radius
            result = await edit_sketch(
                sketch_id="profile_sketch",
                curve_id="profile_sketch_circle_0",
                properties={"radius": 25}
            )

        Note:
            Use get_sketch_by_id(sketch_id, include_curves=True) to see
            all available curves and their current properties before editing.
        """
        logger.info(
            "edit_sketch called",
            sketch_id=sketch_id,
            curve_id=curve_id,
            properties=properties,
        )
        async with FusionClient() as client:
            return await client.edit_sketch(
                sketch_id=sketch_id,
                curve_id=curve_id,
                properties=properties,
            )

    # --- MODIFY Menu Tools ---

    @mcp.tool()
    async def combine(
        target_body_id: str,
        tool_body_ids: list[str],
        operation: str = "join",
        keep_tools: bool = False,
    ) -> dict:
        """Combine multiple bodies using boolean operations.

        Combines bodies using Join (add material), Cut (subtract material),
        or Intersect (keep only overlapping volume).

        **Use this when**: Merging separate bodies, creating cutouts,
        or finding intersections between overlapping geometry.

        Args:
            target_body_id: ID of the body to modify (receives the result).
                           Get from get_bodies() or body creation results.
            tool_body_ids: List of body IDs to combine with the target.
                          These are the "tools" that modify the target.
            operation: Boolean operation type:
                - "join": Add tool bodies to target (union)
                - "cut": Subtract tool bodies from target (difference)
                - "intersect": Keep only overlapping volume
            keep_tools: If True, keep tool bodies after operation.
                       Default False (tool bodies are consumed).

        Returns:
            Dict containing:
            - success: True if combine succeeded
            - feature: Feature info with id and type
            - combine: Operation details (target, tools, operation, keep_tools)
            - body: Resulting body info

        Example:
            # Create two overlapping boxes
            box1 = await create_box(width=50, depth=50, height=50)
            box2 = await create_box(width=30, depth=30, height=80, x=25)

            # Join them into one body
            result = await combine(
                target_body_id=box1["body"]["id"],
                tool_body_ids=[box2["body"]["id"]],
                operation="join"
            )

            # Cut a cylinder from a box
            box = await create_box(width=100, depth=100, height=20)
            cyl = await create_cylinder(radius=15, height=30)

            result = await combine(
                target_body_id=box["body"]["id"],
                tool_body_ids=[cyl["body"]["id"]],
                operation="cut"
            )
        """
        logger.info(
            "combine called",
            target_body_id=target_body_id,
            tool_body_ids=tool_body_ids,
            operation=operation,
            keep_tools=keep_tools,
        )
        async with FusionClient() as client:
            return await client.combine(
                target_body_id=target_body_id,
                tool_body_ids=tool_body_ids,
                operation=operation,
                keep_tools=keep_tools,
            )

    @mcp.tool()
    async def split_body(
        body_id: str,
        splitting_tool: str,
        extend_splitting_tool: bool = True,
    ) -> dict:
        """Split a body into multiple bodies using a plane or face.

        Divides a single body into two or more separate bodies using
        a splitting surface. The original body is replaced by the
        resulting body pieces.

        **Use this when**: Cutting parts in half, creating sections,
        or dividing geometry for separate manufacturing.

        Args:
            body_id: ID of the body to split. Get from get_bodies().
            splitting_tool: The surface to split with. Options:
                - "XY", "YZ", "XZ": Standard construction planes
                - face_id: A planar face from another body
                - construction plane name or ID
            extend_splitting_tool: If True, extend the splitting surface
                to ensure complete split. Default True.

        Returns:
            Dict containing:
            - success: True if split succeeded
            - feature: Feature info with id and type
            - split: Operation details (source body, tool, bodies created)
            - bodies: List of resulting body info

        Example:
            # Split a box in half using the XY plane
            box = await create_box(width=100, depth=50, height=40, z=-20)

            result = await split_body(
                body_id=box["body"]["id"],
                splitting_tool="XY"
            )
            # Creates 2 bodies: one above and one below XY plane

            # Split using a custom construction plane
            plane = await create_offset_plane(base_plane="XY", offset=10)
            result = await split_body(
                body_id="Body1",
                splitting_tool=plane["plane"]["id"]
            )
        """
        logger.info(
            "split_body called",
            body_id=body_id,
            splitting_tool=splitting_tool,
            extend_splitting_tool=extend_splitting_tool,
        )
        async with FusionClient() as client:
            return await client.split_body(
                body_id=body_id,
                splitting_tool=splitting_tool,
                extend_splitting_tool=extend_splitting_tool,
            )

    @mcp.tool()
    async def shell(
        body_id: str,
        face_ids: list[str],
        thickness: float,
        direction: str = "inside",
    ) -> dict:
        """Create a hollow shell from a solid body.

        Removes selected faces from a solid body and adds uniform wall
        thickness to create a hollow part. The removed faces become
        openings in the shell.

        **Use this when**: Creating enclosures, housings, containers,
        or any hollow parts with uniform wall thickness.

        **All dimensions in millimeters (mm).**

        Args:
            body_id: ID of the solid body to shell.
            face_ids: List of face IDs to remove (become openings).
                     Get face IDs from get_body_by_id with include_faces=True.
            thickness: Wall thickness in mm. Must be positive.
            direction: Direction to add material:
                - "inside": Shell inward (default, most common)
                - "outside": Shell outward

        Returns:
            Dict containing:
            - success: True if shell succeeded
            - feature: Feature info with id and type
            - shell: Operation details (body, removed faces, thickness)
            - body: Resulting body info

        Example:
            # Create a hollow box (remove top face)
            box = await create_box(width=100, depth=80, height=50)
            body = await get_body_by_id(
                body_id=box["body"]["id"],
                include_faces=True
            )
            # Find the top face (usually the one with max Z)
            top_face_id = body["faces"][0]["id"]  # Identify correct face

            result = await shell(
                body_id=box["body"]["id"],
                face_ids=[top_face_id],
                thickness=3  # 3mm walls
            )

            # Shell outward for thin-walled containers
            result = await shell(
                body_id="Body1",
                face_ids=["Body1_face_0"],
                thickness=1.5,
                direction="outside"
            )
        """
        logger.info(
            "shell called",
            body_id=body_id,
            face_ids=face_ids,
            thickness=thickness,
            direction=direction,
        )
        async with FusionClient() as client:
            return await client.shell(
                body_id=body_id,
                face_ids=face_ids,
                thickness=thickness,
                direction=direction,
            )

    @mcp.tool()
    async def draft(
        face_ids: list[str],
        plane: str,
        angle: float,
        is_tangent_chain: bool = True,
    ) -> dict:
        """Add draft angle to faces for mold release.

        Applies a draft angle to selected faces, tapering them relative
        to a pull direction. Essential for injection molding and casting
        to allow parts to release from molds.

        **Use this when**: Preparing parts for manufacturing via molding,
        casting, or any process requiring draft angles.

        **Angle in degrees (0-90).**

        Args:
            face_ids: List of face IDs to apply draft to.
                     Get from get_body_by_id with include_faces=True.
            plane: Pull direction plane (mold opening direction):
                - "XY", "YZ", "XZ": Standard construction planes
                - face_id: A planar face defining the direction
                - construction plane name or ID
            angle: Draft angle in degrees. Typical values: 1-5 degrees.
                  Must be between 0 and 90.
            is_tangent_chain: If True, automatically include faces that
                             are tangent to selected faces. Default True.

        Returns:
            Dict containing:
            - success: True if draft succeeded
            - feature: Feature info with id and type
            - draft: Operation details (faces, plane, angle)

        Example:
            # Add 3-degree draft to vertical faces of a box
            box = await create_box(width=50, depth=50, height=30)
            body = await get_body_by_id(
                body_id=box["body"]["id"],
                include_faces=True
            )
            # Select the vertical (side) faces
            side_faces = [f["id"] for f in body["faces"]
                         if f["face_type"] == "planar"]

            result = await draft(
                face_ids=side_faces,
                plane="XY",  # Pull direction is Z axis
                angle=3
            )
        """
        logger.info(
            "draft called",
            face_ids=face_ids,
            plane=plane,
            angle=angle,
            is_tangent_chain=is_tangent_chain,
        )
        async with FusionClient() as client:
            return await client.draft(
                face_ids=face_ids,
                plane=plane,
                angle=angle,
                is_tangent_chain=is_tangent_chain,
            )

    @mcp.tool()
    async def scale(
        body_ids: list[str],
        scale_factor: float = 1.0,
        point_x: float = 0.0,
        point_y: float = 0.0,
        point_z: float = 0.0,
        x_scale: float | None = None,
        y_scale: float | None = None,
        z_scale: float | None = None,
    ) -> dict:
        """Scale bodies uniformly or non-uniformly.

        Scales one or more bodies about a point. Supports both uniform
        scaling (same factor in all directions) and non-uniform scaling
        (different factors per axis).

        **Use this when**: Resizing parts, creating scaled variations,
        or adjusting proportions.

        **All positions in millimeters (mm). Scale factors are unitless.**

        Args:
            body_ids: List of body IDs to scale.
            scale_factor: Uniform scale factor. Default 1.0 (no change).
                         Values > 1 enlarge, < 1 shrink.
                         Used when x_scale/y_scale/z_scale not provided.
            point_x: Scale origin X in mm. Default 0.
            point_y: Scale origin Y in mm. Default 0.
            point_z: Scale origin Z in mm. Default 0.
            x_scale: Non-uniform X scale factor. If provided, all three
                    (x_scale, y_scale, z_scale) must be provided.
            y_scale: Non-uniform Y scale factor.
            z_scale: Non-uniform Z scale factor.

        Returns:
            Dict containing:
            - success: True if scale succeeded
            - feature: Feature info with id and type
            - scale: Operation details (origin, factors, is_uniform)
            - bodies: List of scaled body info

        Example:
            # Scale a body to double size
            box = await create_box(width=50, depth=50, height=50)
            result = await scale(
                body_ids=[box["body"]["id"]],
                scale_factor=2.0
            )
            # Body is now 100x100x100mm

            # Non-uniform scale: make taller but narrower
            result = await scale(
                body_ids=["Body1"],
                x_scale=0.5,
                y_scale=0.5,
                z_scale=2.0
            )

            # Scale about a specific point
            result = await scale(
                body_ids=["Body1"],
                scale_factor=1.5,
                point_x=50, point_y=50, point_z=0
            )
        """
        logger.info(
            "scale called",
            body_ids=body_ids,
            scale_factor=scale_factor,
            point_x=point_x,
            point_y=point_y,
            point_z=point_z,
            x_scale=x_scale,
            y_scale=y_scale,
            z_scale=z_scale,
        )
        async with FusionClient() as client:
            return await client.scale(
                body_ids=body_ids,
                scale_factor=scale_factor,
                point_x=point_x,
                point_y=point_y,
                point_z=point_z,
                x_scale=x_scale,
                y_scale=y_scale,
                z_scale=z_scale,
            )

    @mcp.tool()
    async def offset_face(
        face_ids: list[str],
        distance: float,
    ) -> dict:
        """Offset faces to add or remove material.

        Moves selected faces perpendicular to themselves, adding or
        removing material. Similar to Press/Pull in other CAD tools.
        Useful for local modifications without recreating features.

        **Use this when**: Adjusting wall thickness, creating pockets,
        adding bosses, or making local modifications to existing geometry.

        **Distance in millimeters (mm).**

        Args:
            face_ids: List of face IDs to offset.
                     Get from get_body_by_id with include_faces=True.
            distance: Offset distance in mm.
                     Positive = move outward (add material)
                     Negative = move inward (remove material)

        Returns:
            Dict containing:
            - success: True if offset succeeded
            - feature: Feature info with id and type
            - offset: Operation details (faces, distance)

        Example:
            # Add 5mm to the top of a box (make it taller)
            box = await create_box(width=100, depth=100, height=50)
            body = await get_body_by_id(
                body_id=box["body"]["id"],
                include_faces=True
            )
            # Find top face
            top_face_id = body["faces"][0]["id"]

            result = await offset_face(
                face_ids=[top_face_id],
                distance=5  # Add 5mm height
            )

            # Create a shallow pocket by pushing a face inward
            result = await offset_face(
                face_ids=["Body1_face_0"],
                distance=-2  # Remove 2mm
            )
        """
        logger.info(
            "offset_face called",
            face_ids=face_ids,
            distance=distance,
        )
        async with FusionClient() as client:
            return await client.offset_face(
                face_ids=face_ids,
                distance=distance,
            )

    @mcp.tool()
    async def split_face(
        face_ids: list[str],
        splitting_tool: str,
        extend_splitting_tool: bool = True,
    ) -> dict:
        """Split faces using edges or curves.

        Divides selected faces into multiple faces using a splitting
        tool (edge, curve, or sketch). Useful for creating regions
        on a face for different finishes, colors, or operations.

        **Use this when**: Creating split lines for different materials,
        preparing faces for partial operations, or defining regions.

        Args:
            face_ids: List of face IDs to split.
                     Get from get_body_by_id with include_faces=True.
            splitting_tool: Tool to split faces with:
                - edge_id: An edge from another body
                - curve_id: A sketch curve
                - sketch_id: Use all curves from a sketch
            extend_splitting_tool: If True, extend the splitting tool
                to ensure complete split. Default True.

        Returns:
            Dict containing:
            - success: True if split succeeded
            - feature: Feature info with id and type
            - split: Operation details (faces, tool)

        Example:
            # Split a face using a sketch line
            box = await create_box(width=100, depth=100, height=20)
            sketch = await create_sketch(plane="XY", offset=20)
            await draw_line(
                sketch_id=sketch["sketch"]["id"],
                start_x=-60, start_y=0,
                end_x=60, end_y=0
            )

            body = await get_body_by_id(
                body_id=box["body"]["id"],
                include_faces=True
            )
            top_face_id = body["faces"][0]["id"]

            result = await split_face(
                face_ids=[top_face_id],
                splitting_tool=sketch["sketch"]["id"]
            )
            # Top face is now split into two faces
        """
        logger.info(
            "split_face called",
            face_ids=face_ids,
            splitting_tool=splitting_tool,
            extend_splitting_tool=extend_splitting_tool,
        )
        async with FusionClient() as client:
            return await client.split_face(
                face_ids=face_ids,
                splitting_tool=splitting_tool,
                extend_splitting_tool=extend_splitting_tool,
            )
