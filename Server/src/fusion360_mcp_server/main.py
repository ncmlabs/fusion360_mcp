"""Main entry point for Fusion 360 MCP Server."""

import argparse
from .config import get_config
from .logging import setup_logging, get_logger


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
    logger.info(
        "Starting Fusion 360 MCP Server",
        fusion_url=config.fusion_base_url,
        transport=args.transport or config.server_transport,
    )

    # TODO: Initialize MCP server with tools (Phase 1+)
    logger.info("Server infrastructure ready - tools will be added in Phase 1")


if __name__ == "__main__":
    main()
