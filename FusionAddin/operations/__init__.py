"""Operations module for Fusion 360 MCP Add-in.

This module contains the actual Fusion 360 API operations for creating
and modifying geometry. Operations are called from handlers and return
structured results.
"""

from .body_ops import (
    create_box,
    create_cylinder,
)
from .sketch_ops import (
    create_sketch,
    draw_line,
    draw_circle,
    draw_rectangle,
    draw_arc,
)
from .feature_ops import (
    extrude,
    revolve,
    fillet,
    chamfer,
    create_hole,
)

__all__ = [
    # Body operations
    "create_box",
    "create_cylinder",
    # Sketch operations
    "create_sketch",
    "draw_line",
    "draw_circle",
    "draw_rectangle",
    "draw_arc",
    # Feature operations
    "extrude",
    "revolve",
    "fillet",
    "chamfer",
    "create_hole",
]
