"""Modification tools for Fusion 360 MCP Server.

These tools enable AI to modify existing geometry in Fusion 360 designs -
move, rotate, modify parameters, delete entities, and edit sketches.

All dimensions are in millimeters (mm).

IMPORTANT: Move and rotate operations use defineAsTranslate/defineAsRotate
which preserve parametric relationships in the design.
"""

from typing import Optional, Dict, Any
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
