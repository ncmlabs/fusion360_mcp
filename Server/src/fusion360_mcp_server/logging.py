"""Structured logging for Fusion 360 MCP Server.

Provides JSON logging with correlation IDs for request tracing.
"""

import structlog
import uuid
import logging
from contextvars import ContextVar
from typing import Optional, Any, Dict
from .config import get_config


# Context variable for correlation ID
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> str:
    """Get current correlation ID or generate a new one."""
    cid = correlation_id_var.get()
    if cid is None:
        cid = str(uuid.uuid4())[:8]
        correlation_id_var.set(cid)
    return cid


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID for the current context."""
    correlation_id_var.set(correlation_id)


def new_correlation_id() -> str:
    """Generate and set a new correlation ID."""
    cid = str(uuid.uuid4())[:8]
    correlation_id_var.set(cid)
    return cid


def clear_correlation_id() -> None:
    """Clear the correlation ID."""
    correlation_id_var.set(None)


def add_correlation_id(
    logger: Any,
    method_name: str,
    event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Structlog processor to add correlation ID."""
    event_dict["correlation_id"] = get_correlation_id()
    return event_dict


def setup_logging() -> None:
    """Configure structured logging."""
    config = get_config()

    # Configure structlog processors
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        add_correlation_id,
        structlog.processors.UnicodeDecoder(),
    ]

    if config.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Set log level
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)
    logging.basicConfig(
        format="%(message)s",
        level=log_level,
    )


def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    """Get a logger instance."""
    return structlog.get_logger(name)


class LogContext:
    """Context manager for scoped logging with correlation ID."""

    def __init__(self, correlation_id: Optional[str] = None, **extra: Any):
        self.correlation_id = correlation_id
        self.extra = extra
        self._previous_id: Optional[str] = None

    def __enter__(self) -> "LogContext":
        self._previous_id = correlation_id_var.get()
        if self.correlation_id:
            correlation_id_var.set(self.correlation_id)
        elif self._previous_id is None:
            correlation_id_var.set(str(uuid.uuid4())[:8])
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        correlation_id_var.set(self._previous_id)
