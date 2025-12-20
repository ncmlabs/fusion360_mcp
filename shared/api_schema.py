"""API schema definitions shared between Server and Add-in.

This module defines the HTTP API contract between the MCP Server
and the Fusion 360 Add-in.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class APIRequest:
    """Base API request structure."""
    correlation_id: Optional[str] = None


@dataclass
class APIResponse:
    """Base API response structure."""
    success: bool = True
    correlation_id: Optional[str] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {"success": self.success}
        if self.correlation_id:
            result["correlation_id"] = self.correlation_id
        if not self.success:
            if self.error:
                result["error"] = self.error
            if self.error_type:
                result["error_type"] = self.error_type
        if self.data:
            result["data"] = self.data
        return result


# API Endpoints
ENDPOINTS = {
    # Health & Status
    "health": "/health",
    "test_connection": "/test",

    # Query endpoints (Phase 1)
    "get_design_state": "/query/design_state",
    "get_bodies": "/query/bodies",
    "get_body": "/query/body",
    "get_sketches": "/query/sketches",
    "get_sketch": "/query/sketch",
    "get_timeline": "/query/timeline",
    "get_parameters": "/query/parameters",

    # Creation endpoints (Phase 2)
    "create_box": "/create/box",
    "create_cylinder": "/create/cylinder",
    "create_sketch": "/create/sketch",
    "create_hole": "/create/hole",
    "extrude": "/create/extrude",
    "revolve": "/create/revolve",
    "sweep": "/create/sweep",
    "loft": "/create/loft",

    # Modification endpoints (Phase 3)
    "move_body": "/modify/move_body",
    "rotate_body": "/modify/rotate_body",
    "modify_feature": "/modify/feature",
    "update_parameter": "/modify/parameter",
    "delete_body": "/modify/delete_body",
    "delete_feature": "/modify/delete_feature",

    # Validation endpoints (Phase 4)
    "measure_distance": "/validate/measure_distance",
    "check_interference": "/validate/interference",
    "get_body_properties": "/validate/body_properties",

    # Assembly endpoints (Phase 5)
    "create_component": "/assembly/create_component",
    "create_joint": "/assembly/create_joint",
    "move_occurrence": "/assembly/move_occurrence",

    # Export
    "export_step": "/export/step",
    "export_stl": "/export/stl",

    # Viewport
    "take_screenshot": "/viewport/screenshot",
    "set_camera": "/viewport/camera",
    "get_camera": "/viewport/camera/get",
    "set_view": "/viewport/view",
    "fit_view": "/viewport/fit",

    # Utility
    "undo": "/utility/undo",
    "delete_all": "/utility/delete_all",
}


def get_endpoint(name: str) -> str:
    """Get endpoint path by name."""
    return ENDPOINTS.get(name, f"/unknown/{name}")
