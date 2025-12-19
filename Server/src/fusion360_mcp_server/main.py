"""Main entry point for Fusion 360 MCP Server."""

import argparse
from mcp.server.fastmcp import FastMCP

from .config import get_config
from .logging import setup_logging, get_logger
from .tools import register_query_tools, register_creation_tools


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

IMPORTANT:
- All dimensions are in millimeters (mm)
- Always query the design state before making changes
- Use the returned entity IDs for referencing bodies and sketches
- Check body.is_solid to know if you're working with solid or surface geometry
- Check sketch.is_fully_constrained to know if a sketch is ready for extrusion
- For fillet/chamfer, get edge IDs using get_body_by_id with include_edges=True
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

    # Determine transport
    transport = args.transport or config.server_transport

    # Run MCP server
    logger.info("Starting MCP server", transport=transport)
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
