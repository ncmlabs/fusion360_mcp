"""HTTP request handlers for Fusion 360 MCP Add-in."""

from .query_handlers import (
    handle_get_design_state,
    handle_get_bodies,
    handle_get_body_by_id,
    handle_get_sketches,
    handle_get_sketch_by_id,
    handle_get_parameters,
    handle_get_timeline,
)

from .creation_handlers import (
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

from .modification_handlers import (
    handle_move_body,
    handle_rotate_body,
    handle_modify_feature,
    handle_update_parameter,
    handle_delete_body,
    handle_delete_feature,
    handle_edit_sketch,
)

from .validation_handlers import (
    handle_measure_distance,
    handle_measure_angle,
    handle_check_interference,
    handle_get_body_properties,
    handle_get_sketch_status,
)

__all__ = [
    # Query handlers
    "handle_get_design_state",
    "handle_get_bodies",
    "handle_get_body_by_id",
    "handle_get_sketches",
    "handle_get_sketch_by_id",
    "handle_get_parameters",
    "handle_get_timeline",
    # Creation handlers - Bodies
    "handle_create_box",
    "handle_create_cylinder",
    # Creation handlers - Sketches
    "handle_create_sketch",
    "handle_draw_line",
    "handle_draw_circle",
    "handle_draw_rectangle",
    "handle_draw_arc",
    # Creation handlers - Features
    "handle_extrude",
    "handle_revolve",
    "handle_fillet",
    "handle_chamfer",
    "handle_create_hole",
    # Modification handlers
    "handle_move_body",
    "handle_rotate_body",
    "handle_modify_feature",
    "handle_update_parameter",
    "handle_delete_body",
    "handle_delete_feature",
    "handle_edit_sketch",
    # Validation handlers
    "handle_measure_distance",
    "handle_measure_angle",
    "handle_check_interference",
    "handle_get_body_properties",
    "handle_get_sketch_status",
]
