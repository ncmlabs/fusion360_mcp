"""Fusion 360 MCP Add-in Entry Point.

This add-in provides an HTTP interface for the MCP server to communicate
with Fusion 360, enabling AI-assisted CAD design.
"""

# Add the add-in folder to sys.path for local module imports
import os
import sys
_ADDIN_PATH = os.path.dirname(os.path.abspath(__file__))
if _ADDIN_PATH not in sys.path:
    sys.path.insert(0, _ADDIN_PATH)

# Fusion 360 API imports - these are only available when running in Fusion
try:
    import adsk.core
    import adsk.fusion
    FUSION_AVAILABLE = True
except ImportError:
    FUSION_AVAILABLE = False

import traceback
from typing import Optional, Any, Dict

from core.event_manager import EventManager
from core.http_server import FusionHTTPServer, FusionHTTPHandler, ServerConfig, setup_default_routes
from core.task_queue import reset as reset_task_queue
from core.entity_registry import reset_registry

# Import query handlers
from handlers.query_handlers import (
    handle_get_design_state,
    handle_get_bodies,
    handle_get_body_by_id,
    handle_get_sketches,
    handle_get_sketch_by_id,
    handle_get_parameters,
    handle_get_timeline,
)

# Import creation handlers
from handlers.creation_handlers import (
    # Body creation
    handle_create_box,
    handle_create_cylinder,
    # Sketch creation
    handle_create_sketch,
    handle_draw_line,
    handle_draw_circle,
    handle_draw_rectangle,
    handle_draw_arc,
    # Feature creation
    handle_extrude,
    handle_revolve,
    handle_fillet,
    handle_chamfer,
    handle_create_hole,
)


# Global state
_app: Optional[Any] = None
_ui: Optional[Any] = None
_event_manager: Optional[EventManager] = None
_http_server: Optional[FusionHTTPServer] = None
_handlers: list = []

# Configuration
HTTP_PORT = 5001
HTTP_HOST = "localhost"


def run(context: Dict[str, Any]) -> None:
    """Add-in entry point - called when add-in is started.

    Args:
        context: Fusion 360 context dictionary
    """
    global _app, _ui, _event_manager, _http_server

    try:
        if FUSION_AVAILABLE:
            _app = adsk.core.Application.get()
            _ui = _app.userInterface
        else:
            _app = None
            _ui = None

        # Initialize event manager
        _event_manager = EventManager(_app)

        # Register task handlers
        _register_task_handlers()

        # Start event manager
        if not _event_manager.start():
            _show_message("Failed to start event manager")
            return

        # Setup HTTP routes
        setup_default_routes()
        _register_query_routes()
        _register_creation_routes()

        # Start HTTP server
        config = ServerConfig(host=HTTP_HOST, port=HTTP_PORT)
        _http_server = FusionHTTPServer(config)

        if not _http_server.start():
            _show_message(f"Failed to start HTTP server on port {HTTP_PORT}")
            return

        _show_message(f"Fusion MCP Add-in started on {_http_server.address}")

    except Exception as e:
        _show_message(f"Failed to start add-in: {traceback.format_exc()}")


def stop(context: Dict[str, Any]) -> None:
    """Add-in shutdown - called when add-in is stopped.

    Args:
        context: Fusion 360 context dictionary
    """
    global _app, _ui, _event_manager, _http_server

    try:
        # Stop HTTP server
        if _http_server:
            _http_server.stop()
            _http_server = None

        # Stop event manager
        if _event_manager:
            _event_manager.stop()
            _event_manager = None

        # Reset task queue
        reset_task_queue()

        # Reset entity registry
        reset_registry()

        # Clear routes
        FusionHTTPHandler.clear_routes()

        _show_message("Fusion MCP Add-in stopped")

    except Exception as e:
        _show_message(f"Error stopping add-in: {traceback.format_exc()}")

    finally:
        _app = None
        _ui = None


def _register_task_handlers() -> None:
    """Register all task handlers with the event manager."""
    global _event_manager

    if not _event_manager:
        return

    # Health/test handlers (handled directly by HTTP server custom handlers)

    # Phase 1: Query handlers
    _event_manager.register_task_handler("get_design_state", handle_get_design_state)
    _event_manager.register_task_handler("get_bodies", handle_get_bodies)
    _event_manager.register_task_handler("get_body_by_id", handle_get_body_by_id)
    _event_manager.register_task_handler("get_sketches", handle_get_sketches)
    _event_manager.register_task_handler("get_sketch_by_id", handle_get_sketch_by_id)
    _event_manager.register_task_handler("get_parameters", handle_get_parameters)
    _event_manager.register_task_handler("get_timeline", handle_get_timeline)

    # Phase 2: Creation handlers - Bodies
    _event_manager.register_task_handler("create_box", handle_create_box)
    _event_manager.register_task_handler("create_cylinder", handle_create_cylinder)

    # Phase 2: Creation handlers - Sketches
    _event_manager.register_task_handler("create_sketch", handle_create_sketch)
    _event_manager.register_task_handler("draw_line", handle_draw_line)
    _event_manager.register_task_handler("draw_circle", handle_draw_circle)
    _event_manager.register_task_handler("draw_rectangle", handle_draw_rectangle)
    _event_manager.register_task_handler("draw_arc", handle_draw_arc)

    # Phase 2: Creation handlers - Features
    _event_manager.register_task_handler("extrude", handle_extrude)
    _event_manager.register_task_handler("revolve", handle_revolve)
    _event_manager.register_task_handler("fillet", handle_fillet)
    _event_manager.register_task_handler("chamfer", handle_chamfer)
    _event_manager.register_task_handler("create_hole", handle_create_hole)


def _register_query_routes() -> None:
    """Register HTTP routes for query endpoints."""
    # Phase 1: Query routes
    FusionHTTPHandler.register_route("POST", "/query/design_state", "get_design_state")
    FusionHTTPHandler.register_route("GET", "/query/design_state", "get_design_state")
    FusionHTTPHandler.register_route("POST", "/query/bodies", "get_bodies")
    FusionHTTPHandler.register_route("GET", "/query/bodies", "get_bodies")
    FusionHTTPHandler.register_route("POST", "/query/body", "get_body_by_id")
    FusionHTTPHandler.register_route("POST", "/query/sketches", "get_sketches")
    FusionHTTPHandler.register_route("GET", "/query/sketches", "get_sketches")
    FusionHTTPHandler.register_route("POST", "/query/sketch", "get_sketch_by_id")
    FusionHTTPHandler.register_route("POST", "/query/parameters", "get_parameters")
    FusionHTTPHandler.register_route("GET", "/query/parameters", "get_parameters")
    FusionHTTPHandler.register_route("POST", "/query/timeline", "get_timeline")
    FusionHTTPHandler.register_route("GET", "/query/timeline", "get_timeline")


def _register_creation_routes() -> None:
    """Register HTTP routes for creation endpoints."""
    # Phase 2: Body creation routes
    FusionHTTPHandler.register_route("POST", "/create/box", "create_box")
    FusionHTTPHandler.register_route("POST", "/create/cylinder", "create_cylinder")

    # Phase 2: Sketch creation routes
    FusionHTTPHandler.register_route("POST", "/create/sketch", "create_sketch")
    FusionHTTPHandler.register_route("POST", "/sketch/line", "draw_line")
    FusionHTTPHandler.register_route("POST", "/sketch/circle", "draw_circle")
    FusionHTTPHandler.register_route("POST", "/sketch/rectangle", "draw_rectangle")
    FusionHTTPHandler.register_route("POST", "/sketch/arc", "draw_arc")

    # Phase 2: Feature creation routes
    FusionHTTPHandler.register_route("POST", "/create/extrude", "extrude")
    FusionHTTPHandler.register_route("POST", "/create/revolve", "revolve")
    FusionHTTPHandler.register_route("POST", "/create/fillet", "fillet")
    FusionHTTPHandler.register_route("POST", "/create/chamfer", "chamfer")
    FusionHTTPHandler.register_route("POST", "/create/hole", "create_hole")


def _show_message(message: str) -> None:
    """Show a message to the user.

    Args:
        message: Message to display
    """
    global _ui
    try:
        if _ui:
            _ui.messageBox(message)
        else:
            print(message)
    except:
        print(message)


# For testing outside Fusion 360
if __name__ == "__main__":
    print("Starting Fusion MCP Add-in in standalone mode...")
    run({})
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop({})
