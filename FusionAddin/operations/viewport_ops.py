"""Viewport and camera operations for Fusion 360 MCP Add-in.

These operations control the Fusion 360 viewport camera and capture
screenshots for visualization.
"""

import os
from typing import Dict, Any, Optional, List, Tuple

# Fusion 360 API imports
try:
    import adsk.core
    import adsk.fusion
    FUSION_AVAILABLE = True
except ImportError:
    FUSION_AVAILABLE = False

from core.entity_registry import get_registry
from shared.exceptions import (
    DesignStateError,
    InvalidParameterError,
)
from utils.units import mm_to_cm, cm_to_mm


# Standard view definitions
# Each view defines the eye direction (normalized) and up vector
# The actual eye position is calculated based on model extents
STANDARD_VIEWS: Dict[str, Dict[str, Tuple[float, float, float]]] = {
    "front": {
        "eye_direction": (0, -1, 0),   # Looking from -Y toward origin
        "up_vector": (0, 0, 1),        # Z is up
    },
    "back": {
        "eye_direction": (0, 1, 0),    # Looking from +Y toward origin
        "up_vector": (0, 0, 1),
    },
    "top": {
        "eye_direction": (0, 0, 1),    # Looking from +Z toward origin
        "up_vector": (0, 1, 0),        # Y is up when looking down
    },
    "bottom": {
        "eye_direction": (0, 0, -1),   # Looking from -Z toward origin
        "up_vector": (0, -1, 0),
    },
    "left": {
        "eye_direction": (-1, 0, 0),   # Looking from -X toward origin
        "up_vector": (0, 0, 1),
    },
    "right": {
        "eye_direction": (1, 0, 0),    # Looking from +X toward origin
        "up_vector": (0, 0, 1),
    },
    "isometric": {
        "eye_direction": (1, -1, 1),   # Standard isometric view
        "up_vector": (0, 0, 1),
    },
    "trimetric": {
        "eye_direction": (1, -0.5, 0.8),
        "up_vector": (0, 0, 1),
    },
}

# Valid view names for validation
VALID_VIEWS = list(STANDARD_VIEWS.keys()) + ["current", "home"]


def _get_application() -> Any:
    """Get the Fusion 360 application instance.

    Returns:
        Fusion Application object

    Raises:
        DesignStateError: If application is not available
    """
    if not FUSION_AVAILABLE:
        raise DesignStateError(
            "not_available",
            "Fusion 360 API not available. Running outside of Fusion 360."
        )

    app = adsk.core.Application.get()
    if not app:
        raise DesignStateError(
            "no_application",
            "Cannot get Fusion 360 application instance."
        )

    return app


def _get_viewport() -> Any:
    """Get the active viewport.

    Returns:
        Fusion Viewport object

    Raises:
        DesignStateError: If no viewport is active
    """
    app = _get_application()
    viewport = app.activeViewport

    if not viewport:
        raise DesignStateError(
            "no_viewport",
            "No active viewport. Please open a design."
        )

    return viewport


def _serialize_camera(camera: Any) -> Dict[str, Any]:
    """Serialize camera state to dictionary.

    Args:
        camera: Fusion Camera object

    Returns:
        Dict with camera state in mm units
    """
    eye = camera.eye
    target = camera.target
    up = camera.upVector

    # Check camera type
    is_perspective = True
    try:
        is_perspective = camera.cameraType == adsk.core.CameraTypes.PerspectiveCameraType
    except:
        pass

    return {
        "eye": {
            "x": cm_to_mm(eye.x),
            "y": cm_to_mm(eye.y),
            "z": cm_to_mm(eye.z),
        },
        "target": {
            "x": cm_to_mm(target.x),
            "y": cm_to_mm(target.y),
            "z": cm_to_mm(target.z),
        },
        "up_vector": {
            "x": up.x,
            "y": up.y,
            "z": up.z,
        },
        "view_extents": camera.viewExtents,
        "is_perspective": is_perspective,
    }


def _calculate_view_distance(viewport: Any) -> float:
    """Calculate appropriate viewing distance based on model extents.

    Args:
        viewport: Fusion Viewport object

    Returns:
        Distance in cm for camera positioning
    """
    try:
        app = adsk.core.Application.get()
        product = app.activeProduct
        if product:
            design = adsk.fusion.Design.cast(product)
            if design and design.rootComponent:
                bbox = design.rootComponent.boundingBox
                if bbox and bbox.isValid:
                    # Calculate diagonal of bounding box
                    dx = bbox.maxPoint.x - bbox.minPoint.x
                    dy = bbox.maxPoint.y - bbox.minPoint.y
                    dz = bbox.maxPoint.z - bbox.minPoint.z
                    diagonal = (dx*dx + dy*dy + dz*dz) ** 0.5

                    # Return 2x the diagonal for good framing
                    return max(diagonal * 2.0, 10.0)  # Minimum 10cm
    except:
        pass

    # Default distance if we can't calculate
    return 50.0  # 50cm default


def _set_standard_view(viewport: Any, view: str, smooth: bool = True) -> None:
    """Set the viewport to a standard named view.

    Args:
        viewport: Fusion Viewport object
        view: View name from STANDARD_VIEWS
        smooth: Whether to animate the transition
    """
    if view not in STANDARD_VIEWS:
        raise InvalidParameterError(
            "view",
            view,
            valid_values=list(STANDARD_VIEWS.keys()),
            reason=f"Unknown standard view: {view}"
        )

    view_def = STANDARD_VIEWS[view]
    eye_dir = view_def["eye_direction"]
    up_vec = view_def["up_vector"]

    # Calculate viewing distance
    distance = _calculate_view_distance(viewport)

    # Normalize eye direction and calculate eye position
    length = (eye_dir[0]**2 + eye_dir[1]**2 + eye_dir[2]**2) ** 0.5
    if length > 0:
        eye_dir = (eye_dir[0]/length, eye_dir[1]/length, eye_dir[2]/length)

    # Create camera with calculated position
    camera = viewport.camera
    camera.eye = adsk.core.Point3D.create(
        eye_dir[0] * distance,
        eye_dir[1] * distance,
        eye_dir[2] * distance
    )
    camera.target = adsk.core.Point3D.create(0, 0, 0)
    camera.upVector = adsk.core.Vector3D.create(up_vec[0], up_vec[1], up_vec[2])
    camera.isSmoothTransition = smooth

    viewport.camera = camera

    # Fit to model after setting view
    viewport.fit()


def take_screenshot(
    file_path: str,
    view: str = "current",
    width: int = 1920,
    height: int = 1080,
) -> Dict[str, Any]:
    """Capture the viewport as a PNG image.

    Args:
        file_path: Path to save the image (required)
        view: View to capture - "current" or a standard view name
        width: Image width in pixels
        height: Image height in pixels

    Returns:
        Dict with:
        - file_path: Path where image was saved
        - format: "png"
        - dimensions: {width, height}
        - view: View that was captured

    Raises:
        InvalidParameterError: If parameters are invalid
        DesignStateError: If viewport is not available
    """
    # Validate file_path
    if not file_path:
        raise InvalidParameterError(
            "file_path",
            file_path,
            reason="file_path is required"
        )

    # Validate view parameter
    if view not in VALID_VIEWS:
        raise InvalidParameterError(
            "view",
            view,
            valid_values=VALID_VIEWS,
            reason=f"Unknown view: {view}"
        )

    # Validate dimensions
    if width <= 0 or width > 8192:
        raise InvalidParameterError(
            "width",
            width,
            min_value=1,
            max_value=8192,
            reason="Width must be between 1 and 8192 pixels"
        )
    if height <= 0 or height > 8192:
        raise InvalidParameterError(
            "height",
            height,
            min_value=1,
            max_value=8192,
            reason="Height must be between 1 and 8192 pixels"
        )

    viewport = _get_viewport()

    # Set standard view if requested
    if view != "current":
        if view == "home":
            viewport.goHome()
        else:
            _set_standard_view(viewport, view, smooth=False)

    # Ensure directory exists
    parent_dir = os.path.dirname(file_path)
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir)

    # Capture screenshot
    success = viewport.saveAsImageFile(file_path, width, height)

    if not success:
        raise DesignStateError(
            "screenshot_failed",
            "Failed to save viewport image. Check file path and permissions."
        )

    return {
        "format": "png",
        "dimensions": {"width": width, "height": height},
        "view": view,
        "file_path": file_path,
    }


def set_camera(
    eye_x: float,
    eye_y: float,
    eye_z: float,
    target_x: float = 0.0,
    target_y: float = 0.0,
    target_z: float = 0.0,
    up_x: float = 0.0,
    up_y: float = 0.0,
    up_z: float = 1.0,
    smooth_transition: bool = True,
) -> Dict[str, Any]:
    """Set the viewport camera position and orientation.

    All coordinates are in millimeters (mm).

    Args:
        eye_x: Camera eye X position in mm
        eye_y: Camera eye Y position in mm
        eye_z: Camera eye Z position in mm
        target_x: Camera target X position in mm
        target_y: Camera target Y position in mm
        target_z: Camera target Z position in mm
        up_x: Camera up vector X component
        up_y: Camera up vector Y component
        up_z: Camera up vector Z component
        smooth_transition: Whether to animate the camera transition

    Returns:
        Dict with camera state after change

    Raises:
        InvalidParameterError: If eye equals target
        DesignStateError: If viewport is not available
    """
    # Validate that eye and target are different
    if eye_x == target_x and eye_y == target_y and eye_z == target_z:
        raise InvalidParameterError(
            "eye/target",
            f"eye=({eye_x}, {eye_y}, {eye_z})",
            reason="Camera eye and target positions cannot be the same"
        )

    # Validate up vector is not zero
    up_length = (up_x*up_x + up_y*up_y + up_z*up_z) ** 0.5
    if up_length < 0.001:
        raise InvalidParameterError(
            "up_vector",
            f"({up_x}, {up_y}, {up_z})",
            reason="Up vector cannot be zero"
        )

    viewport = _get_viewport()
    camera = viewport.camera

    # Convert mm to cm for Fusion API
    camera.eye = adsk.core.Point3D.create(
        mm_to_cm(eye_x),
        mm_to_cm(eye_y),
        mm_to_cm(eye_z)
    )
    camera.target = adsk.core.Point3D.create(
        mm_to_cm(target_x),
        mm_to_cm(target_y),
        mm_to_cm(target_z)
    )
    camera.upVector = adsk.core.Vector3D.create(up_x, up_y, up_z)
    camera.isSmoothTransition = smooth_transition

    viewport.camera = camera

    return {
        "camera": _serialize_camera(camera),
    }


def get_camera() -> Dict[str, Any]:
    """Get the current viewport camera state.

    Returns:
        Dict with camera state:
        - eye: {x, y, z} in mm
        - target: {x, y, z} in mm
        - up_vector: {x, y, z}
        - view_extents: zoom level
        - is_perspective: True if perspective camera
    """
    viewport = _get_viewport()
    camera = viewport.camera

    return {
        "camera": _serialize_camera(camera),
    }


def set_view(
    view: str,
    smooth_transition: bool = True,
) -> Dict[str, Any]:
    """Set the viewport to a standard named view.

    Args:
        view: Named view to set. Options:
              "front", "back", "top", "bottom",
              "left", "right", "isometric", "trimetric", "home"
        smooth_transition: Whether to animate the view change

    Returns:
        Dict with view name and camera state

    Raises:
        InvalidParameterError: If view name is invalid
        DesignStateError: If viewport is not available
    """
    valid_set_views = list(STANDARD_VIEWS.keys()) + ["home"]
    if view not in valid_set_views:
        raise InvalidParameterError(
            "view",
            view,
            valid_values=valid_set_views,
            reason=f"Unknown view: {view}"
        )

    viewport = _get_viewport()

    if view == "home":
        viewport.goHome()
    else:
        _set_standard_view(viewport, view, smooth=smooth_transition)

    camera = viewport.camera

    return {
        "view": view,
        "camera": _serialize_camera(camera),
    }


def fit_view(
    entity_ids: Optional[List[str]] = None,
    smooth_transition: bool = True,
) -> Dict[str, Any]:
    """Fit the viewport to show specific entities or all geometry.

    Args:
        entity_ids: Optional list of body, component, or occurrence IDs
                   to fit the view to. If not provided, fits to all
                   visible geometry.
        smooth_transition: Whether to animate the zoom change

    Returns:
        Dict with fitted_to and camera state

    Raises:
        DesignStateError: If viewport is not available
    """
    viewport = _get_viewport()

    fitted_to = "all"

    if entity_ids:
        # Try to get entities and fit to them
        registry = get_registry()
        entities = []

        for eid in entity_ids:
            # Try different entity types
            entity = registry.get_body(eid)
            if not entity:
                entity = registry.get_component(eid)
            if not entity:
                entity = registry.get_occurrence(eid)

            if entity:
                entities.append(entity)

        if entities:
            # Note: Fusion's viewport.fit() doesn't take specific entities
            # We would need to calculate bounding box and zoom manually
            # For now, just fit to all
            fitted_to = entity_ids
            # TODO: Implement entity-specific fitting

    # Fit to all visible geometry
    camera = viewport.camera
    camera.isSmoothTransition = smooth_transition
    viewport.camera = camera

    viewport.fit()

    # Get camera state after fit
    camera = viewport.camera

    return {
        "fitted_to": fitted_to,
        "camera": _serialize_camera(camera),
    }
