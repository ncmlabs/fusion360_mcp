"""Shared modules for Fusion 360 MCP Server and Add-in."""

from .exceptions import (
    FusionMCPError,
    EntityNotFoundError,
    InvalidParameterError,
    GeometryError,
    ConstraintError,
    FeatureError,
    SelectionError,
    ConnectionError,
    TimeoutError,
    DesignStateError,
    ErrorContext,
    ErrorDetail,
    ErrorResponse,
)

__all__ = [
    "FusionMCPError",
    "EntityNotFoundError",
    "InvalidParameterError",
    "GeometryError",
    "ConstraintError",
    "FeatureError",
    "SelectionError",
    "ConnectionError",
    "TimeoutError",
    "DesignStateError",
    "ErrorContext",
    "ErrorDetail",
    "ErrorResponse",
]
