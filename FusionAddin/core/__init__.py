"""Core infrastructure for Fusion 360 MCP Add-in."""

from .task_queue import (
    Task,
    TaskResult,
    create_task,
    submit_task,
    set_task_result,
    wait_for_result,
    execute_and_wait,
    get_task_queue,
    clear_queue,
    reset,
    DEFAULT_TIMEOUT,
)
from .http_server import (
    FusionHTTPServer,
    FusionHTTPHandler,
    ServerConfig,
)

__all__ = [
    # Task Queue
    "Task",
    "TaskResult",
    "create_task",
    "submit_task",
    "set_task_result",
    "wait_for_result",
    "execute_and_wait",
    "get_task_queue",
    "clear_queue",
    "reset",
    "DEFAULT_TIMEOUT",
    # HTTP Server
    "FusionHTTPServer",
    "FusionHTTPHandler",
    "ServerConfig",
]
