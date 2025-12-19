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

from .assembly_handlers import (
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
    # Assembly handlers
    "handle_create_component",
    "handle_get_components",
    "handle_get_component_by_id",
    "handle_activate_component",
    "handle_get_component_bodies",
    "handle_get_occurrences",
    "handle_move_occurrence",
    "handle_create_joint",
    "handle_create_joint_between_occurrences",
    "handle_get_joints",
    "handle_get_joint_by_id",
]
