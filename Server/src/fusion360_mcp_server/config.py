"""Configuration management for Fusion 360 MCP Server.

Uses pydantic-settings for environment variable support with validation.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class ServerConfig(BaseSettings):
    """Server configuration with environment variable support."""

    # Fusion 360 Add-in connection
    fusion_host: str = Field(default="localhost", description="Fusion 360 add-in host")
    fusion_port: int = Field(default=5001, description="Fusion 360 add-in port")

    # Server settings
    server_transport: str = Field(
        default="sse",
        description="MCP transport type: sse or stdio"
    )

    # Logging
    log_level: str = Field(default="INFO", description="Log level")
    log_format: str = Field(
        default="json",
        description="Log format: json or console"
    )

    # Timeouts
    request_timeout: float = Field(
        default=30.0,
        description="HTTP request timeout in seconds"
    )
    task_timeout: float = Field(
        default=30.0,
        description="Task execution timeout in seconds"
    )

    # Retry settings
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_delay: float = Field(default=1.0, description="Delay between retries in seconds")

    @property
    def fusion_base_url(self) -> str:
        """Get the base URL for Fusion 360 add-in."""
        return f"http://{self.fusion_host}:{self.fusion_port}"

    model_config = {
        "env_prefix": "FUSION_MCP_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


# Singleton instance
_config: Optional[ServerConfig] = None


def get_config() -> ServerConfig:
    """Get the configuration singleton."""
    global _config
    if _config is None:
        _config = ServerConfig()
    return _config


def reset_config() -> None:
    """Reset the configuration singleton (for testing)."""
    global _config
    _config = None
