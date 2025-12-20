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
    # Advanced sketch geometry
    handle_draw_polygon,
    handle_draw_ellipse,
    handle_draw_slot,
    handle_draw_spline,
    handle_draw_point,
    # Phase 7b: Sketch patterns & operations
    handle_sketch_mirror,
    handle_sketch_circular_pattern,
    handle_sketch_rectangular_pattern,
    handle_project_geometry,
    handle_add_sketch_text,
    # Phase 7c: Sketch constraints & dimensions
    handle_add_constraint_horizontal,
    handle_add_constraint_vertical,
    handle_add_constraint_coincident,
    handle_add_constraint_perpendicular,
    handle_add_constraint_parallel,
    handle_add_constraint_tangent,
    handle_add_constraint_equal,
    handle_add_constraint_concentric,
    handle_add_constraint_fix,
    handle_add_dimension,
    # Feature creation
    handle_extrude,
    handle_revolve,
    handle_fillet,
    handle_chamfer,
    handle_create_hole,
    # Phase 8a: Advanced feature tools
    handle_sweep,
    handle_loft,
    handle_create_sphere,
    handle_create_torus,
    handle_create_coil,
    handle_create_pipe,
    # Phase 8b: Feature Pattern Tools
    handle_rectangular_pattern,
    handle_circular_pattern,
    handle_mirror_feature,
    # Phase 8c: Specialized Feature Tools
    handle_create_thread,
    handle_thicken,
    handle_emboss,
    # Construction plane creation
    handle_create_offset_plane,
    handle_create_angle_plane,
    handle_create_three_point_plane,
    handle_create_midplane,
)

# Import modification handlers
from handlers.modification_handlers import (
    handle_move_body,
    handle_rotate_body,
    handle_modify_feature,
    handle_update_parameter,
    handle_delete_body,
    handle_delete_feature,
    handle_edit_sketch,
    # MODIFY menu tools
    handle_combine,
    handle_split_body,
    handle_shell,
)

# Import validation handlers
from handlers.validation_handlers import (
    handle_measure_distance,
    handle_measure_angle,
    handle_check_interference,
    handle_get_body_properties,
    handle_get_sketch_status,
)

# Import viewport handlers
from handlers.viewport_handlers import (
    handle_take_screenshot,
    handle_set_camera,
    handle_get_camera,
    handle_set_view,
    handle_fit_view,
)

# Import assembly handlers
from handlers.assembly_handlers import (
    handle_create_component,
    handle_get_components,
    handle_get_component_by_id,
    handle_activate_component,
    handle_get_component_bodies,
    handle_get_occurrences,
    handle_move_occurrence,
    handle_create_joint,
    handle_create_joint_between_occurrences,
    handle_get_joints,
    handle_get_joint_by_id,
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
        _register_modification_routes()
        _register_validation_routes()
        _register_viewport_routes()
        _register_assembly_routes()

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

    # Phase 7a: Advanced sketch geometry handlers
    _event_manager.register_task_handler("draw_polygon", handle_draw_polygon)
    _event_manager.register_task_handler("draw_ellipse", handle_draw_ellipse)
    _event_manager.register_task_handler("draw_slot", handle_draw_slot)
    _event_manager.register_task_handler("draw_spline", handle_draw_spline)
    _event_manager.register_task_handler("draw_point", handle_draw_point)

    # Phase 7b: Sketch patterns & operations handlers
    _event_manager.register_task_handler("sketch_mirror", handle_sketch_mirror)
    _event_manager.register_task_handler("sketch_circular_pattern", handle_sketch_circular_pattern)
    _event_manager.register_task_handler("sketch_rectangular_pattern", handle_sketch_rectangular_pattern)
    _event_manager.register_task_handler("project_geometry", handle_project_geometry)
    _event_manager.register_task_handler("add_sketch_text", handle_add_sketch_text)

    # Phase 7c: Sketch constraints & dimensions handlers
    _event_manager.register_task_handler("add_constraint_horizontal", handle_add_constraint_horizontal)
    _event_manager.register_task_handler("add_constraint_vertical", handle_add_constraint_vertical)
    _event_manager.register_task_handler("add_constraint_coincident", handle_add_constraint_coincident)
    _event_manager.register_task_handler("add_constraint_perpendicular", handle_add_constraint_perpendicular)
    _event_manager.register_task_handler("add_constraint_parallel", handle_add_constraint_parallel)
    _event_manager.register_task_handler("add_constraint_tangent", handle_add_constraint_tangent)
    _event_manager.register_task_handler("add_constraint_equal", handle_add_constraint_equal)
    _event_manager.register_task_handler("add_constraint_concentric", handle_add_constraint_concentric)
    _event_manager.register_task_handler("add_constraint_fix", handle_add_constraint_fix)
    _event_manager.register_task_handler("add_dimension", handle_add_dimension)

    # Phase 2: Creation handlers - Features
    _event_manager.register_task_handler("extrude", handle_extrude)
    _event_manager.register_task_handler("revolve", handle_revolve)
    _event_manager.register_task_handler("fillet", handle_fillet)
    _event_manager.register_task_handler("chamfer", handle_chamfer)
    _event_manager.register_task_handler("create_hole", handle_create_hole)

    # Phase 8a: Advanced feature handlers
    _event_manager.register_task_handler("sweep", handle_sweep)
    _event_manager.register_task_handler("loft", handle_loft)
    _event_manager.register_task_handler("create_sphere", handle_create_sphere)
    _event_manager.register_task_handler("create_torus", handle_create_torus)
    _event_manager.register_task_handler("create_coil", handle_create_coil)
    _event_manager.register_task_handler("create_pipe", handle_create_pipe)

    # Phase 8b: Feature pattern handlers
    _event_manager.register_task_handler("rectangular_pattern", handle_rectangular_pattern)
    _event_manager.register_task_handler("circular_pattern", handle_circular_pattern)
    _event_manager.register_task_handler("mirror_feature", handle_mirror_feature)

    # Phase 8c: Specialized feature handlers
    _event_manager.register_task_handler("create_thread", handle_create_thread)
    _event_manager.register_task_handler("thicken", handle_thicken)
    _event_manager.register_task_handler("emboss", handle_emboss)

    # Construction plane handlers
    _event_manager.register_task_handler("create_offset_plane", handle_create_offset_plane)
    _event_manager.register_task_handler("create_angle_plane", handle_create_angle_plane)
    _event_manager.register_task_handler("create_three_point_plane", handle_create_three_point_plane)
    _event_manager.register_task_handler("create_midplane", handle_create_midplane)

    # Phase 3: Modification handlers
    _event_manager.register_task_handler("move_body", handle_move_body)
    _event_manager.register_task_handler("rotate_body", handle_rotate_body)
    _event_manager.register_task_handler("modify_feature", handle_modify_feature)
    _event_manager.register_task_handler("update_parameter", handle_update_parameter)
    _event_manager.register_task_handler("delete_body", handle_delete_body)
    _event_manager.register_task_handler("delete_feature", handle_delete_feature)
    _event_manager.register_task_handler("edit_sketch", handle_edit_sketch)

    # MODIFY menu tools
    _event_manager.register_task_handler("combine", handle_combine)
    _event_manager.register_task_handler("split_body", handle_split_body)
    _event_manager.register_task_handler("shell", handle_shell)

    # Phase 4: Validation handlers
    _event_manager.register_task_handler("measure_distance", handle_measure_distance)
    _event_manager.register_task_handler("measure_angle", handle_measure_angle)
    _event_manager.register_task_handler("check_interference", handle_check_interference)
    _event_manager.register_task_handler("get_body_properties", handle_get_body_properties)
    _event_manager.register_task_handler("get_sketch_status", handle_get_sketch_status)

    # Viewport handlers
    _event_manager.register_task_handler("take_screenshot", handle_take_screenshot)
    _event_manager.register_task_handler("set_camera", handle_set_camera)
    _event_manager.register_task_handler("get_camera", handle_get_camera)
    _event_manager.register_task_handler("set_view", handle_set_view)
    _event_manager.register_task_handler("fit_view", handle_fit_view)

    # Phase 5: Assembly handlers - Components
    _event_manager.register_task_handler("create_component", handle_create_component)
    _event_manager.register_task_handler("get_components", handle_get_components)
    _event_manager.register_task_handler("get_component_by_id", handle_get_component_by_id)
    _event_manager.register_task_handler("activate_component", handle_activate_component)
    _event_manager.register_task_handler("get_component_bodies", handle_get_component_bodies)

    # Phase 5: Assembly handlers - Occurrences
    _event_manager.register_task_handler("get_occurrences", handle_get_occurrences)
    _event_manager.register_task_handler("move_occurrence", handle_move_occurrence)

    # Phase 5: Assembly handlers - Joints
    _event_manager.register_task_handler("create_joint", handle_create_joint)
    _event_manager.register_task_handler("create_joint_between_occurrences", handle_create_joint_between_occurrences)
    _event_manager.register_task_handler("get_joints", handle_get_joints)
    _event_manager.register_task_handler("get_joint_by_id", handle_get_joint_by_id)


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

    # Phase 7a: Advanced sketch geometry routes
    FusionHTTPHandler.register_route("POST", "/sketch/polygon", "draw_polygon")
    FusionHTTPHandler.register_route("POST", "/sketch/ellipse", "draw_ellipse")
    FusionHTTPHandler.register_route("POST", "/sketch/slot", "draw_slot")
    FusionHTTPHandler.register_route("POST", "/sketch/spline", "draw_spline")
    FusionHTTPHandler.register_route("POST", "/sketch/point", "draw_point")

    # Phase 7b: Sketch patterns & operations routes
    FusionHTTPHandler.register_route("POST", "/sketch/mirror", "sketch_mirror")
    FusionHTTPHandler.register_route("POST", "/sketch/circular_pattern", "sketch_circular_pattern")
    FusionHTTPHandler.register_route("POST", "/sketch/rectangular_pattern", "sketch_rectangular_pattern")
    FusionHTTPHandler.register_route("POST", "/sketch/project", "project_geometry")
    FusionHTTPHandler.register_route("POST", "/sketch/text", "add_sketch_text")

    # Phase 7c: Sketch constraints & dimensions routes
    FusionHTTPHandler.register_route("POST", "/sketch/constraint/horizontal", "add_constraint_horizontal")
    FusionHTTPHandler.register_route("POST", "/sketch/constraint/vertical", "add_constraint_vertical")
    FusionHTTPHandler.register_route("POST", "/sketch/constraint/coincident", "add_constraint_coincident")
    FusionHTTPHandler.register_route("POST", "/sketch/constraint/perpendicular", "add_constraint_perpendicular")
    FusionHTTPHandler.register_route("POST", "/sketch/constraint/parallel", "add_constraint_parallel")
    FusionHTTPHandler.register_route("POST", "/sketch/constraint/tangent", "add_constraint_tangent")
    FusionHTTPHandler.register_route("POST", "/sketch/constraint/equal", "add_constraint_equal")
    FusionHTTPHandler.register_route("POST", "/sketch/constraint/concentric", "add_constraint_concentric")
    FusionHTTPHandler.register_route("POST", "/sketch/constraint/fix", "add_constraint_fix")
    FusionHTTPHandler.register_route("POST", "/sketch/dimension", "add_dimension")

    # Phase 2: Feature creation routes
    FusionHTTPHandler.register_route("POST", "/create/extrude", "extrude")
    FusionHTTPHandler.register_route("POST", "/create/revolve", "revolve")
    FusionHTTPHandler.register_route("POST", "/create/fillet", "fillet")
    FusionHTTPHandler.register_route("POST", "/create/chamfer", "chamfer")
    FusionHTTPHandler.register_route("POST", "/create/hole", "create_hole")

    # Phase 8a: Advanced feature creation routes
    FusionHTTPHandler.register_route("POST", "/create/sweep", "sweep")
    FusionHTTPHandler.register_route("POST", "/create/loft", "loft")
    FusionHTTPHandler.register_route("POST", "/create/sphere", "create_sphere")
    FusionHTTPHandler.register_route("POST", "/create/torus", "create_torus")
    FusionHTTPHandler.register_route("POST", "/create/coil", "create_coil")
    FusionHTTPHandler.register_route("POST", "/create/pipe", "create_pipe")

    # Phase 8b: Feature pattern routes
    FusionHTTPHandler.register_route("POST", "/pattern/rectangular", "rectangular_pattern")
    FusionHTTPHandler.register_route("POST", "/pattern/circular", "circular_pattern")
    FusionHTTPHandler.register_route("POST", "/pattern/mirror", "mirror_feature")

    # Phase 8c: Specialized feature routes
    FusionHTTPHandler.register_route("POST", "/create/thread", "create_thread")
    FusionHTTPHandler.register_route("POST", "/create/thicken", "thicken")
    FusionHTTPHandler.register_route("POST", "/create/emboss", "emboss")

    # Construction plane routes
    FusionHTTPHandler.register_route("POST", "/create/plane/offset", "create_offset_plane")
    FusionHTTPHandler.register_route("POST", "/create/plane/angle", "create_angle_plane")
    FusionHTTPHandler.register_route("POST", "/create/plane/three_points", "create_three_point_plane")
    FusionHTTPHandler.register_route("POST", "/create/plane/midplane", "create_midplane")


def _register_modification_routes() -> None:
    """Register HTTP routes for modification endpoints."""
    # Phase 3: Move/Rotate routes
    FusionHTTPHandler.register_route("POST", "/modify/move_body", "move_body")
    FusionHTTPHandler.register_route("POST", "/modify/rotate_body", "rotate_body")

    # Phase 3: Feature modification routes
    FusionHTTPHandler.register_route("POST", "/modify/feature", "modify_feature")
    FusionHTTPHandler.register_route("POST", "/modify/parameter", "update_parameter")

    # Phase 3: Delete routes
    FusionHTTPHandler.register_route("POST", "/delete/body", "delete_body")
    FusionHTTPHandler.register_route("POST", "/delete/feature", "delete_feature")

    # Phase 3: Sketch edit routes
    FusionHTTPHandler.register_route("POST", "/modify/sketch", "edit_sketch")

    # MODIFY menu tools
    FusionHTTPHandler.register_route("POST", "/modify/combine", "combine")
    FusionHTTPHandler.register_route("POST", "/modify/split_body", "split_body")
    FusionHTTPHandler.register_route("POST", "/modify/shell", "shell")


def _register_validation_routes() -> None:
    """Register HTTP routes for validation endpoints."""
    # Phase 4: Measurement routes
    FusionHTTPHandler.register_route("POST", "/validate/measure_distance", "measure_distance")
    FusionHTTPHandler.register_route("POST", "/validate/measure_angle", "measure_angle")

    # Phase 4: Interference detection routes
    FusionHTTPHandler.register_route("POST", "/validate/check_interference", "check_interference")

    # Phase 4: Property and status routes
    FusionHTTPHandler.register_route("POST", "/validate/body_properties", "get_body_properties")
    FusionHTTPHandler.register_route("POST", "/validate/sketch_status", "get_sketch_status")


def _register_viewport_routes() -> None:
    """Register HTTP routes for viewport endpoints."""
    FusionHTTPHandler.register_route("POST", "/viewport/screenshot", "take_screenshot")
    FusionHTTPHandler.register_route("POST", "/viewport/camera", "set_camera")
    FusionHTTPHandler.register_route("GET", "/viewport/camera/get", "get_camera")
    FusionHTTPHandler.register_route("POST", "/viewport/camera/get", "get_camera")
    FusionHTTPHandler.register_route("POST", "/viewport/view", "set_view")
    FusionHTTPHandler.register_route("POST", "/viewport/fit", "fit_view")


def _register_assembly_routes() -> None:
    """Register HTTP routes for assembly endpoints."""
    # Phase 5: Component routes
    FusionHTTPHandler.register_route("POST", "/assembly/create_component", "create_component")
    FusionHTTPHandler.register_route("GET", "/assembly/components", "get_components")
    FusionHTTPHandler.register_route("POST", "/assembly/components", "get_components")
    FusionHTTPHandler.register_route("POST", "/assembly/component", "get_component_by_id")
    FusionHTTPHandler.register_route("POST", "/assembly/activate_component", "activate_component")
    FusionHTTPHandler.register_route("POST", "/assembly/component_bodies", "get_component_bodies")

    # Phase 5: Occurrence routes
    FusionHTTPHandler.register_route("POST", "/assembly/occurrences", "get_occurrences")
    FusionHTTPHandler.register_route("GET", "/assembly/occurrences", "get_occurrences")
    FusionHTTPHandler.register_route("POST", "/assembly/move_occurrence", "move_occurrence")

    # Phase 5: Joint routes
    FusionHTTPHandler.register_route("POST", "/assembly/create_joint", "create_joint")
    FusionHTTPHandler.register_route("POST", "/assembly/create_joint_occurrences", "create_joint_between_occurrences")
    FusionHTTPHandler.register_route("GET", "/assembly/joints", "get_joints")
    FusionHTTPHandler.register_route("POST", "/assembly/joints", "get_joints")
    FusionHTTPHandler.register_route("POST", "/assembly/joint", "get_joint_by_id")


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
