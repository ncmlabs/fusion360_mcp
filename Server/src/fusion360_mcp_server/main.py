"""Main entry point for Fusion 360 MCP Server."""

import argparse
from mcp.server.fastmcp import FastMCP

from .config import get_config
from .logging import setup_logging, get_logger
from .tools import (
    register_query_tools,
    register_creation_tools,
    register_modification_tools,
    register_validation_tools,
    register_system_tools,
    register_viewport_tools,
    register_assembly_tools,
)


# Create FastMCP server instance
mcp = FastMCP(
    "Fusion360",
    instructions="""You are an assistant for Fusion 360 CAD design.

WORKFLOW:
1. Use get_design_state() first to understand the current design context
2. Use get_bodies() and get_sketches() to explore existing geometry
3. Use get_body_by_id() or get_sketch_by_id() for detailed information
4. Entity IDs from query results can be used in modification operations

CREATION WORKFLOW:
1. For simple primitives, use create_box() or create_cylinder()
2. For custom shapes:
   a. Create a sketch with create_sketch()
   b. Draw geometry with draw_line(), draw_circle(), draw_rectangle(), draw_arc()
   c. Extrude with extrude() or revolve with revolve()
3. Apply edge modifications with fillet() or chamfer()
4. Add holes with create_hole()

MODIFICATION WORKFLOW:
1. Move bodies with move_body() - preserves parametric relationships
2. Rotate bodies with rotate_body() - preserves parametric relationships
3. Change feature dimensions with modify_feature() (e.g., extrusion distance)
4. Update design parameters with update_parameter() for dynamic changes
5. Delete bodies with delete_body() or features with delete_feature()
6. Edit sketch curves with edit_sketch() to modify geometry

VALIDATION WORKFLOW:
1. Use measure_distance() to verify spacing between entities (accurate to 0.001mm)
2. Use measure_angle() to check angles between faces or edges
3. Use check_interference() to detect collisions between bodies
4. Use get_body_properties() for volume, area, center of mass, and dimensions
5. Use get_sketch_status() to check if a sketch is fully constrained

VIEWPORT WORKFLOW:
1. Use take_screenshot() to capture the current view as PNG (base64 or file)
2. Use set_view() to switch to standard views (front, top, isometric, etc.)
3. Use set_camera() for precise camera positioning
4. Use fit_view() to zoom to fit all geometry or specific entities
5. Use get_camera() to query the current camera state

ASSEMBLY WORKFLOW:
1. Create components with create_component() to organize related geometry
2. Activate a component with activate_component() before adding geometry to it
3. Query components with get_components() and get_component_by_id()
4. Position component instances with move_occurrence()
5. Connect components with create_joint() or create_joint_between_occurrences()
6. Query joints with get_joints() and get_joint_by_id()
7. Joint types: rigid, revolute, slider, cylindrical, pin_slot, planar, ball

IMPORTANT:
- All dimensions are in millimeters (mm)
- Always query the design state before making changes
- Use the returned entity IDs for referencing bodies and sketches
- Check body.is_solid to know if you're working with solid or surface geometry
- Check sketch.is_fully_constrained to know if a sketch is ready for extrusion
- For fillet/chamfer, get edge IDs using get_body_by_id with include_edges=True
- move_body and rotate_body use parametric operations that preserve design history
- Use update_parameter to change dimensions via expressions like "50 mm" or "d1 * 2"
- Use take_screenshot() to visualize the design at any point in the workflow

CRITICAL CONSTRAINTS:
- All dimensions must be > 0.001 mm
- create_torus: minor_radius must be < major_radius
- create_pipe: wall_thickness must be < outer_diameter/2
- loft with cut/join/intersect: REQUIRES target_body_id parameter
- draw_polygon: sides must be 3-64
- extrude/revolve: sketch must have closed profiles (profiles_count > 0)
- add_sketch_text: creates SketchText (no profiles) - use emboss for text features
- create_coil: NOT SUPPORTED - use sweep with helical path instead

QUICK TOOL SELECTION:
- Understand design → get_design_state(), get_bodies(), get_sketches()
- Simple shapes → create_box(), create_cylinder(), create_sphere()
- Custom 2D→3D → create_sketch() → draw_*() → extrude()
- Along path → sweep() (solid) or create_pipe() (hollow)
- Between profiles → loft() [remember target_body_id for cut/join]
- Round edges → fillet()
- Bevel edges → chamfer()
- Patterns → circular_pattern(), rectangular_pattern()
- Validate → measure_distance(), check_interference(), get_body_properties()
- Visualize → take_screenshot(), set_view("isometric")
""",
)


def main() -> None:
    """Main entry point."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Fusion 360 MCP Server")
    parser.add_argument(
        "--transport",
        type=str,
        choices=["sse", "stdio"],
        help="MCP transport type (overrides config)"
    )
    parser.add_argument(
        "--port",
        type=int,
        help="Fusion 360 add-in port (overrides config)"
    )
    args = parser.parse_args()

    # Setup logging
    setup_logging()
    logger = get_logger(__name__)

    # Get configuration
    config = get_config()

    # Apply port override if provided
    if args.port:
        config.fusion_port = args.port

    logger.info(
        "Starting Fusion 360 MCP Server",
        fusion_url=config.fusion_base_url,
        transport=args.transport or config.server_transport,
    )

    # Register tools
    register_query_tools(mcp)
    logger.info("Query tools registered")

    register_creation_tools(mcp)
    logger.info("Creation tools registered")

    register_modification_tools(mcp)
    logger.info("Modification tools registered")

    register_validation_tools(mcp)
    logger.info("Validation tools registered")

    register_system_tools(mcp)
    logger.info("System tools registered")

    register_viewport_tools(mcp)
    logger.info("Viewport tools registered")

    register_assembly_tools(mcp)
    logger.info("Assembly tools registered")

    # Determine transport
    transport = args.transport or config.server_transport

    # Run MCP server
    logger.info("Starting MCP server", transport=transport)
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
