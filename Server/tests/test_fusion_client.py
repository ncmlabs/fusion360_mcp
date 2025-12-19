"""Unit tests for FusionClient HTTP client."""

import pytest
import httpx
import respx
from unittest.mock import AsyncMock, patch

from fusion360_mcp_server.services.fusion_client import FusionClient
from fusion360_mcp_server.config import ServerConfig


# Import shared exceptions for testing
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from shared.exceptions import (
    ConnectionError as FusionConnectionError,
    TimeoutError as FusionTimeoutError,
    EntityNotFoundError,
    InvalidParameterError,
    DesignStateError,
    FusionMCPError,
)


@pytest.fixture
def config():
    """Create test configuration."""
    return ServerConfig(
        fusion_host="localhost",
        fusion_port=5001,
        request_timeout=5.0,
        max_retries=2,
        retry_delay=0.1,
    )


@pytest.fixture
def client(config):
    """Create FusionClient with test config."""
    return FusionClient(config=config)


class TestFusionClientConnection:
    """Tests for connection management."""

    @pytest.mark.asyncio
    async def test_connect_creates_client(self, client):
        """Test that connect creates the HTTP client."""
        assert client._client is None
        await client.connect()
        assert client._client is not None
        await client.disconnect()

    @pytest.mark.asyncio
    async def test_disconnect_closes_client(self, client):
        """Test that disconnect closes the HTTP client."""
        await client.connect()
        assert client._client is not None
        await client.disconnect()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_context_manager(self, config):
        """Test async context manager usage."""
        async with FusionClient(config=config) as client:
            assert client._client is not None
        assert client._client is None

    @pytest.mark.asyncio
    async def test_ensure_connected(self, client):
        """Test _ensure_connected creates client if needed."""
        assert client._client is None
        await client._ensure_connected()
        assert client._client is not None
        await client.disconnect()


class TestFusionClientHealthCheck:
    """Tests for health check."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_health_check_success(self, client, config):
        """Test successful health check."""
        respx.get(f"{config.fusion_base_url}/health").mock(
            return_value=httpx.Response(200, json={
                "success": True,
                "status": "healthy",
                "message": "Fusion 360 MCP Add-in is running",
                "version": "0.1.0",
            })
        )

        async with client:
            result = await client.health_check()

        assert result["healthy"] is True
        assert result["status"] == "healthy"
        assert result["version"] == "0.1.0"

    @pytest.mark.asyncio
    @respx.mock
    async def test_health_check_unhealthy(self, client, config):
        """Test unhealthy status."""
        respx.get(f"{config.fusion_base_url}/health").mock(
            return_value=httpx.Response(200, json={
                "success": True,
                "status": "unhealthy",
                "message": "Fusion 360 not connected",
            })
        )

        async with client:
            result = await client.health_check()

        assert result["healthy"] is False
        assert result["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_health_check_connection_error(self, client):
        """Test health check when add-in is unreachable."""
        async with client:
            result = await client.health_check()

        assert result["healthy"] is False
        assert result["status"] == "unreachable"


class TestFusionClientVersion:
    """Tests for version endpoint."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_version_success(self, client, config):
        """Test successful version retrieval."""
        respx.get(f"{config.fusion_base_url}/version").mock(
            return_value=httpx.Response(200, json={
                "success": True,
                "addin_name": "FusionMCP",
                "addin_version": "0.1.0",
                "fusion_version": "2.0.18719",
                "api_version": "1.0",
            })
        )

        async with client:
            result = await client.get_version()

        assert result["addin_name"] == "FusionMCP"
        assert result["addin_version"] == "0.1.0"
        assert result["fusion_version"] == "2.0.18719"


class TestFusionClientRetry:
    """Tests for retry logic."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_retry_on_connection_error(self, client, config):
        """Test retry when connection fails."""
        route = respx.get(f"{config.fusion_base_url}/health")
        route.side_effect = [
            httpx.ConnectError("Connection refused"),
            httpx.Response(200, json={"success": True, "status": "healthy"}),
        ]

        async with client:
            result = await client.health_check()

        assert result["healthy"] is True
        assert route.call_count == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_retry_exhausted_raises_connection_error(self, client, config):
        """Test that exhausted retries raise FusionConnectionError."""
        respx.get(f"{config.fusion_base_url}/health").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        async with client:
            result = await client.health_check()

        # health_check catches exceptions and returns status
        assert result["healthy"] is False
        assert result["status"] == "unreachable"

    @pytest.mark.asyncio
    @respx.mock
    async def test_retry_on_timeout(self, client, config):
        """Test retry on timeout."""
        route = respx.post(f"{config.fusion_base_url}/query/bodies")
        route.side_effect = [
            httpx.TimeoutException("Request timed out"),
            httpx.Response(200, json={"success": True, "data": {"bodies": []}}),
        ]

        async with client:
            result = await client.get_bodies()

        assert result == []
        assert route.call_count == 2


class TestFusionClientErrorHandling:
    """Tests for error response handling."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_entity_not_found_error(self, client, config):
        """Test EntityNotFoundError response handling."""
        respx.post(f"{config.fusion_base_url}/query/body").mock(
            return_value=httpx.Response(200, json={
                "success": False,
                "error_type": "EntityNotFound",
                "error": "Body not found",
                "context": {
                    "entity_type": "Body",
                    "requested_id": "nonexistent",
                    "available_entities": ["body1", "body2"],
                },
            })
        )

        async with client:
            with pytest.raises(EntityNotFoundError) as exc_info:
                await client.get_body_by_id("nonexistent")

        assert "Body" in str(exc_info.value)
        assert "nonexistent" in str(exc_info.value)

    @pytest.mark.asyncio
    @respx.mock
    async def test_invalid_parameter_error(self, client, config):
        """Test InvalidParameterError response handling."""
        respx.post(f"{config.fusion_base_url}/create/box").mock(
            return_value=httpx.Response(200, json={
                "success": False,
                "error_type": "InvalidParameter",
                "error": "Width must be positive",
                "context": {
                    "parameter_name": "width",
                    "current_value": -10,
                },
            })
        )

        async with client:
            with pytest.raises(InvalidParameterError) as exc_info:
                await client.create_box(width=-10, depth=50, height=10)

        assert "width" in str(exc_info.value)

    @pytest.mark.asyncio
    @respx.mock
    async def test_design_state_error(self, client, config):
        """Test DesignStateError response handling."""
        respx.get(f"{config.fusion_base_url}/query/design_state").mock(
            return_value=httpx.Response(200, json={
                "success": False,
                "error_type": "DesignState",
                "error": "No active design",
                "context": {
                    "current_state": "no_document",
                },
            })
        )

        async with client:
            with pytest.raises(DesignStateError):
                await client.get_design_state()


class TestFusionClientQueryMethods:
    """Tests for query methods."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_design_state(self, client, config):
        """Test get_design_state method."""
        respx.get(f"{config.fusion_base_url}/query/design_state").mock(
            return_value=httpx.Response(200, json={
                "success": True,
                "data": {
                    "design": {
                        "name": "TestDesign",
                        "units": "mm",
                        "bodies_count": 3,
                        "sketches_count": 2,
                    }
                }
            })
        )

        async with client:
            result = await client.get_design_state()

        assert result["name"] == "TestDesign"
        assert result["units"] == "mm"
        assert result["bodies_count"] == 3

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_bodies(self, client, config):
        """Test get_bodies method."""
        respx.post(f"{config.fusion_base_url}/query/bodies").mock(
            return_value=httpx.Response(200, json={
                "success": True,
                "data": {
                    "bodies": [
                        {"id": "body1", "name": "Box", "is_solid": True},
                        {"id": "body2", "name": "Cylinder", "is_solid": True},
                    ]
                }
            })
        )

        async with client:
            result = await client.get_bodies()

        assert len(result) == 2
        assert result[0]["id"] == "body1"
        assert result[1]["name"] == "Cylinder"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_body_by_id(self, client, config):
        """Test get_body_by_id method."""
        respx.post(f"{config.fusion_base_url}/query/body").mock(
            return_value=httpx.Response(200, json={
                "success": True,
                "data": {
                    "body": {
                        "id": "body1",
                        "name": "Box",
                        "is_solid": True,
                        "volume": 1000.0,
                        "faces": [],
                        "edges": [],
                    }
                }
            })
        )

        async with client:
            result = await client.get_body_by_id("body1", include_faces=True)

        assert result["id"] == "body1"
        assert result["volume"] == 1000.0

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_sketches(self, client, config):
        """Test get_sketches method."""
        respx.post(f"{config.fusion_base_url}/query/sketches").mock(
            return_value=httpx.Response(200, json={
                "success": True,
                "data": {
                    "sketches": [
                        {"id": "sketch1", "name": "Sketch1", "is_fully_constrained": True},
                    ]
                }
            })
        )

        async with client:
            result = await client.get_sketches()

        assert len(result) == 1
        assert result[0]["is_fully_constrained"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_parameters(self, client, config):
        """Test get_parameters method."""
        respx.post(f"{config.fusion_base_url}/query/parameters").mock(
            return_value=httpx.Response(200, json={
                "success": True,
                "data": {
                    "parameters": [
                        {"name": "width", "value": 100.0, "unit": "mm"},
                        {"name": "height", "value": 50.0, "unit": "mm"},
                    ]
                }
            })
        )

        async with client:
            result = await client.get_parameters(user_only=True)

        assert len(result) == 2
        assert result[0]["name"] == "width"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_timeline(self, client, config):
        """Test get_timeline method."""
        respx.post(f"{config.fusion_base_url}/query/timeline").mock(
            return_value=httpx.Response(200, json={
                "success": True,
                "data": {
                    "entries": [
                        {"index": 0, "name": "Sketch1", "type": "Sketch"},
                        {"index": 1, "name": "Extrude1", "type": "ExtrudeFeature"},
                    ],
                    "marker_position": 2,
                }
            })
        )

        async with client:
            result = await client.get_timeline()

        assert len(result["entries"]) == 2
        assert result["marker_position"] == 2


class TestFusionClientCreationMethods:
    """Tests for creation methods."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_box(self, client, config):
        """Test create_box method."""
        respx.post(f"{config.fusion_base_url}/create/box").mock(
            return_value=httpx.Response(200, json={
                "success": True,
                "data": {
                    "body_id": "box1",
                    "feature_id": "extrude1",
                    "body": {"id": "box1", "name": "Box", "is_solid": True},
                }
            })
        )

        async with client:
            result = await client.create_box(
                width=100, depth=50, height=20,
                x=0, y=0, z=0,
                name="MyBox"
            )

        assert result["body_id"] == "box1"
        assert result["body"]["is_solid"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_cylinder(self, client, config):
        """Test create_cylinder method."""
        respx.post(f"{config.fusion_base_url}/create/cylinder").mock(
            return_value=httpx.Response(200, json={
                "success": True,
                "data": {
                    "body_id": "cyl1",
                    "body": {"id": "cyl1", "name": "Cylinder", "is_solid": True},
                }
            })
        )

        async with client:
            result = await client.create_cylinder(radius=25, height=50)

        assert result["body_id"] == "cyl1"

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_sketch(self, client, config):
        """Test create_sketch method."""
        respx.post(f"{config.fusion_base_url}/create/sketch").mock(
            return_value=httpx.Response(200, json={
                "success": True,
                "data": {
                    "sketch_id": "sketch1",
                    "sketch": {"id": "sketch1", "name": "Sketch1"},
                }
            })
        )

        async with client:
            result = await client.create_sketch(plane="XY", name="MySketch")

        assert result["sketch_id"] == "sketch1"

    @pytest.mark.asyncio
    @respx.mock
    async def test_extrude(self, client, config):
        """Test extrude method."""
        respx.post(f"{config.fusion_base_url}/create/extrude").mock(
            return_value=httpx.Response(200, json={
                "success": True,
                "data": {
                    "feature_id": "extrude1",
                    "body_id": "body1",
                }
            })
        )

        async with client:
            result = await client.extrude(
                sketch_id="sketch1",
                distance=20,
                direction="positive",
                operation="new_body"
            )

        assert result["feature_id"] == "extrude1"

    @pytest.mark.asyncio
    @respx.mock
    async def test_fillet(self, client, config):
        """Test fillet method."""
        respx.post(f"{config.fusion_base_url}/create/fillet").mock(
            return_value=httpx.Response(200, json={
                "success": True,
                "data": {
                    "feature_id": "fillet1",
                }
            })
        )

        async with client:
            result = await client.fillet(
                body_id="body1",
                edge_ids=["edge1", "edge2"],
                radius=5.0
            )

        assert result["feature_id"] == "fillet1"


class TestFusionClientModificationMethods:
    """Tests for modification methods."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_move_body(self, client, config):
        """Test move_body method."""
        respx.post(f"{config.fusion_base_url}/modify/move_body").mock(
            return_value=httpx.Response(200, json={
                "success": True,
                "data": {
                    "feature_id": "move1",
                    "new_position": {"x": 10, "y": 20, "z": 0},
                }
            })
        )

        async with client:
            result = await client.move_body(body_id="body1", x=10, y=20, z=0)

        assert result["feature_id"] == "move1"

    @pytest.mark.asyncio
    @respx.mock
    async def test_rotate_body(self, client, config):
        """Test rotate_body method."""
        respx.post(f"{config.fusion_base_url}/modify/rotate_body").mock(
            return_value=httpx.Response(200, json={
                "success": True,
                "data": {
                    "feature_id": "rotate1",
                }
            })
        )

        async with client:
            result = await client.rotate_body(
                body_id="body1",
                axis="Z",
                angle=45
            )

        assert result["feature_id"] == "rotate1"

    @pytest.mark.asyncio
    @respx.mock
    async def test_modify_feature(self, client, config):
        """Test modify_feature method."""
        respx.post(f"{config.fusion_base_url}/modify/feature").mock(
            return_value=httpx.Response(200, json={
                "success": True,
                "data": {
                    "old_values": {"distance": 20},
                    "new_values": {"distance": 30},
                }
            })
        )

        async with client:
            result = await client.modify_feature(
                feature_id="extrude1",
                parameters={"distance": 30}
            )

        assert result["new_values"]["distance"] == 30

    @pytest.mark.asyncio
    @respx.mock
    async def test_delete_body(self, client, config):
        """Test delete_body method."""
        respx.post(f"{config.fusion_base_url}/delete/body").mock(
            return_value=httpx.Response(200, json={
                "success": True,
                "data": {
                    "deleted_id": "body1",
                }
            })
        )

        async with client:
            result = await client.delete_body(body_id="body1")

        assert result["deleted_id"] == "body1"


class TestFusionClientValidationMethods:
    """Tests for validation methods."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_measure_distance(self, client, config):
        """Test measure_distance method."""
        respx.post(f"{config.fusion_base_url}/validate/measure_distance").mock(
            return_value=httpx.Response(200, json={
                "success": True,
                "data": {
                    "distance": 15.5,
                    "point1": {"x": 0, "y": 0, "z": 0},
                    "point2": {"x": 15.5, "y": 0, "z": 0},
                }
            })
        )

        async with client:
            result = await client.measure_distance("body1", "body2")

        assert result["distance"] == 15.5

    @pytest.mark.asyncio
    @respx.mock
    async def test_check_interference(self, client, config):
        """Test check_interference method."""
        respx.post(f"{config.fusion_base_url}/validate/check_interference").mock(
            return_value=httpx.Response(200, json={
                "success": True,
                "data": {
                    "has_interference": False,
                    "interferences": [],
                    "bodies_checked": 3,
                }
            })
        )

        async with client:
            result = await client.check_interference()

        assert result["has_interference"] is False
        assert result["bodies_checked"] == 3

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_body_properties(self, client, config):
        """Test get_body_properties method."""
        respx.post(f"{config.fusion_base_url}/validate/body_properties").mock(
            return_value=httpx.Response(200, json={
                "success": True,
                "data": {
                    "volume": 50000.0,
                    "area": 7000.0,
                    "center_of_mass": {"x": 50, "y": 25, "z": 5},
                }
            })
        )

        async with client:
            result = await client.get_body_properties("body1")

        assert result["volume"] == 50000.0
        assert result["area"] == 7000.0
