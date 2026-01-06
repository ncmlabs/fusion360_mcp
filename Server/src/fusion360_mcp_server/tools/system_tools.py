"""System tools for Fusion 360 MCP Server.

These tools provide health check, version information, and system status
for monitoring and diagnostics.
"""

from mcp.server.fastmcp import FastMCP

from ..services.fusion_client import FusionClient
from ..logging import get_logger

# Server version (should match pyproject.toml)
SERVER_VERSION = "0.1.2"
API_VERSION = "1.0"

logger = get_logger(__name__)


def register_system_tools(mcp: FastMCP) -> None:
    """Register all system tools with the MCP server.

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool()
    async def check_health() -> dict:
        """Check the health status of the Fusion 360 connection.

        Verifies that:
        - The MCP server is running
        - The Fusion 360 add-in is responsive
        - Communication between server and add-in is working

        **Use this** to diagnose connection issues or verify the system
        is ready for design operations.

        Returns:
            Dict with health status:
            - healthy: True if all systems operational
            - server_status: "running" if MCP server is operational
            - addin_status: "healthy", "unhealthy", or "unreachable"
            - message: Human-readable status message

        Example response:
            {
                "healthy": true,
                "server_status": "running",
                "addin_status": "healthy",
                "message": "All systems operational"
            }
        """
        logger.info("check_health called")
        async with FusionClient() as client:
            addin_health = await client.health_check()

        overall_healthy = addin_health.get("healthy", False)

        return {
            "healthy": overall_healthy,
            "server_status": "running",
            "server_version": SERVER_VERSION,
            "addin_status": addin_health.get("status", "unknown"),
            "addin_version": addin_health.get("version", "unknown"),
            "message": (
                "All systems operational"
                if overall_healthy
                else f"Add-in issue: {addin_health.get('message', 'Unknown error')}"
            ),
        }

    @mcp.tool()
    async def get_version() -> dict:
        """Get version information for all system components.

        Returns version details for:
        - MCP Server
        - Fusion 360 Add-in
        - Fusion 360 application
        - API compatibility version

        **Use this** to verify compatibility or for debugging purposes.

        Returns:
            Dict with version information:
            - server_version: MCP server version
            - addin_version: Fusion add-in version
            - fusion_version: Fusion 360 application version
            - api_version: API protocol version

        Example response:
            {
                "server_version": "0.1.0",
                "addin_version": "0.1.0",
                "fusion_version": "2.0.18719",
                "api_version": "1.0"
            }
        """
        logger.info("get_version called")
        async with FusionClient() as client:
            try:
                addin_info = await client.get_version()
                return {
                    "server_version": SERVER_VERSION,
                    "addin_name": addin_info.get("addin_name", "FusionMCP"),
                    "addin_version": addin_info.get("addin_version", "unknown"),
                    "fusion_version": addin_info.get("fusion_version", "unknown"),
                    "api_version": API_VERSION,
                }
            except Exception as e:
                logger.warning("Failed to get add-in version", error=str(e))
                return {
                    "server_version": SERVER_VERSION,
                    "addin_name": "FusionMCP",
                    "addin_version": "unknown (unreachable)",
                    "fusion_version": "unknown",
                    "api_version": API_VERSION,
                    "error": str(e),
                }
