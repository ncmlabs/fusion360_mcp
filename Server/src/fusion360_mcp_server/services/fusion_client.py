"""Async HTTP client for Fusion 360 add-in communication.

Provides a typed interface for making requests to the Fusion 360 add-in
HTTP server, with retry logic and response parsing.
"""

import asyncio
from typing import Optional, Dict, Any, List
import httpx

from ..config import get_config, ServerConfig
from ..logging import get_logger
from ..exceptions import (
    ConnectionError as FusionConnectionError,
    TimeoutError as FusionTimeoutError,
    FusionMCPError,
    EntityNotFoundError,
    InvalidParameterError,
    DesignStateError,
)


logger = get_logger(__name__)


class FusionClient:
    """Async HTTP client for Fusion 360 add-in communication.

    Provides methods for querying design state, bodies, sketches,
    parameters, and timeline from the Fusion 360 add-in.

    Usage:
        async with FusionClient() as client:
            state = await client.get_design_state()
            bodies = await client.get_bodies()

    Or without context manager:
        client = FusionClient()
        await client.connect()
        try:
            state = await client.get_design_state()
        finally:
            await client.disconnect()
    """

    def __init__(self, config: Optional[ServerConfig] = None) -> None:
        """Initialize client with optional config.

        Args:
            config: Server configuration (uses global config if not provided)
        """
        self.config = config or get_config()
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "FusionClient":
        """Async context manager entry - creates HTTP client."""
        await self.connect()
        return self

    async def __aexit__(self, *args) -> None:
        """Async context manager exit - closes HTTP client."""
        await self.disconnect()

    async def connect(self) -> None:
        """Create the async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.fusion_base_url,
                timeout=httpx.Timeout(self.config.request_timeout),
            )
            logger.debug(
                "FusionClient connected",
                base_url=self.config.fusion_base_url,
            )

    async def disconnect(self) -> None:
        """Close the async HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.debug("FusionClient disconnected")

    async def _ensure_connected(self) -> None:
        """Ensure client is connected."""
        if self._client is None:
            await self.connect()

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET or POST)
            endpoint: API endpoint path
            data: Optional request body data

        Returns:
            Response data dict

        Raises:
            FusionConnectionError: Cannot connect to add-in
            FusionTimeoutError: Request timed out
            FusionMCPError: Error from add-in
        """
        await self._ensure_connected()

        last_error: Optional[Exception] = None

        for attempt in range(self.config.max_retries):
            try:
                if method.upper() == "GET":
                    response = await self._client.get(endpoint, params=data)
                else:
                    response = await self._client.post(endpoint, json=data or {})

                result = response.json()
                logger.debug(
                    "Fusion request completed",
                    endpoint=endpoint,
                    status=response.status_code,
                    attempt=attempt + 1,
                )

                # Check for error response
                if not result.get("success", True):
                    self._handle_error_response(result)

                return result.get("data", result)

            except httpx.ConnectError as e:
                last_error = e
                logger.warning(
                    "Connection error, retrying",
                    endpoint=endpoint,
                    attempt=attempt + 1,
                    max_retries=self.config.max_retries,
                )
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay)

            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(
                    "Timeout error, retrying",
                    endpoint=endpoint,
                    attempt=attempt + 1,
                    max_retries=self.config.max_retries,
                )
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay)

        # All retries exhausted
        if isinstance(last_error, httpx.ConnectError):
            raise FusionConnectionError(
                self.config.fusion_host,
                self.config.fusion_port,
            )
        elif isinstance(last_error, httpx.TimeoutException):
            raise FusionTimeoutError(
                endpoint,
                self.config.request_timeout,
            )
        else:
            raise FusionMCPError(
                "request_failed",
                f"Request to {endpoint} failed after {self.config.max_retries} retries",
                suggestion="Check that the Fusion 360 add-in is running and accessible.",
            )

    def _handle_error_response(self, result: Dict[str, Any]) -> None:
        """Handle error response from add-in.

        Args:
            result: Response dict with error info

        Raises:
            Appropriate FusionMCPError subclass
        """
        error_type = result.get("error_type", "unknown")
        error_msg = result.get("error", "Unknown error")
        context = result.get("context", {})

        # Map error types to exceptions
        if error_type == "EntityNotFound":
            raise EntityNotFoundError(
                context.get("entity_type", "Entity"),
                context.get("requested_id", "unknown"),
                context.get("available_entities", []),
            )
        elif error_type == "InvalidParameter":
            raise InvalidParameterError(
                context.get("parameter_name", "unknown"),
                context.get("current_value"),
                reason=error_msg,
            )
        elif error_type == "DesignState":
            raise DesignStateError(
                context.get("current_state", "unknown"),
                error_msg,
            )
        else:
            raise FusionMCPError(
                error_type,
                error_msg,
                suggestion=result.get("suggestion", ""),
            )

    # --- Query Methods ---

    async def get_design_state(self) -> Dict[str, Any]:
        """Get current design state summary.

        Returns:
            Dict with design info including name, units, counts
        """
        result = await self._request("GET", "/query/design_state")
        return result.get("design", result)

    async def get_bodies(
        self,
        component_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all bodies in design or component.

        Args:
            component_id: Optional component ID to filter bodies

        Returns:
            List of body summary dicts
        """
        data = {"component_id": component_id} if component_id else None
        result = await self._request("POST", "/query/bodies", data)
        return result.get("bodies", [])

    async def get_body_by_id(
        self,
        body_id: str,
        include_faces: bool = False,
        include_edges: bool = False,
        include_vertices: bool = False,
    ) -> Dict[str, Any]:
        """Get detailed body info by ID.

        Args:
            body_id: Body ID to retrieve
            include_faces: Include face geometry details
            include_edges: Include edge geometry details
            include_vertices: Include vertex positions

        Returns:
            Full body dict with topology if requested
        """
        result = await self._request("POST", "/query/body", {
            "body_id": body_id,
            "include_faces": include_faces,
            "include_edges": include_edges,
            "include_vertices": include_vertices,
        })
        return result.get("body", result)

    async def get_sketches(
        self,
        component_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all sketches in design or component.

        Args:
            component_id: Optional component ID to filter sketches

        Returns:
            List of sketch summary dicts
        """
        data = {"component_id": component_id} if component_id else None
        result = await self._request("POST", "/query/sketches", data)
        return result.get("sketches", [])

    async def get_sketch_by_id(
        self,
        sketch_id: str,
        include_curves: bool = True,
        include_constraints: bool = True,
        include_dimensions: bool = True,
        include_profiles: bool = False,
    ) -> Dict[str, Any]:
        """Get detailed sketch info by ID.

        Args:
            sketch_id: Sketch ID to retrieve
            include_curves: Include curve details
            include_constraints: Include constraint details
            include_dimensions: Include dimension details
            include_profiles: Include profile details

        Returns:
            Full sketch dict with geometry
        """
        result = await self._request("POST", "/query/sketch", {
            "sketch_id": sketch_id,
            "include_curves": include_curves,
            "include_constraints": include_constraints,
            "include_dimensions": include_dimensions,
            "include_profiles": include_profiles,
        })
        return result.get("sketch", result)

    async def get_parameters(
        self,
        user_only: bool = False,
        favorites_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get all parameters in design.

        Args:
            user_only: Only return user parameters
            favorites_only: Only return favorite parameters

        Returns:
            List of parameter dicts
        """
        result = await self._request("POST", "/query/parameters", {
            "user_only": user_only,
            "favorites_only": favorites_only,
        })
        return result.get("parameters", [])

    async def get_timeline(
        self,
        include_suppressed: bool = True,
        include_rolled_back: bool = False,
    ) -> Dict[str, Any]:
        """Get design timeline (feature history).

        Args:
            include_suppressed: Include suppressed features
            include_rolled_back: Include rolled back features

        Returns:
            Dict with timeline entries and marker position
        """
        result = await self._request("POST", "/query/timeline", {
            "include_suppressed": include_suppressed,
            "include_rolled_back": include_rolled_back,
        })
        return result

    # --- Health Check ---

    async def health_check(self) -> Dict[str, Any]:
        """Check if add-in is responsive.

        Returns:
            Dict with status, message, and version
        """
        try:
            result = await self._request("GET", "/health")
            return {
                "healthy": result.get("status") == "healthy",
                "status": result.get("status", "unknown"),
                "message": result.get("message", ""),
                "version": result.get("version", "unknown"),
            }
        except Exception as e:
            return {
                "healthy": False,
                "status": "unreachable",
                "message": str(e),
                "version": "unknown",
            }

    async def get_version(self) -> Dict[str, Any]:
        """Get version information from add-in.

        Returns:
            Dict with addin_name, addin_version, fusion_version, api_version
        """
        return await self._request("GET", "/version")

    # --- Creation Methods ---

    async def create_box(
        self,
        width: float,
        depth: float,
        height: float,
        x: float = 0.0,
        y: float = 0.0,
        z: float = 0.0,
        name: Optional[str] = None,
        plane: str = "XY",
        component_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a box (rectangular prism).

        Args:
            width: Box width in mm
            depth: Box depth in mm
            height: Box height in mm
            x: X position of center in mm
            y: Y position of center in mm
            z: Z position/offset in mm
            name: Optional name for the body
            plane: Construction plane (XY, YZ, XZ)
            component_id: Optional component ID

        Returns:
            Dict with body and feature info
        """
        return await self._request("POST", "/create/box", {
            "width": width,
            "depth": depth,
            "height": height,
            "x": x,
            "y": y,
            "z": z,
            "name": name,
            "plane": plane,
            "component_id": component_id,
        })

    async def create_cylinder(
        self,
        radius: float,
        height: float,
        x: float = 0.0,
        y: float = 0.0,
        z: float = 0.0,
        name: Optional[str] = None,
        plane: str = "XY",
        component_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a cylinder.

        Args:
            radius: Cylinder radius in mm
            height: Cylinder height in mm
            x: X position of center in mm
            y: Y position of center in mm
            z: Z position/offset in mm
            name: Optional name for the body
            plane: Construction plane (XY, YZ, XZ)
            component_id: Optional component ID

        Returns:
            Dict with body and feature info
        """
        return await self._request("POST", "/create/cylinder", {
            "radius": radius,
            "height": height,
            "x": x,
            "y": y,
            "z": z,
            "name": name,
            "plane": plane,
            "component_id": component_id,
        })

    async def create_sketch(
        self,
        plane: str = "XY",
        name: Optional[str] = None,
        offset: float = 0.0,
        component_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new sketch.

        Args:
            plane: Construction plane (XY, YZ, XZ) or face_id
            name: Optional name for the sketch
            offset: Offset from plane in mm
            component_id: Optional component ID

        Returns:
            Dict with sketch info
        """
        return await self._request("POST", "/create/sketch", {
            "plane": plane,
            "name": name,
            "offset": offset,
            "component_id": component_id,
        })

    async def draw_line(
        self,
        sketch_id: str,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
    ) -> Dict[str, Any]:
        """Draw a line in a sketch.

        Args:
            sketch_id: ID of the sketch
            start_x: Start X coordinate in mm
            start_y: Start Y coordinate in mm
            end_x: End X coordinate in mm
            end_y: End Y coordinate in mm

        Returns:
            Dict with curve info
        """
        return await self._request("POST", "/sketch/line", {
            "sketch_id": sketch_id,
            "start_x": start_x,
            "start_y": start_y,
            "end_x": end_x,
            "end_y": end_y,
        })

    async def draw_circle(
        self,
        sketch_id: str,
        center_x: float,
        center_y: float,
        radius: float,
    ) -> Dict[str, Any]:
        """Draw a circle in a sketch.

        Args:
            sketch_id: ID of the sketch
            center_x: Center X coordinate in mm
            center_y: Center Y coordinate in mm
            radius: Circle radius in mm

        Returns:
            Dict with curve info
        """
        return await self._request("POST", "/sketch/circle", {
            "sketch_id": sketch_id,
            "center_x": center_x,
            "center_y": center_y,
            "radius": radius,
        })

    async def draw_rectangle(
        self,
        sketch_id: str,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ) -> Dict[str, Any]:
        """Draw a rectangle in a sketch.

        Args:
            sketch_id: ID of the sketch
            x1: First corner X in mm
            y1: First corner Y in mm
            x2: Opposite corner X in mm
            y2: Opposite corner Y in mm

        Returns:
            Dict with curve info
        """
        return await self._request("POST", "/sketch/rectangle", {
            "sketch_id": sketch_id,
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
        })

    async def draw_arc(
        self,
        sketch_id: str,
        center_x: float,
        center_y: float,
        radius: float,
        start_angle: float,
        end_angle: float,
    ) -> Dict[str, Any]:
        """Draw an arc in a sketch.

        Args:
            sketch_id: ID of the sketch
            center_x: Center X coordinate in mm
            center_y: Center Y coordinate in mm
            radius: Arc radius in mm
            start_angle: Start angle in degrees
            end_angle: End angle in degrees

        Returns:
            Dict with curve info
        """
        return await self._request("POST", "/sketch/arc", {
            "sketch_id": sketch_id,
            "center_x": center_x,
            "center_y": center_y,
            "radius": radius,
            "start_angle": start_angle,
            "end_angle": end_angle,
        })

    async def draw_polygon(
        self,
        sketch_id: str,
        center_x: float,
        center_y: float,
        radius: float,
        sides: int,
        rotation_angle: float = 0.0,
    ) -> Dict[str, Any]:
        """Draw a regular polygon in a sketch.

        Args:
            sketch_id: ID of the sketch
            center_x: Center X coordinate in mm
            center_y: Center Y coordinate in mm
            radius: Circumscribed radius in mm
            sides: Number of sides (3-64)
            rotation_angle: Rotation angle in degrees

        Returns:
            Dict with curve IDs and polygon info
        """
        return await self._request("POST", "/sketch/polygon", {
            "sketch_id": sketch_id,
            "center_x": center_x,
            "center_y": center_y,
            "radius": radius,
            "sides": sides,
            "rotation_angle": rotation_angle,
        })

    async def draw_ellipse(
        self,
        sketch_id: str,
        center_x: float,
        center_y: float,
        major_radius: float,
        minor_radius: float,
        rotation_angle: float = 0.0,
    ) -> Dict[str, Any]:
        """Draw an ellipse in a sketch.

        Args:
            sketch_id: ID of the sketch
            center_x: Center X coordinate in mm
            center_y: Center Y coordinate in mm
            major_radius: Major axis radius in mm
            minor_radius: Minor axis radius in mm
            rotation_angle: Rotation of major axis in degrees

        Returns:
            Dict with curve ID and ellipse info
        """
        return await self._request("POST", "/sketch/ellipse", {
            "sketch_id": sketch_id,
            "center_x": center_x,
            "center_y": center_y,
            "major_radius": major_radius,
            "minor_radius": minor_radius,
            "rotation_angle": rotation_angle,
        })

    async def draw_slot(
        self,
        sketch_id: str,
        center_x: float,
        center_y: float,
        length: float,
        width: float,
        slot_type: str = "overall",
        rotation_angle: float = 0.0,
    ) -> Dict[str, Any]:
        """Draw a slot shape in a sketch.

        Args:
            sketch_id: ID of the sketch
            center_x: Center X coordinate in mm
            center_y: Center Y coordinate in mm
            length: Slot length in mm
            width: Slot width in mm
            slot_type: "overall" or "center_to_center"
            rotation_angle: Rotation angle in degrees

        Returns:
            Dict with curve IDs and slot info
        """
        return await self._request("POST", "/sketch/slot", {
            "sketch_id": sketch_id,
            "center_x": center_x,
            "center_y": center_y,
            "length": length,
            "width": width,
            "slot_type": slot_type,
            "rotation_angle": rotation_angle,
        })

    async def draw_spline(
        self,
        sketch_id: str,
        points: List[Dict[str, float]],
        is_closed: bool = False,
    ) -> Dict[str, Any]:
        """Draw a spline through control points in a sketch.

        Args:
            sketch_id: ID of the sketch
            points: List of {x, y} point dicts in mm
            is_closed: Whether to create a closed spline

        Returns:
            Dict with curve ID and spline info
        """
        return await self._request("POST", "/sketch/spline", {
            "sketch_id": sketch_id,
            "points": points,
            "is_closed": is_closed,
        })

    async def draw_point(
        self,
        sketch_id: str,
        x: float,
        y: float,
        is_construction: bool = False,
    ) -> Dict[str, Any]:
        """Draw a point in a sketch.

        Args:
            sketch_id: ID of the sketch
            x: X coordinate in mm
            y: Y coordinate in mm
            is_construction: Mark as construction geometry

        Returns:
            Dict with point ID and info
        """
        return await self._request("POST", "/sketch/point", {
            "sketch_id": sketch_id,
            "x": x,
            "y": y,
            "is_construction": is_construction,
        })

    # --- Phase 7b: Sketch Patterns & Operations ---

    async def sketch_mirror(
        self,
        sketch_id: str,
        curve_ids: List[str],
        mirror_line_id: str,
    ) -> Dict[str, Any]:
        """Mirror sketch entities across a line.

        Args:
            sketch_id: ID of the sketch
            curve_ids: List of curve IDs to mirror
            mirror_line_id: ID of the line to mirror across

        Returns:
            Dict with mirrored curve IDs and info
        """
        return await self._request("POST", "/sketch/mirror", {
            "sketch_id": sketch_id,
            "curve_ids": curve_ids,
            "mirror_line_id": mirror_line_id,
        })

    async def sketch_circular_pattern(
        self,
        sketch_id: str,
        curve_ids: List[str],
        center_x: float,
        center_y: float,
        count: int,
        total_angle: float = 360.0,
    ) -> Dict[str, Any]:
        """Create a circular pattern of sketch entities.

        Args:
            sketch_id: ID of the sketch
            curve_ids: List of curve IDs to pattern
            center_x: Pattern center X in mm
            center_y: Pattern center Y in mm
            count: Number of instances (including original)
            total_angle: Total angle span in degrees

        Returns:
            Dict with pattern info and new curve IDs
        """
        return await self._request("POST", "/sketch/circular_pattern", {
            "sketch_id": sketch_id,
            "curve_ids": curve_ids,
            "center_x": center_x,
            "center_y": center_y,
            "count": count,
            "total_angle": total_angle,
        })

    async def sketch_rectangular_pattern(
        self,
        sketch_id: str,
        curve_ids: List[str],
        x_count: int,
        y_count: int,
        x_spacing: float,
        y_spacing: float,
    ) -> Dict[str, Any]:
        """Create a rectangular pattern of sketch entities.

        Args:
            sketch_id: ID of the sketch
            curve_ids: List of curve IDs to pattern
            x_count: Number of columns
            y_count: Number of rows
            x_spacing: Column spacing in mm
            y_spacing: Row spacing in mm

        Returns:
            Dict with pattern info and new curve IDs
        """
        return await self._request("POST", "/sketch/rectangular_pattern", {
            "sketch_id": sketch_id,
            "curve_ids": curve_ids,
            "x_count": x_count,
            "y_count": y_count,
            "x_spacing": x_spacing,
            "y_spacing": y_spacing,
        })

    async def project_geometry(
        self,
        sketch_id: str,
        entity_ids: List[str],
        project_type: str = "standard",
    ) -> Dict[str, Any]:
        """Project edges or faces from 3D bodies onto a sketch.

        Args:
            sketch_id: ID of the target sketch
            entity_ids: List of entity IDs to project
            project_type: "standard" or "cut_edges"

        Returns:
            Dict with projected curve IDs and info
        """
        return await self._request("POST", "/sketch/project", {
            "sketch_id": sketch_id,
            "entity_ids": entity_ids,
            "project_type": project_type,
        })

    async def wrap_sketch_to_surface(
        self,
        sketch_id: str,
        face_id: str,
        projection_type: str = "closest_point",
        direction_axis: Optional[str] = None,
        create_new_sketch: bool = True,
    ) -> Dict[str, Any]:
        """Wrap sketch curves onto a curved surface using projection.

        Projects 2D sketch geometry onto curved 3D surfaces like cylinders,
        spheres, or other curved faces using Fusion 360's projectToSurface.

        Args:
            sketch_id: ID of the source sketch containing curves to wrap
            face_id: ID of the target curved face to wrap onto
            projection_type: Projection method:
                - "closest_point": Projects each point to nearest surface point
                - "along_vector": Projects along a specific direction
            direction_axis: Required for "along_vector" type ("X", "Y", or "Z")
            create_new_sketch: If True, creates new sketch for wrapped curves

        Returns:
            Dict with wrapped curve IDs, sketch info, and projection details
        """
        data: Dict[str, Any] = {
            "sketch_id": sketch_id,
            "face_id": face_id,
            "projection_type": projection_type,
            "create_new_sketch": create_new_sketch,
        }
        if direction_axis is not None:
            data["direction_axis"] = direction_axis
        return await self._request("POST", "/sketch/wrap_to_surface", data)

    async def add_sketch_text(
        self,
        sketch_id: str,
        text: str,
        x: float,
        y: float,
        height: float,
        font_name: Optional[str] = None,
        is_bold: bool = False,
        is_italic: bool = False,
    ) -> Dict[str, Any]:
        """Add text to a sketch for engraving or embossing.

        Args:
            sketch_id: ID of the target sketch
            text: Text content
            x: Text position X in mm
            y: Text position Y in mm
            height: Text height in mm
            font_name: Font name (optional)
            is_bold: Bold text
            is_italic: Italic text

        Returns:
            Dict with text info and profiles
        """
        data: Dict[str, Any] = {
            "sketch_id": sketch_id,
            "text": text,
            "x": x,
            "y": y,
            "height": height,
            "is_bold": is_bold,
            "is_italic": is_italic,
        }
        if font_name is not None:
            data["font_name"] = font_name
        return await self._request("POST", "/sketch/text", data)

    async def extrude(
        self,
        sketch_id: str,
        distance: float,
        direction: str = "positive",
        operation: str = "new_body",
        profile_index: int = 0,
        name: Optional[str] = None,
        taper_angle: float = 0.0,
    ) -> Dict[str, Any]:
        """Extrude a sketch profile.

        Args:
            sketch_id: ID of the sketch
            distance: Extrusion distance in mm
            direction: "positive", "negative", or "symmetric"
            operation: "new_body", "join", "cut", "intersect"
            profile_index: Index of profile to extrude
            name: Optional name for created body
            taper_angle: Taper angle in degrees

        Returns:
            Dict with feature and body info
        """
        return await self._request("POST", "/create/extrude", {
            "sketch_id": sketch_id,
            "distance": distance,
            "direction": direction,
            "operation": operation,
            "profile_index": profile_index,
            "name": name,
            "taper_angle": taper_angle,
        })

    async def revolve(
        self,
        sketch_id: str,
        axis: str,
        angle: float = 360.0,
        operation: str = "new_body",
        profile_index: int = 0,
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Revolve a sketch profile around an axis.

        Args:
            sketch_id: ID of the sketch
            axis: Axis to revolve around ("X", "Y", "Z")
            angle: Revolution angle in degrees
            operation: "new_body", "join", "cut", "intersect"
            profile_index: Index of profile to revolve
            name: Optional name for created body

        Returns:
            Dict with feature and body info
        """
        return await self._request("POST", "/create/revolve", {
            "sketch_id": sketch_id,
            "axis": axis,
            "angle": angle,
            "operation": operation,
            "profile_index": profile_index,
            "name": name,
        })

    async def fillet(
        self,
        body_id: str,
        edge_ids: List[str],
        radius: float,
    ) -> Dict[str, Any]:
        """Apply fillet to edges.

        Args:
            body_id: ID of the body
            edge_ids: List of edge IDs to fillet
            radius: Fillet radius in mm

        Returns:
            Dict with feature info
        """
        return await self._request("POST", "/create/fillet", {
            "body_id": body_id,
            "edge_ids": edge_ids,
            "radius": radius,
        })

    async def chamfer(
        self,
        body_id: str,
        edge_ids: List[str],
        distance: float,
        distance2: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Apply chamfer to edges.

        Args:
            body_id: ID of the body
            edge_ids: List of edge IDs to chamfer
            distance: Chamfer distance in mm
            distance2: Optional second distance for asymmetric chamfer

        Returns:
            Dict with feature info
        """
        data = {
            "body_id": body_id,
            "edge_ids": edge_ids,
            "distance": distance,
        }
        if distance2 is not None:
            data["distance2"] = distance2
        return await self._request("POST", "/create/chamfer", data)

    async def create_hole(
        self,
        diameter: float,
        depth: float,
        body_id: Optional[str] = None,
        face_id: Optional[str] = None,
        x: float = 0.0,
        y: float = 0.0,
        name: Optional[str] = None,
        hole_type: str = "simple",
        countersink_angle: float = 90.0,
        countersink_diameter: float = 0.0,
        counterbore_diameter: float = 0.0,
        counterbore_depth: float = 0.0,
    ) -> Dict[str, Any]:
        """Create a hole in a body.

        Args:
            diameter: Hole diameter in mm
            depth: Hole depth in mm
            body_id: ID of the body (optional if face_id provided)
            face_id: ID of the face to place hole on
            x: X position in mm
            y: Y position in mm
            name: Optional name for the feature
            hole_type: "simple", "countersink", or "counterbore"
            countersink_angle: Countersink angle in degrees
            countersink_diameter: Countersink diameter in mm
            counterbore_diameter: Counterbore diameter in mm
            counterbore_depth: Counterbore depth in mm

        Returns:
            Dict with feature info
        """
        return await self._request("POST", "/create/hole", {
            "body_id": body_id,
            "face_id": face_id,
            "x": x,
            "y": y,
            "diameter": diameter,
            "depth": depth,
            "name": name,
            "hole_type": hole_type,
            "countersink_angle": countersink_angle,
            "countersink_diameter": countersink_diameter,
            "counterbore_diameter": counterbore_diameter,
            "counterbore_depth": counterbore_depth,
        })

    # --- Modification Methods ---

    async def move_body(
        self,
        body_id: str,
        x: float = 0.0,
        y: float = 0.0,
        z: float = 0.0,
    ) -> Dict[str, Any]:
        """Move a body by translation.

        Uses defineAsTranslate to preserve parametric relationships.

        Args:
            body_id: ID of the body to move
            x: Translation in X direction in mm
            y: Translation in Y direction in mm
            z: Translation in Z direction in mm

        Returns:
            Dict with success, feature info, and new position
        """
        return await self._request("POST", "/modify/move_body", {
            "body_id": body_id,
            "x": x,
            "y": y,
            "z": z,
        })

    async def rotate_body(
        self,
        body_id: str,
        axis: str,
        angle: float,
        origin_x: float = 0.0,
        origin_y: float = 0.0,
        origin_z: float = 0.0,
    ) -> Dict[str, Any]:
        """Rotate a body around an axis.

        Uses defineAsRotate to preserve parametric relationships.

        Args:
            body_id: ID of the body to rotate
            axis: Axis to rotate around ("X", "Y", "Z")
            angle: Rotation angle in degrees
            origin_x: X coordinate of rotation origin in mm
            origin_y: Y coordinate of rotation origin in mm
            origin_z: Z coordinate of rotation origin in mm

        Returns:
            Dict with success, feature info, and new orientation
        """
        return await self._request("POST", "/modify/rotate_body", {
            "body_id": body_id,
            "axis": axis,
            "angle": angle,
            "origin_x": origin_x,
            "origin_y": origin_y,
            "origin_z": origin_z,
        })

    async def modify_feature(
        self,
        feature_id: str,
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Modify feature parameters.

        Supports modifying extrusion distance, fillet/chamfer radius, etc.

        Args:
            feature_id: ID of the feature to modify
            parameters: Dict of parameter names to new values
                - For ExtrudeFeature: {"distance": float}
                - For FilletFeature: {"radius": float}
                - For ChamferFeature: {"distance": float}
                - For RevolveFeature: {"angle": float}

        Returns:
            Dict with success, feature info, and old/new values
        """
        return await self._request("POST", "/modify/feature", {
            "feature_id": feature_id,
            "parameters": parameters,
        })

    async def update_parameter(
        self,
        name: str,
        expression: str,
    ) -> Dict[str, Any]:
        """Update a parameter value.

        Args:
            name: Parameter name
            expression: New value expression (e.g., "50 mm", "d1 * 2")

        Returns:
            Dict with success and old/new values
        """
        return await self._request("POST", "/modify/parameter", {
            "name": name,
            "expression": expression,
        })

    async def delete_body(
        self,
        body_id: str,
    ) -> Dict[str, Any]:
        """Delete a body from the design.

        Args:
            body_id: ID of the body to delete

        Returns:
            Dict with success and deleted entity info
        """
        return await self._request("POST", "/delete/body", {
            "body_id": body_id,
        })

    async def delete_feature(
        self,
        feature_id: str,
    ) -> Dict[str, Any]:
        """Delete a feature from the timeline.

        Args:
            feature_id: ID of the feature to delete

        Returns:
            Dict with success, deleted feature info, and any affected features
        """
        return await self._request("POST", "/delete/feature", {
            "feature_id": feature_id,
        })

    async def edit_sketch(
        self,
        sketch_id: str,
        curve_id: str,
        properties: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Edit a sketch curve.

        Args:
            sketch_id: ID of the sketch
            curve_id: ID of the curve to modify
            properties: Dict of properties to modify
                - For lines: {"start_x", "start_y", "end_x", "end_y"}
                - For circles: {"center_x", "center_y", "radius"}
                - For arcs: {"center_x", "center_y"}

        Returns:
            Dict with success and old/new values
        """
        return await self._request("POST", "/modify/sketch", {
            "sketch_id": sketch_id,
            "curve_id": curve_id,
            "properties": properties,
        })

    # --- MODIFY Menu Methods ---

    async def combine(
        self,
        target_body_id: str,
        tool_body_ids: List[str],
        operation: str = "join",
        keep_tools: bool = False,
    ) -> Dict[str, Any]:
        """Combine multiple bodies using boolean operations.

        Args:
            target_body_id: ID of the body to modify (target)
            tool_body_ids: List of body IDs to combine with (tools)
            operation: "join", "cut", or "intersect"
            keep_tools: If True, keep tool bodies after operation

        Returns:
            Dict with feature info and resulting body
        """
        return await self._request("POST", "/modify/combine", {
            "target_body_id": target_body_id,
            "tool_body_ids": tool_body_ids,
            "operation": operation,
            "keep_tools": keep_tools,
        })

    async def split_body(
        self,
        body_id: str,
        splitting_tool: str,
        extend_splitting_tool: bool = True,
    ) -> Dict[str, Any]:
        """Split a body using a plane or face.

        Args:
            body_id: ID of the body to split
            splitting_tool: Face ID, plane ID, or "XY"/"YZ"/"XZ"
            extend_splitting_tool: If True, extend tool to fully split body

        Returns:
            Dict with feature info and resulting bodies
        """
        return await self._request("POST", "/modify/split_body", {
            "body_id": body_id,
            "splitting_tool": splitting_tool,
            "extend_splitting_tool": extend_splitting_tool,
        })

    async def shell(
        self,
        body_id: str,
        face_ids: List[str],
        thickness: float,
        direction: str = "inside",
    ) -> Dict[str, Any]:
        """Create hollow shell by removing faces and adding wall thickness.

        Args:
            body_id: ID of the body to shell
            face_ids: List of face IDs to remove (become openings)
            thickness: Wall thickness in mm
            direction: "inside" or "outside"

        Returns:
            Dict with feature info and resulting body
        """
        return await self._request("POST", "/modify/shell", {
            "body_id": body_id,
            "face_ids": face_ids,
            "thickness": thickness,
            "direction": direction,
        })

    # NOTE: The following methods are implemented but disabled pending debugging:
    # - draft: Add draft angle to faces
    # - scale: Scale bodies
    # - offset_face: Offset faces
    # - split_face: Split faces
    # See feature_ops.py in the add-in for the core implementations.

    # --- Validation Methods ---

    async def measure_distance(
        self,
        entity1_id: str,
        entity2_id: str,
    ) -> Dict[str, Any]:
        """Measure minimum distance between two entities.

        Supports body-to-body, face-to-face, edge-to-edge, and other
        entity combinations.

        Args:
            entity1_id: ID of the first entity
            entity2_id: ID of the second entity

        Returns:
            Dict with distance (mm), point1, point2 (closest points)
        """
        return await self._request("POST", "/validate/measure_distance", {
            "entity1_id": entity1_id,
            "entity2_id": entity2_id,
        })

    async def measure_angle(
        self,
        entity1_id: str,
        entity2_id: str,
    ) -> Dict[str, Any]:
        """Measure angle between two planar faces or linear edges.

        Args:
            entity1_id: ID of the first entity (face or edge)
            entity2_id: ID of the second entity (face or edge)

        Returns:
            Dict with angle in degrees (0-180)
        """
        return await self._request("POST", "/validate/measure_angle", {
            "entity1_id": entity1_id,
            "entity2_id": entity2_id,
        })

    async def check_interference(
        self,
        body_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Check for interference (collisions) between bodies.

        Args:
            body_ids: Optional list of body IDs to check.
                     If None, checks all bodies.

        Returns:
            Dict with has_interference, interferences list, bodies_checked
        """
        data = {}
        if body_ids is not None:
            data["body_ids"] = body_ids
        return await self._request("POST", "/validate/check_interference", data)

    async def get_body_properties(
        self,
        body_id: str,
    ) -> Dict[str, Any]:
        """Get detailed physical properties of a body.

        Args:
            body_id: ID of the body to analyze

        Returns:
            Dict with volume, area, center_of_mass, bounding_box,
            dimensions, topology counts
        """
        return await self._request("POST", "/validate/body_properties", {
            "body_id": body_id,
        })

    async def get_sketch_status(
        self,
        sketch_id: str,
    ) -> Dict[str, Any]:
        """Get the constraint status of a sketch.

        Args:
            sketch_id: ID of the sketch to analyze

        Returns:
            Dict with is_fully_constrained, under_constrained_count,
            profiles_count, curves_count, constraints_count, etc.
        """
        return await self._request("POST", "/validate/sketch_status", {
            "sketch_id": sketch_id,
        })

    # --- Phase 7c: Sketch Constraints & Dimensions ---

    async def add_constraint_horizontal(
        self,
        sketch_id: str,
        curve_id: str,
    ) -> Dict[str, Any]:
        """Add a horizontal constraint to a line.

        Args:
            sketch_id: ID of the sketch
            curve_id: ID of the line to constrain

        Returns:
            Dict with constraint info and sketch status
        """
        return await self._request("POST", "/sketch/constraint/horizontal", {
            "sketch_id": sketch_id,
            "curve_id": curve_id,
        })

    async def add_constraint_vertical(
        self,
        sketch_id: str,
        curve_id: str,
    ) -> Dict[str, Any]:
        """Add a vertical constraint to a line.

        Args:
            sketch_id: ID of the sketch
            curve_id: ID of the line to constrain

        Returns:
            Dict with constraint info and sketch status
        """
        return await self._request("POST", "/sketch/constraint/vertical", {
            "sketch_id": sketch_id,
            "curve_id": curve_id,
        })

    async def add_constraint_coincident(
        self,
        sketch_id: str,
        entity1_id: str,
        entity2_id: str,
    ) -> Dict[str, Any]:
        """Add a coincident constraint between two entities.

        Args:
            sketch_id: ID of the sketch
            entity1_id: ID of the first entity
            entity2_id: ID of the second entity

        Returns:
            Dict with constraint info and sketch status
        """
        return await self._request("POST", "/sketch/constraint/coincident", {
            "sketch_id": sketch_id,
            "entity1_id": entity1_id,
            "entity2_id": entity2_id,
        })

    async def add_constraint_perpendicular(
        self,
        sketch_id: str,
        curve1_id: str,
        curve2_id: str,
    ) -> Dict[str, Any]:
        """Add a perpendicular constraint between two lines.

        Args:
            sketch_id: ID of the sketch
            curve1_id: ID of the first line
            curve2_id: ID of the second line

        Returns:
            Dict with constraint info and sketch status
        """
        return await self._request("POST", "/sketch/constraint/perpendicular", {
            "sketch_id": sketch_id,
            "curve1_id": curve1_id,
            "curve2_id": curve2_id,
        })

    async def add_constraint_parallel(
        self,
        sketch_id: str,
        curve1_id: str,
        curve2_id: str,
    ) -> Dict[str, Any]:
        """Add a parallel constraint between two lines.

        Args:
            sketch_id: ID of the sketch
            curve1_id: ID of the first line
            curve2_id: ID of the second line

        Returns:
            Dict with constraint info and sketch status
        """
        return await self._request("POST", "/sketch/constraint/parallel", {
            "sketch_id": sketch_id,
            "curve1_id": curve1_id,
            "curve2_id": curve2_id,
        })

    async def add_constraint_tangent(
        self,
        sketch_id: str,
        curve1_id: str,
        curve2_id: str,
    ) -> Dict[str, Any]:
        """Add a tangent constraint between two curves.

        Args:
            sketch_id: ID of the sketch
            curve1_id: ID of the first curve
            curve2_id: ID of the second curve

        Returns:
            Dict with constraint info and sketch status
        """
        return await self._request("POST", "/sketch/constraint/tangent", {
            "sketch_id": sketch_id,
            "curve1_id": curve1_id,
            "curve2_id": curve2_id,
        })

    async def add_constraint_equal(
        self,
        sketch_id: str,
        curve1_id: str,
        curve2_id: str,
    ) -> Dict[str, Any]:
        """Add an equal constraint between two curves.

        Args:
            sketch_id: ID of the sketch
            curve1_id: ID of the first curve
            curve2_id: ID of the second curve

        Returns:
            Dict with constraint info and sketch status
        """
        return await self._request("POST", "/sketch/constraint/equal", {
            "sketch_id": sketch_id,
            "curve1_id": curve1_id,
            "curve2_id": curve2_id,
        })

    async def add_constraint_concentric(
        self,
        sketch_id: str,
        curve1_id: str,
        curve2_id: str,
    ) -> Dict[str, Any]:
        """Add a concentric constraint between two circles or arcs.

        Args:
            sketch_id: ID of the sketch
            curve1_id: ID of the first circle/arc
            curve2_id: ID of the second circle/arc

        Returns:
            Dict with constraint info and sketch status
        """
        return await self._request("POST", "/sketch/constraint/concentric", {
            "sketch_id": sketch_id,
            "curve1_id": curve1_id,
            "curve2_id": curve2_id,
        })

    async def add_constraint_fix(
        self,
        sketch_id: str,
        entity_id: str,
    ) -> Dict[str, Any]:
        """Fix a point or curve in place.

        Args:
            sketch_id: ID of the sketch
            entity_id: ID of the point or curve to fix

        Returns:
            Dict with constraint info and sketch status
        """
        return await self._request("POST", "/sketch/constraint/fix", {
            "sketch_id": sketch_id,
            "entity_id": entity_id,
        })

    async def add_dimension(
        self,
        sketch_id: str,
        dimension_type: str,
        entity1_id: str,
        value: float,
        entity2_id: Optional[str] = None,
        text_position_x: Optional[float] = None,
        text_position_y: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Add a dimensional constraint to a sketch.

        Args:
            sketch_id: ID of the sketch
            dimension_type: Type of dimension ("distance", "radius", "diameter", "angle")
            entity1_id: ID of the first entity
            value: Dimension value in mm or degrees
            entity2_id: ID of second entity (for distance/angle)
            text_position_x: Optional X position for dimension text
            text_position_y: Optional Y position for dimension text

        Returns:
            Dict with dimension info and sketch status
        """
        data: Dict[str, Any] = {
            "sketch_id": sketch_id,
            "dimension_type": dimension_type,
            "entity1_id": entity1_id,
            "value": value,
        }
        if entity2_id is not None:
            data["entity2_id"] = entity2_id
        if text_position_x is not None:
            data["text_position_x"] = text_position_x
        if text_position_y is not None:
            data["text_position_y"] = text_position_y
        return await self._request("POST", "/sketch/dimension", data)

    # --- Phase 8a: Advanced Feature Methods ---

    async def sweep(
        self,
        profile_sketch_id: str,
        path_sketch_id: str,
        profile_index: int = 0,
        operation: str = "new_body",
        orientation: str = "perpendicular",
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Sweep a profile along a path.

        Args:
            profile_sketch_id: ID of the sketch containing the profile
            path_sketch_id: ID of the sketch containing the sweep path
            profile_index: Index of profile to sweep (0 for first/only)
            operation: "new_body", "join", "cut", or "intersect"
            orientation: "perpendicular" or "parallel"
            name: Optional name for created body

        Returns:
            Dict with feature and body info
        """
        data: Dict[str, Any] = {
            "profile_sketch_id": profile_sketch_id,
            "path_sketch_id": path_sketch_id,
            "profile_index": profile_index,
            "operation": operation,
            "orientation": orientation,
        }
        if name is not None:
            data["name"] = name
        return await self._request("POST", "/create/sweep", data)

    async def loft(
        self,
        sketch_ids: List[str],
        profile_indices: Optional[List[int]] = None,
        operation: str = "new_body",
        is_solid: bool = True,
        is_closed: bool = False,
        name: Optional[str] = None,
        target_body_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a loft between multiple profiles.

        Args:
            sketch_ids: List of sketch IDs (in order from start to end)
            profile_indices: Optional list of profile indices for each sketch
            operation: "new_body", "join", "cut", or "intersect"
            is_solid: Create solid (True) or surface (False)
            is_closed: Close the loft ends
            name: Optional name for created body
            target_body_id: Body ID for boolean operations (cut/join/intersect)

        Returns:
            Dict with feature and body info
        """
        data: Dict[str, Any] = {
            "sketch_ids": sketch_ids,
            "operation": operation,
            "is_solid": is_solid,
            "is_closed": is_closed,
        }
        if profile_indices is not None:
            data["profile_indices"] = profile_indices
        if name is not None:
            data["name"] = name
        if target_body_id is not None:
            data["target_body_id"] = target_body_id
        return await self._request("POST", "/create/loft", data)

    async def create_sphere(
        self,
        radius: float,
        x: float = 0.0,
        y: float = 0.0,
        z: float = 0.0,
        name: Optional[str] = None,
        component_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a solid sphere primitive.

        Args:
            radius: Sphere radius in mm
            x: Center X position in mm
            y: Center Y position in mm
            z: Center Z position in mm
            name: Optional name for the body
            component_id: Optional component ID

        Returns:
            Dict with body and feature info
        """
        data: Dict[str, Any] = {
            "radius": radius,
            "x": x,
            "y": y,
            "z": z,
        }
        if name is not None:
            data["name"] = name
        if component_id is not None:
            data["component_id"] = component_id
        return await self._request("POST", "/create/sphere", data)

    async def create_torus(
        self,
        major_radius: float,
        minor_radius: float,
        x: float = 0.0,
        y: float = 0.0,
        z: float = 0.0,
        name: Optional[str] = None,
        component_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a torus (donut/ring shape).

        Args:
            major_radius: Distance from center to tube center in mm
            minor_radius: Tube radius in mm
            x: Center X position in mm
            y: Center Y position in mm
            z: Center Z position in mm
            name: Optional name for the body
            component_id: Optional component ID

        Returns:
            Dict with body and feature info
        """
        data: Dict[str, Any] = {
            "major_radius": major_radius,
            "minor_radius": minor_radius,
            "x": x,
            "y": y,
            "z": z,
        }
        if name is not None:
            data["name"] = name
        if component_id is not None:
            data["component_id"] = component_id
        return await self._request("POST", "/create/torus", data)

    async def create_coil(
        self,
        diameter: float,
        pitch: float,
        revolutions: float,
        section_size: float,
        section_type: str = "circular",
        operation: str = "new_body",
        name: Optional[str] = None,
        x: float = 0.0,
        y: float = 0.0,
        z: float = 0.0,
        component_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a helix/spring shape (coil).

        Args:
            diameter: Coil diameter in mm
            pitch: Distance between coils in mm
            revolutions: Number of turns
            section_size: Wire/section diameter in mm
            section_type: "circular" or "square"
            operation: "new_body", "join", "cut", "intersect"
            name: Optional name for the body
            x: X position in mm
            y: Y position in mm
            z: Z position in mm
            component_id: Optional component ID

        Returns:
            Dict with body and feature info
        """
        data: Dict[str, Any] = {
            "diameter": diameter,
            "pitch": pitch,
            "revolutions": revolutions,
            "section_size": section_size,
            "section_type": section_type,
            "operation": operation,
            "x": x,
            "y": y,
            "z": z,
        }
        if name is not None:
            data["name"] = name
        if component_id is not None:
            data["component_id"] = component_id
        return await self._request("POST", "/create/coil", data)

    async def create_pipe(
        self,
        path_sketch_id: str,
        outer_diameter: float,
        wall_thickness: float,
        operation: str = "new_body",
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a hollow tubular shape (pipe) along a path.

        Args:
            path_sketch_id: ID of the sketch containing the path
            outer_diameter: Outer pipe diameter in mm
            wall_thickness: Pipe wall thickness in mm
            operation: "new_body", "join", "cut", "intersect"
            name: Optional name for the body

        Returns:
            Dict with body and feature info
        """
        data: Dict[str, Any] = {
            "path_sketch_id": path_sketch_id,
            "outer_diameter": outer_diameter,
            "wall_thickness": wall_thickness,
            "operation": operation,
        }
        if name is not None:
            data["name"] = name
        return await self._request("POST", "/create/pipe", data)

    # --- Phase 8b: Feature Pattern Methods ---

    async def rectangular_pattern(
        self,
        entity_ids: List[str],
        entity_type: str,
        x_count: int,
        x_spacing: float,
        x_axis: str = "X",
        y_count: int = 1,
        y_spacing: float = 0.0,
        y_axis: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a rectangular (linear) pattern of bodies or features.

        Args:
            entity_ids: List of body or feature IDs to pattern
            entity_type: "bodies" or "features"
            x_count: Number of columns (minimum 2)
            x_spacing: Column spacing in mm
            x_axis: Direction for columns ("X", "Y", "Z" or edge_id)
            y_count: Number of rows (default 1 for 1D pattern)
            y_spacing: Row spacing in mm
            y_axis: Direction for rows (default perpendicular to x_axis)

        Returns:
            Dict with pattern feature info and created instance IDs
        """
        data: Dict[str, Any] = {
            "entity_ids": entity_ids,
            "entity_type": entity_type,
            "x_count": x_count,
            "x_spacing": x_spacing,
            "x_axis": x_axis,
            "y_count": y_count,
            "y_spacing": y_spacing,
        }
        if y_axis is not None:
            data["y_axis"] = y_axis
        return await self._request("POST", "/pattern/rectangular", data)

    async def circular_pattern(
        self,
        entity_ids: List[str],
        entity_type: str,
        axis: str,
        count: int,
        total_angle: float = 360.0,
        is_symmetric: bool = True,
    ) -> Dict[str, Any]:
        """Create a circular (radial) pattern of bodies or features.

        Args:
            entity_ids: List of body or feature IDs to pattern
            entity_type: "bodies" or "features"
            axis: Rotation axis ("X", "Y", "Z" or axis_id)
            count: Number of instances (including original, minimum 2)
            total_angle: Total angle span in degrees (default 360)
            is_symmetric: Distribute evenly within total_angle (default True)

        Returns:
            Dict with pattern feature info and created instance IDs
        """
        return await self._request("POST", "/pattern/circular", {
            "entity_ids": entity_ids,
            "entity_type": entity_type,
            "axis": axis,
            "count": count,
            "total_angle": total_angle,
            "is_symmetric": is_symmetric,
        })

    async def mirror_feature(
        self,
        entity_ids: List[str],
        entity_type: str,
        mirror_plane: str,
    ) -> Dict[str, Any]:
        """Mirror bodies or features across a plane.

        Args:
            entity_ids: List of body or feature IDs to mirror
            entity_type: "bodies" or "features"
            mirror_plane: Mirror plane ("XY", "YZ", "XZ" or plane_id)

        Returns:
            Dict with mirror feature info and created instance IDs
        """
        return await self._request("POST", "/pattern/mirror", {
            "entity_ids": entity_ids,
            "entity_type": entity_type,
            "mirror_plane": mirror_plane,
        })

    # --- Phase 8c: Specialized Feature Methods ---

    async def create_thread(
        self,
        face_id: str,
        thread_type: str,
        thread_size: str,
        is_internal: bool = False,
        is_full_length: bool = True,
        thread_length: Optional[float] = None,
        is_modeled: bool = False,
    ) -> Dict[str, Any]:
        """Add threads to a cylindrical face.

        Args:
            face_id: ID of the cylindrical face to add thread to
            thread_type: Thread standard (e.g., "ISO Metric profile")
            thread_size: Thread designation (e.g., "M6x1", "M8x1.25")
            is_internal: Internal thread (True) or external thread (False)
            is_full_length: Thread entire face length (True) or use custom length
            thread_length: Custom thread length in mm (used if is_full_length=False)
            is_modeled: Create physical thread geometry (slower but visible)

        Returns:
            Dict with thread feature info and thread specification
        """
        data: Dict[str, Any] = {
            "face_id": face_id,
            "thread_type": thread_type,
            "thread_size": thread_size,
            "is_internal": is_internal,
            "is_full_length": is_full_length,
            "is_modeled": is_modeled,
        }
        if thread_length is not None:
            data["thread_length"] = thread_length
        return await self._request("POST", "/create/thread", data)

    async def thicken(
        self,
        face_ids: List[str],
        thickness: float,
        direction: str = "both",
        operation: str = "new_body",
        is_chain: bool = True,
    ) -> Dict[str, Any]:
        """Add thickness to surface faces to create solid bodies.

        Args:
            face_ids: List of face IDs to thicken
            thickness: Thickness in mm
            direction: "positive", "negative", or "both"
            operation: "new_body", "join", "cut", "intersect"
            is_chain: Include tangent-connected faces

        Returns:
            Dict with thicken feature info and created bodies
        """
        return await self._request("POST", "/create/thicken", {
            "face_ids": face_ids,
            "thickness": thickness,
            "direction": direction,
            "operation": operation,
            "is_chain": is_chain,
        })

    async def emboss(
        self,
        sketch_id: str,
        face_id: str,
        depth: float,
        is_emboss: bool = True,
        profile_index: int = 0,
        taper_angle: float = 0.0,
    ) -> Dict[str, Any]:
        """Create raised (emboss) or recessed (deboss) features from sketch profiles.

        Args:
            sketch_id: ID of the sketch containing profile/text to emboss
            face_id: ID of the face to emboss onto
            depth: Emboss/deboss depth in mm
            is_emboss: True for emboss, False for deboss/engrave
            profile_index: Index of profile to use from sketch
            taper_angle: Side taper angle in degrees

        Returns:
            Dict with emboss feature info
        """
        return await self._request("POST", "/create/emboss", {
            "sketch_id": sketch_id,
            "face_id": face_id,
            "depth": depth,
            "is_emboss": is_emboss,
            "profile_index": profile_index,
            "taper_angle": taper_angle,
        })

    # --- Viewport Methods ---

    async def take_screenshot(
        self,
        file_path: str,
        view: str = "current",
        width: int = 1920,
        height: int = 1080,
    ) -> Dict[str, Any]:
        """Capture the viewport as a PNG image.

        Args:
            file_path: Path to save the image (required)
            view: View to capture ("current" or standard view name)
            width: Image width in pixels
            height: Image height in pixels

        Returns:
            Dict with image metadata
        """
        data: Dict[str, Any] = {
            "file_path": file_path,
            "view": view,
            "width": width,
            "height": height,
        }
        return await self._request("POST", "/viewport/screenshot", data)

    async def set_camera(
        self,
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

        Args:
            eye_x: Camera eye X position in mm
            eye_y: Camera eye Y position in mm
            eye_z: Camera eye Z position in mm
            target_x: Camera target X position in mm
            target_y: Camera target Y position in mm
            target_z: Camera target Z position in mm
            up_x: Up vector X component
            up_y: Up vector Y component
            up_z: Up vector Z component
            smooth_transition: Animate the transition

        Returns:
            Dict with camera state after change
        """
        return await self._request("POST", "/viewport/camera", {
            "eye_x": eye_x,
            "eye_y": eye_y,
            "eye_z": eye_z,
            "target_x": target_x,
            "target_y": target_y,
            "target_z": target_z,
            "up_x": up_x,
            "up_y": up_y,
            "up_z": up_z,
            "smooth_transition": smooth_transition,
        })

    async def get_camera(self) -> Dict[str, Any]:
        """Get the current viewport camera state.

        Returns:
            Dict with camera position, orientation, and settings
        """
        return await self._request("GET", "/viewport/camera/get")

    async def set_view(
        self,
        view: str,
        smooth_transition: bool = True,
    ) -> Dict[str, Any]:
        """Set the viewport to a standard named view.

        Args:
            view: Named view (front, back, top, bottom, left, right,
                  isometric, trimetric, home)
            smooth_transition: Animate the view change

        Returns:
            Dict with view name and camera state
        """
        return await self._request("POST", "/viewport/view", {
            "view": view,
            "smooth_transition": smooth_transition,
        })

    async def fit_view(
        self,
        entity_ids: Optional[List[str]] = None,
        smooth_transition: bool = True,
    ) -> Dict[str, Any]:
        """Fit the viewport to show specific entities or all geometry.

        Args:
            entity_ids: Optional list of entity IDs to fit to
            smooth_transition: Animate the zoom change

        Returns:
            Dict with fitted_to and camera state
        """
        data: Dict[str, Any] = {
            "smooth_transition": smooth_transition,
        }
        if entity_ids is not None:
            data["entity_ids"] = entity_ids
        return await self._request("POST", "/viewport/fit", data)

    # --- Construction Plane Methods ---

    async def create_offset_plane(
        self,
        base_plane: str,
        offset: float,
        name: Optional[str] = None,
        component_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a construction plane offset from an existing plane or face.

        Args:
            base_plane: Base plane ("XY", "YZ", "XZ") or face/plane ID
            offset: Offset distance in mm (positive or negative)
            name: Optional name for the plane
            component_id: Optional component ID

        Returns:
            Dict with plane info including id, origin, normal
        """
        data: Dict[str, Any] = {
            "base_plane": base_plane,
            "offset": offset,
        }
        if name is not None:
            data["name"] = name
        if component_id is not None:
            data["component_id"] = component_id
        return await self._request("POST", "/create/plane/offset", data)

    async def create_angle_plane(
        self,
        base_plane: str,
        edge_id: str,
        angle: float,
        name: Optional[str] = None,
        component_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a construction plane at an angle from a plane along an edge.

        Args:
            base_plane: Base plane ("XY", "YZ", "XZ") or face/plane ID
            edge_id: ID of the edge to rotate around
            angle: Rotation angle in degrees
            name: Optional name for the plane
            component_id: Optional component ID

        Returns:
            Dict with plane info including id, origin, normal
        """
        data: Dict[str, Any] = {
            "base_plane": base_plane,
            "edge_id": edge_id,
            "angle": angle,
        }
        if name is not None:
            data["name"] = name
        if component_id is not None:
            data["component_id"] = component_id
        return await self._request("POST", "/create/plane/angle", data)

    async def create_three_point_plane(
        self,
        point1: Dict[str, float],
        point2: Dict[str, float],
        point3: Dict[str, float],
        name: Optional[str] = None,
        component_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a construction plane through three points.

        Args:
            point1: First point {x, y, z} in mm
            point2: Second point {x, y, z} in mm
            point3: Third point {x, y, z} in mm
            name: Optional name for the plane
            component_id: Optional component ID

        Returns:
            Dict with plane info including id, origin, normal
        """
        data: Dict[str, Any] = {
            "point1": point1,
            "point2": point2,
            "point3": point3,
        }
        if name is not None:
            data["name"] = name
        if component_id is not None:
            data["component_id"] = component_id
        return await self._request("POST", "/create/plane/three_points", data)

    async def create_midplane(
        self,
        plane1: str,
        plane2: str,
        name: Optional[str] = None,
        component_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a construction plane midway between two planes or faces.

        Args:
            plane1: First plane ("XY", "YZ", "XZ") or face/plane ID
            plane2: Second plane ("XY", "YZ", "XZ") or face/plane ID
            name: Optional name for the plane
            component_id: Optional component ID

        Returns:
            Dict with plane info including id, origin, normal
        """
        data: Dict[str, Any] = {
            "plane1": plane1,
            "plane2": plane2,
        }
        if name is not None:
            data["name"] = name
        if component_id is not None:
            data["component_id"] = component_id
        return await self._request("POST", "/create/plane/midplane", data)

    # --- Assembly Methods ---

    async def create_component(
        self,
        name: str,
    ) -> Dict[str, Any]:
        """Create a new component.

        Args:
            name: Name for the new component

        Returns:
            Dict with component and occurrence info
        """
        return await self._request("POST", "/assembly/create_component", {
            "name": name,
        })

    async def get_components(self) -> Dict[str, Any]:
        """Get all components in the design.

        Returns:
            Dict with list of component summaries
        """
        return await self._request("GET", "/assembly/components")

    async def get_component_by_id(
        self,
        component_id: str,
    ) -> Dict[str, Any]:
        """Get detailed component info by ID.

        Args:
            component_id: Component ID to retrieve

        Returns:
            Dict with full component info
        """
        return await self._request("POST", "/assembly/component", {
            "component_id": component_id,
        })

    async def activate_component(
        self,
        component_id: str,
    ) -> Dict[str, Any]:
        """Activate a component for editing.

        Args:
            component_id: Component ID to activate

        Returns:
            Dict confirming activation
        """
        return await self._request("POST", "/assembly/activate_component", {
            "component_id": component_id,
        })

    async def get_component_bodies(
        self,
        component_id: str,
    ) -> Dict[str, Any]:
        """Get all bodies within a specific component.

        Args:
            component_id: Component ID to get bodies from

        Returns:
            Dict with list of body summaries
        """
        return await self._request("POST", "/assembly/component_bodies", {
            "component_id": component_id,
        })

    async def get_occurrences(
        self,
        component_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get all occurrences in the design or within a component.

        Args:
            component_id: Optional component ID to filter occurrences

        Returns:
            Dict with list of occurrence info
        """
        data = {"component_id": component_id} if component_id else {}
        return await self._request("POST", "/assembly/occurrences", data)

    async def move_occurrence(
        self,
        occurrence_id: str,
        x: float = 0.0,
        y: float = 0.0,
        z: float = 0.0,
    ) -> Dict[str, Any]:
        """Move an occurrence by translation.

        Args:
            occurrence_id: Occurrence ID to move
            x: X translation in mm
            y: Y translation in mm
            z: Z translation in mm

        Returns:
            Dict with updated occurrence info
        """
        return await self._request("POST", "/assembly/move_occurrence", {
            "occurrence_id": occurrence_id,
            "x": x,
            "y": y,
            "z": z,
        })

    async def create_joint(
        self,
        geometry1_id: str,
        geometry2_id: str,
        joint_type: str = "rigid",
    ) -> Dict[str, Any]:
        """Create a joint between two geometry entities.

        Args:
            geometry1_id: First geometry entity ID
            geometry2_id: Second geometry entity ID
            joint_type: Type of joint (rigid, revolute, slider, etc.)

        Returns:
            Dict with joint info
        """
        return await self._request("POST", "/assembly/create_joint", {
            "geometry1_id": geometry1_id,
            "geometry2_id": geometry2_id,
            "joint_type": joint_type,
        })

    async def create_joint_between_occurrences(
        self,
        occurrence1_id: str,
        occurrence2_id: str,
        joint_type: str = "rigid",
    ) -> Dict[str, Any]:
        """Create a joint between two occurrences.

        Args:
            occurrence1_id: First occurrence ID
            occurrence2_id: Second occurrence ID
            joint_type: Type of joint (rigid, revolute, slider, etc.)

        Returns:
            Dict with joint info
        """
        return await self._request("POST", "/assembly/create_joint_occurrences", {
            "occurrence1_id": occurrence1_id,
            "occurrence2_id": occurrence2_id,
            "joint_type": joint_type,
        })

    async def get_joints(self) -> Dict[str, Any]:
        """Get all joints in the design.

        Returns:
            Dict with list of joint info
        """
        return await self._request("GET", "/assembly/joints")

    async def get_joint_by_id(
        self,
        joint_id: str,
    ) -> Dict[str, Any]:
        """Get detailed joint info by ID.

        Args:
            joint_id: Joint ID to retrieve

        Returns:
            Dict with joint info
        """
        return await self._request("POST", "/assembly/joint", {
            "joint_id": joint_id,
        })
