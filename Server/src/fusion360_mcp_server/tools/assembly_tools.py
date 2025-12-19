"""Assembly tools for Fusion 360 MCP Server.

These tools enable AI to create and manage components, occurrences,
and joints for assembly design in Fusion 360.
"""

from typing import Optional
from mcp.server.fastmcp import FastMCP

from ..services.fusion_client import FusionClient
from ..logging import get_logger

logger = get_logger(__name__)


def register_assembly_tools(mcp: FastMCP) -> None:
    """Register all assembly tools with the MCP server.

    Args:
        mcp: FastMCP server instance
    """

    # --- Component Tools ---

    @mcp.tool()
    async def create_component(name: str) -> dict:
        """Create a new component in the design.

        Components are containers for bodies, sketches, and features that
        can be positioned independently as units in an assembly. Creating
        a component also creates an occurrence (instance) of it.

        Use components to:
        - Organize related geometry together
        - Create reusable parts
        - Build assemblies with multiple parts
        - Apply transforms to groups of geometry

        Args:
            name: Name for the new component. Should be descriptive,
                  like "Bracket", "Housing", or "Shaft".

        Returns:
            Dict containing:
            - success: True if component was created
            - component: Component info including id, name, is_root
            - occurrence: Occurrence info including id and transform
            - component_id: The new component's ID for future operations
            - occurrence_id: The occurrence ID for positioning

        Example:
            # Create a new component for a bracket
            result = await create_component(name="Bracket")
            component_id = result["component_id"]

            # Now activate it and add geometry
            await activate_component(component_id=component_id)
            await create_box(width=50, depth=10, height=30)
        """
        logger.info("create_component called", name=name)
        async with FusionClient() as client:
            return await client.create_component(name=name)

    @mcp.tool()
    async def get_components() -> dict:
        """Get all components in the design.

        Returns a list of all components including the root component
        and any user-created components. Use this to understand the
        design hierarchy and find component IDs.

        Returns:
            Dict containing:
            - success: True if query succeeded
            - components: List of component summaries with:
              - id: Component ID
              - name: Component name
              - is_root: True if this is the root component
              - is_active: True if this is the active component
              - bodies_count: Number of bodies in the component
              - sketches_count: Number of sketches
              - occurrences_count: Number of child occurrences
            - total: Total number of components

        Example:
            # List all components to find one to work with
            result = await get_components()
            for comp in result["components"]:
                print(f"{comp['name']}: {comp['bodies_count']} bodies")
        """
        logger.info("get_components called")
        async with FusionClient() as client:
            return await client.get_components()

    @mcp.tool()
    async def get_component_by_id(component_id: str) -> dict:
        """Get detailed information about a specific component.

        Returns full details about a component including its contents,
        bounding box, and occurrence IDs.

        Args:
            component_id: The component ID to retrieve details for.
                         Get this from get_components() or create_component().

        Returns:
            Dict containing:
            - success: True if found
            - component: Full component info including:
              - id, name, is_root, is_active
              - bodies_count, sketches_count, features_count
              - body_ids: List of body IDs in this component
              - sketch_ids: List of sketch IDs
              - occurrence_ids: List of occurrence IDs
              - bounding_box: Component bounding box

        Example:
            result = await get_component_by_id(component_id="Bracket")
            print(f"Bodies: {result['component']['body_ids']}")
        """
        logger.info("get_component_by_id called", component_id=component_id)
        async with FusionClient() as client:
            return await client.get_component_by_id(component_id=component_id)

    @mcp.tool()
    async def activate_component(component_id: str) -> dict:
        """Activate a component for editing.

        Makes the specified component the active component. All new
        geometry (sketches, bodies, features) will be created in
        the active component.

        Args:
            component_id: The component ID to activate.
                         Use "RootComponent" or the root's ID to return
                         to the top level.

        Returns:
            Dict containing:
            - success: True if activation succeeded
            - active_component: The now-active component info
            - component_id: The activated component's ID

        Example:
            # Activate a component before adding geometry to it
            await activate_component(component_id="Bracket")
            await create_box(width=50, depth=10, height=30)

            # Return to root when done
            await activate_component(component_id="RootComponent")
        """
        logger.info("activate_component called", component_id=component_id)
        async with FusionClient() as client:
            return await client.activate_component(component_id=component_id)

    @mcp.tool()
    async def get_component_bodies(component_id: str) -> dict:
        """Get all bodies within a specific component.

        Returns detailed information about all bodies contained in
        the specified component. Useful for finding bodies to modify
        or use in joints.

        Args:
            component_id: The component ID to get bodies from.

        Returns:
            Dict containing:
            - success: True if query succeeded
            - bodies: List of body summaries
            - total: Number of bodies
            - component_id: The queried component ID

        Example:
            result = await get_component_bodies(component_id="Bracket")
            for body in result["bodies"]:
                print(f"{body['name']}: volume={body['volume']}mm^3")
        """
        logger.info("get_component_bodies called", component_id=component_id)
        async with FusionClient() as client:
            return await client.get_component_bodies(component_id=component_id)

    # --- Occurrence Tools ---

    @mcp.tool()
    async def get_occurrences(component_id: Optional[str] = None) -> dict:
        """Get all occurrences in the design or within a component.

        Occurrences are instances of components positioned in space.
        A single component can have multiple occurrences (like bolts
        in an assembly).

        Args:
            component_id: Optional component ID to filter occurrences.
                         If not provided, returns all occurrences in the design.

        Returns:
            Dict containing:
            - success: True if query succeeded
            - occurrences: List of occurrence info with:
              - id: Occurrence ID
              - name: Occurrence name (like "Bracket:1")
              - component_id: The component this occurrence instantiates
              - transform: Position/rotation transform matrix
              - is_visible: Whether occurrence is visible
              - is_grounded: Whether occurrence is fixed in place
            - total: Number of occurrences

        Example:
            # Get all occurrences
            result = await get_occurrences()

            # Get occurrences only in a specific component
            result = await get_occurrences(component_id="Assembly")
        """
        logger.info("get_occurrences called", component_id=component_id)
        async with FusionClient() as client:
            return await client.get_occurrences(component_id=component_id)

    @mcp.tool()
    async def move_occurrence(
        occurrence_id: str,
        x: float = 0.0,
        y: float = 0.0,
        z: float = 0.0,
    ) -> dict:
        """Move an occurrence to a new position.

        Applies a translation to an occurrence's position. The values
        are added to the current position (relative move, not absolute).

        **All values are in millimeters (mm).**

        Args:
            occurrence_id: The occurrence ID to move.
                          Get this from get_occurrences() or create_component().
            x: X translation in mm. Positive = right.
            y: Y translation in mm. Positive = forward.
            z: Z translation in mm. Positive = up.

        Returns:
            Dict containing:
            - success: True if move succeeded
            - occurrence: Updated occurrence info with new transform
            - occurrence_id: The moved occurrence ID
            - translation: The applied translation

        Example:
            # Move a bracket occurrence 100mm to the right
            await move_occurrence(occurrence_id="Bracket:1", x=100)

            # Move up and forward
            await move_occurrence(occurrence_id="Bracket:1", y=50, z=25)
        """
        logger.info(
            "move_occurrence called",
            occurrence_id=occurrence_id,
            x=x,
            y=y,
            z=z,
        )
        async with FusionClient() as client:
            return await client.move_occurrence(
                occurrence_id=occurrence_id,
                x=x,
                y=y,
                z=z,
            )

    # --- Joint Tools ---

    @mcp.tool()
    async def create_joint(
        geometry1_id: str,
        geometry2_id: str,
        joint_type: str = "rigid",
    ) -> dict:
        """Create a joint between two geometry entities.

        Creates an assembly joint that constrains the motion between
        two parts. The geometry entities can be faces, edges, or
        construction geometry from different occurrences.

        **Joint Types:**
        - rigid: No relative motion (parts fixed together)
        - revolute: Rotation around one axis (like a hinge)
        - slider: Translation along one axis (like a drawer)
        - cylindrical: Rotation + translation along same axis (like a piston)
        - pin_slot: Rotation + perpendicular translation
        - planar: Motion in a plane (2D freedom)
        - ball: Rotation in all directions (like a ball joint)

        Args:
            geometry1_id: First geometry entity ID (face, edge, or vertex).
                         Get from get_body_by_id() with include_faces=True.
            geometry2_id: Second geometry entity ID from a different occurrence.
            joint_type: Type of joint. Default "rigid".

        Returns:
            Dict containing:
            - success: True if joint was created
            - joint: Joint info including id, type, connected occurrences
            - joint_id: The new joint's ID

        Example:
            # Create a rigid joint between two faces
            result = await create_joint(
                geometry1_id="body1_face_0",
                geometry2_id="body2_face_0",
                joint_type="rigid"
            )

            # Create a revolute (hinge) joint
            result = await create_joint(
                geometry1_id="bracket_face_0",
                geometry2_id="door_face_0",
                joint_type="revolute"
            )
        """
        logger.info(
            "create_joint called",
            geometry1_id=geometry1_id,
            geometry2_id=geometry2_id,
            joint_type=joint_type,
        )
        async with FusionClient() as client:
            return await client.create_joint(
                geometry1_id=geometry1_id,
                geometry2_id=geometry2_id,
                joint_type=joint_type,
            )

    @mcp.tool()
    async def create_joint_between_occurrences(
        occurrence1_id: str,
        occurrence2_id: str,
        joint_type: str = "rigid",
    ) -> dict:
        """Create a joint between two occurrences at their origins.

        A simpler way to create joints when you want to connect two
        occurrences without specifying exact geometry. Uses the origin
        points of each occurrence.

        Args:
            occurrence1_id: First occurrence ID.
            occurrence2_id: Second occurrence ID.
            joint_type: Type of joint. Default "rigid".
                       Options: rigid, revolute, slider, cylindrical,
                       pin_slot, planar, ball

        Returns:
            Dict containing:
            - success: True if joint was created
            - joint: Joint info including id, type, connected occurrences
            - joint_id: The new joint's ID

        Example:
            # Create components and then join them
            comp1 = await create_component(name="Part1")
            comp2 = await create_component(name="Part2")

            # Move Part2 to offset position
            await move_occurrence(occurrence_id=comp2["occurrence_id"], x=100)

            # Create a rigid joint between them
            await create_joint_between_occurrences(
                occurrence1_id=comp1["occurrence_id"],
                occurrence2_id=comp2["occurrence_id"],
                joint_type="rigid"
            )
        """
        logger.info(
            "create_joint_between_occurrences called",
            occurrence1_id=occurrence1_id,
            occurrence2_id=occurrence2_id,
            joint_type=joint_type,
        )
        async with FusionClient() as client:
            return await client.create_joint_between_occurrences(
                occurrence1_id=occurrence1_id,
                occurrence2_id=occurrence2_id,
                joint_type=joint_type,
            )

    @mcp.tool()
    async def get_joints() -> dict:
        """Get all joints in the design.

        Returns a list of all assembly joints, including their types
        and connected occurrences.

        Returns:
            Dict containing:
            - success: True if query succeeded
            - joints: List of joint info with:
              - id: Joint ID
              - name: Joint name
              - joint_type: Type (rigid, revolute, slider, etc.)
              - occurrence1_id: First connected occurrence
              - occurrence2_id: Second connected occurrence
              - is_suppressed: Whether joint is disabled
            - total: Number of joints

        Example:
            result = await get_joints()
            for joint in result["joints"]:
                print(f"{joint['name']}: {joint['joint_type']} joint")
        """
        logger.info("get_joints called")
        async with FusionClient() as client:
            return await client.get_joints()

    @mcp.tool()
    async def get_joint_by_id(joint_id: str) -> dict:
        """Get detailed information about a specific joint.

        Args:
            joint_id: The joint ID to retrieve details for.

        Returns:
            Dict containing:
            - success: True if found
            - joint: Full joint info

        Example:
            result = await get_joint_by_id(joint_id="Rigid1")
            print(f"Connects: {result['joint']['occurrence1_id']} to {result['joint']['occurrence2_id']}")
        """
        logger.info("get_joint_by_id called", joint_id=joint_id)
        async with FusionClient() as client:
            return await client.get_joint_by_id(joint_id=joint_id)
