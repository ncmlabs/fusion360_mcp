"""Viewport tools for Fusion 360 MCP Server.

These tools enable AI to control the Fusion 360 viewport camera
and capture screenshots for visualization.
"""

from typing import Optional, List
from mcp.server.fastmcp import FastMCP

from ..services.fusion_client import FusionClient
from ..logging import get_logger

logger = get_logger(__name__)


def register_viewport_tools(mcp: FastMCP) -> None:
    """Register all viewport tools with the MCP server.

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool()
    async def take_screenshot(
        file_path: str,
        view: str = "current",
        width: int = 1920,
        height: int = 1080,
    ) -> dict:
        """Capture the current Fusion 360 viewport as a PNG image.

        Use this tool to visualize the current state of the design.
        Screenshots are saved to the specified file path.

        Args:
            file_path: Path to save the image file (required).
            view: View to capture. Options:
                  - "current" (default): Capture current viewport as-is
                  - "front", "back", "top", "bottom", "left", "right": Standard orthographic views
                  - "isometric": Standard 3D isometric view
                  - "trimetric": Alternative 3D view
                  - "home": Default home view
            width: Image width in pixels (default 1920, max 8192)
            height: Image height in pixels (default 1080, max 8192)

        Returns:
            Dict containing:
            - format: "png"
            - dimensions: {width, height}
            - view: View that was captured
            - file_path: Path where image was saved

        Example usage:
            # Save current view to file
            result = take_screenshot(file_path="/path/to/design.png")

            # Save isometric view to file with custom resolution
            result = take_screenshot(
                file_path="/path/to/design.png",
                view="isometric",
                width=2560,
                height=1440
            )
        """
        logger.info(
            "take_screenshot called",
            file_path=file_path,
            view=view,
            width=width,
            height=height,
        )
        async with FusionClient() as client:
            return await client.take_screenshot(
                file_path=file_path,
                view=view,
                width=width,
                height=height,
            )

    @mcp.tool()
    async def set_camera(
        eye_x: float,
        eye_y: float,
        eye_z: float,
        target_x: float = 0.0,
        target_y: float = 0.0,
        target_z: float = 0.0,
        up_x: float = 0.0,
        up_y: float = 0.0,
        up_z: float = 1.0,
        smooth_transition: bool = True,
    ) -> dict:
        """Set the viewport camera position and orientation.

        Positions the camera at the specified eye point, looking toward
        the target point. The up vector defines which direction is "up"
        in the view.

        **All coordinates are in millimeters (mm).**

        Args:
            eye_x: Camera eye X position in mm
            eye_y: Camera eye Y position in mm
            eye_z: Camera eye Z position in mm
            target_x: Camera target (look-at) X position in mm (default 0)
            target_y: Camera target (look-at) Y position in mm (default 0)
            target_z: Camera target (look-at) Z position in mm (default 0)
            up_x: Camera up vector X component (default 0)
            up_y: Camera up vector Y component (default 0)
            up_z: Camera up vector Z component (default 1, meaning Z is up)
            smooth_transition: Animate the camera movement (default True)

        Returns:
            Dict containing:
            - camera: Current camera state after change
              - eye: {x, y, z} in mm
              - target: {x, y, z} in mm
              - up_vector: {x, y, z}
              - view_extents: zoom level
              - is_perspective: True if perspective camera

        Example usage:
            # Position camera 500mm away along Y axis, looking at origin
            result = set_camera(
                eye_x=0, eye_y=-500, eye_z=200,
                target_x=0, target_y=0, target_z=0
            )
        """
        logger.info(
            "set_camera called",
            eye=f"({eye_x}, {eye_y}, {eye_z})",
            target=f"({target_x}, {target_y}, {target_z})",
        )
        async with FusionClient() as client:
            return await client.set_camera(
                eye_x=eye_x,
                eye_y=eye_y,
                eye_z=eye_z,
                target_x=target_x,
                target_y=target_y,
                target_z=target_z,
                up_x=up_x,
                up_y=up_y,
                up_z=up_z,
                smooth_transition=smooth_transition,
            )

    @mcp.tool()
    async def get_camera() -> dict:
        """Get the current viewport camera state.

        Returns the current camera position, orientation, and zoom
        settings for the active viewport.

        Returns:
            Dict containing:
            - camera: Camera state
              - eye: Camera position {x, y, z} in mm
              - target: Look-at point {x, y, z} in mm
              - up_vector: Up direction {x, y, z}
              - view_extents: Current zoom level
              - is_perspective: True if perspective, False if orthographic

        Example response:
            {
                "camera": {
                    "eye": {"x": 0, "y": -500, "z": 200},
                    "target": {"x": 0, "y": 0, "z": 0},
                    "up_vector": {"x": 0, "y": 0, "z": 1},
                    "view_extents": 50.0,
                    "is_perspective": true
                }
            }
        """
        logger.info("get_camera called")
        async with FusionClient() as client:
            return await client.get_camera()

    @mcp.tool()
    async def set_view(
        view: str,
        smooth_transition: bool = True,
    ) -> dict:
        """Set the viewport to a standard named view.

        Quickly orient the camera to common viewing angles for
        design review and documentation. After setting the view,
        the camera is automatically fitted to show all geometry.

        Args:
            view: Named view to set. Options:
                  - "front": Front view (+Y axis toward viewer)
                  - "back": Back view (-Y axis toward viewer)
                  - "top": Top view (looking down from +Z)
                  - "bottom": Bottom view (looking up from -Z)
                  - "left": Left view (looking from -X)
                  - "right": Right view (looking from +X)
                  - "isometric": Standard 3D isometric view
                  - "trimetric": Alternative 3D view
                  - "home": Reset to default home view
            smooth_transition: Animate the view change (default True)

        Returns:
            Dict containing:
            - view: Name of the view that was set
            - camera: Current camera state after change

        Example usage:
            # Set to top view
            result = set_view("top")

            # Set to isometric without animation
            result = set_view("isometric", smooth_transition=False)
        """
        logger.info("set_view called", view=view)
        async with FusionClient() as client:
            return await client.set_view(
                view=view,
                smooth_transition=smooth_transition,
            )

    @mcp.tool()
    async def fit_view(
        entity_ids: Optional[List[str]] = None,
        smooth_transition: bool = True,
    ) -> dict:
        """Fit the viewport to show specific entities or all geometry.

        Adjusts the camera zoom to optimally frame the specified
        entities or all visible geometry in the design.

        Args:
            entity_ids: Optional list of body, component, or occurrence IDs
                       to fit the view to. If not provided, fits to all
                       visible geometry in the design.
            smooth_transition: Animate the zoom change (default True)

        Returns:
            Dict containing:
            - fitted_to: "all" or list of entity IDs that were fitted to
            - camera: Current camera state after fit

        Example usage:
            # Fit to all geometry
            result = fit_view()

            # Fit to specific bodies
            result = fit_view(entity_ids=["Body1", "Body2"])
        """
        logger.info("fit_view called", entity_ids=entity_ids)
        async with FusionClient() as client:
            return await client.fit_view(
                entity_ids=entity_ids,
                smooth_transition=smooth_transition,
            )

    logger.info("Viewport tools registered")
