"""Async HTTP client for Fusion 360 add-in communication.

Provides a typed interface for making requests to the Fusion 360 add-in
HTTP server, with retry logic and response parsing.
"""

import asyncio
from typing import Optional, Dict, Any, TypeVar, Type, List
import httpx
from pydantic import BaseModel

from ..config import get_config, ServerConfig
from ..models import (
    DesignInfo,
    Body,
    BodySummary,
    Sketch,
    SketchSummary,
    Parameter,
)
from ..logging import get_logger

# Import shared exceptions
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
from shared.exceptions import (
    ConnectionError as FusionConnectionError,
    TimeoutError as FusionTimeoutError,
    FusionMCPError,
    EntityNotFoundError,
    InvalidParameterError,
    DesignStateError,
)


T = TypeVar('T', bound=BaseModel)
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

    async def health_check(self) -> bool:
        """Check if add-in is responsive.

        Returns:
            True if add-in is healthy, False otherwise
        """
        try:
            result = await self._request("GET", "/health")
            return result.get("status") == "ok"
        except Exception:
            return False
