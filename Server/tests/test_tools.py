"""Unit tests for MCP tools."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from mcp.server.fastmcp import FastMCP

# Import tool registration functions
from fusion360_mcp_server.tools.query_tools import register_query_tools
from fusion360_mcp_server.tools.creation_tools import register_creation_tools
from fusion360_mcp_server.tools.modification_tools import register_modification_tools
from fusion360_mcp_server.tools.validation_tools import register_validation_tools
from fusion360_mcp_server.tools.system_tools import register_system_tools


@pytest.fixture
def mcp():
    """Create a FastMCP instance for testing."""
    return FastMCP("TestServer")


@pytest.fixture
def mock_client():
    """Create a mock FusionClient."""
    client = AsyncMock()
    # Setup context manager
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


class TestQueryTools:
    """Tests for query tools."""

    @pytest.mark.asyncio
    async def test_get_design_state_registered(self, mcp):
        """Test that get_design_state tool is registered."""
        register_query_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "get_design_state" in tools

    @pytest.mark.asyncio
    async def test_get_bodies_registered(self, mcp):
        """Test that get_bodies tool is registered."""
        register_query_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "get_bodies" in tools

    @pytest.mark.asyncio
    async def test_get_body_by_id_registered(self, mcp):
        """Test that get_body_by_id tool is registered."""
        register_query_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "get_body_by_id" in tools

    @pytest.mark.asyncio
    async def test_get_sketches_registered(self, mcp):
        """Test that get_sketches tool is registered."""
        register_query_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "get_sketches" in tools

    @pytest.mark.asyncio
    async def test_get_sketch_by_id_registered(self, mcp):
        """Test that get_sketch_by_id tool is registered."""
        register_query_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "get_sketch_by_id" in tools

    @pytest.mark.asyncio
    async def test_get_parameters_registered(self, mcp):
        """Test that get_parameters tool is registered."""
        register_query_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "get_parameters" in tools

    @pytest.mark.asyncio
    async def test_get_timeline_registered(self, mcp):
        """Test that get_timeline tool is registered."""
        register_query_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "get_timeline" in tools

    @pytest.mark.asyncio
    @patch('fusion360_mcp_server.tools.query_tools.FusionClient')
    async def test_get_design_state_calls_client(self, MockClient, mcp, mock_client):
        """Test that get_design_state calls FusionClient correctly."""
        MockClient.return_value = mock_client
        mock_client.get_design_state.return_value = {
            "name": "Test",
            "units": "mm",
        }

        register_query_tools(mcp)
        tool = mcp._tool_manager._tools["get_design_state"]
        result = await tool.fn()

        mock_client.get_design_state.assert_called_once()
        assert result["name"] == "Test"

    @pytest.mark.asyncio
    @patch('fusion360_mcp_server.tools.query_tools.FusionClient')
    async def test_get_bodies_calls_client(self, MockClient, mcp, mock_client):
        """Test that get_bodies calls FusionClient with correct args."""
        MockClient.return_value = mock_client
        mock_client.get_bodies.return_value = [
            {"id": "body1", "name": "Box"}
        ]

        register_query_tools(mcp)
        tool = mcp._tool_manager._tools["get_bodies"]
        result = await tool.fn(component_id="comp1")

        mock_client.get_bodies.assert_called_once_with("comp1")
        assert len(result["bodies"]) == 1

    @pytest.mark.asyncio
    @patch('fusion360_mcp_server.tools.query_tools.FusionClient')
    async def test_get_body_by_id_includes_topology(self, MockClient, mcp, mock_client):
        """Test that get_body_by_id passes topology flags."""
        MockClient.return_value = mock_client
        mock_client.get_body_by_id.return_value = {
            "id": "body1",
            "faces": [{"id": "face1"}],
        }

        register_query_tools(mcp)
        tool = mcp._tool_manager._tools["get_body_by_id"]
        result = await tool.fn(
            body_id="body1",
            include_faces=True,
            include_edges=True,
        )

        # Verify client was called with the topology flags
        mock_client.get_body_by_id.assert_called_once()
        call_args = mock_client.get_body_by_id.call_args
        assert call_args[0][0] == "body1" or call_args.kwargs.get("body_id") == "body1"
        assert call_args.kwargs.get("include_faces") is True
        assert call_args.kwargs.get("include_edges") is True


class TestCreationTools:
    """Tests for creation tools."""

    @pytest.mark.asyncio
    async def test_create_box_registered(self, mcp):
        """Test that create_box tool is registered."""
        register_creation_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "create_box" in tools

    @pytest.mark.asyncio
    async def test_create_cylinder_registered(self, mcp):
        """Test that create_cylinder tool is registered."""
        register_creation_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "create_cylinder" in tools

    @pytest.mark.asyncio
    async def test_create_sketch_registered(self, mcp):
        """Test that create_sketch tool is registered."""
        register_creation_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "create_sketch" in tools

    @pytest.mark.asyncio
    async def test_draw_tools_registered(self, mcp):
        """Test that draw tools are registered."""
        register_creation_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "draw_line" in tools
        assert "draw_circle" in tools
        assert "draw_rectangle" in tools
        assert "draw_arc" in tools

    @pytest.mark.asyncio
    async def test_extrude_registered(self, mcp):
        """Test that extrude tool is registered."""
        register_creation_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "extrude" in tools

    @pytest.mark.asyncio
    async def test_revolve_registered(self, mcp):
        """Test that revolve tool is registered."""
        register_creation_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "revolve" in tools

    @pytest.mark.asyncio
    async def test_fillet_chamfer_registered(self, mcp):
        """Test that fillet and chamfer tools are registered."""
        register_creation_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "fillet" in tools
        assert "chamfer" in tools

    @pytest.mark.asyncio
    async def test_create_hole_registered(self, mcp):
        """Test that create_hole tool is registered."""
        register_creation_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "create_hole" in tools

    @pytest.mark.asyncio
    @patch('fusion360_mcp_server.tools.creation_tools.FusionClient')
    async def test_create_box_calls_client(self, MockClient, mcp, mock_client):
        """Test that create_box calls FusionClient correctly."""
        MockClient.return_value = mock_client
        mock_client.create_box.return_value = {
            "body_id": "box1",
            "feature_id": "extrude1",
        }

        register_creation_tools(mcp)
        tool = mcp._tool_manager._tools["create_box"]
        result = await tool.fn(
            width=100.0,
            depth=50.0,
            height=20.0,
            x=0.0,
            y=0.0,
            z=0.0,
            name="TestBox",
        )

        mock_client.create_box.assert_called_once()
        assert result["body_id"] == "box1"

    @pytest.mark.asyncio
    @patch('fusion360_mcp_server.tools.creation_tools.FusionClient')
    async def test_extrude_calls_client(self, MockClient, mcp, mock_client):
        """Test that extrude calls FusionClient with correct args."""
        MockClient.return_value = mock_client
        mock_client.extrude.return_value = {
            "feature_id": "extrude1",
            "body_id": "body1",
        }

        register_creation_tools(mcp)
        tool = mcp._tool_manager._tools["extrude"]
        result = await tool.fn(
            sketch_id="sketch1",
            distance=25.0,
            direction="positive",
            operation="new_body",
        )

        mock_client.extrude.assert_called_once()
        assert result["feature_id"] == "extrude1"


class TestModificationTools:
    """Tests for modification tools."""

    @pytest.mark.asyncio
    async def test_move_body_registered(self, mcp):
        """Test that move_body tool is registered."""
        register_modification_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "move_body" in tools

    @pytest.mark.asyncio
    async def test_rotate_body_registered(self, mcp):
        """Test that rotate_body tool is registered."""
        register_modification_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "rotate_body" in tools

    @pytest.mark.asyncio
    async def test_modify_feature_registered(self, mcp):
        """Test that modify_feature tool is registered."""
        register_modification_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "modify_feature" in tools

    @pytest.mark.asyncio
    async def test_update_parameter_registered(self, mcp):
        """Test that update_parameter tool is registered."""
        register_modification_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "update_parameter" in tools

    @pytest.mark.asyncio
    async def test_delete_tools_registered(self, mcp):
        """Test that delete tools are registered."""
        register_modification_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "delete_body" in tools
        assert "delete_feature" in tools

    @pytest.mark.asyncio
    async def test_edit_sketch_registered(self, mcp):
        """Test that edit_sketch tool is registered."""
        register_modification_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "edit_sketch" in tools

    @pytest.mark.asyncio
    @patch('fusion360_mcp_server.tools.modification_tools.FusionClient')
    async def test_move_body_calls_client(self, MockClient, mcp, mock_client):
        """Test that move_body calls FusionClient correctly."""
        MockClient.return_value = mock_client
        mock_client.move_body.return_value = {
            "feature_id": "move1",
            "new_position": {"x": 10, "y": 20, "z": 0},
        }

        register_modification_tools(mcp)
        tool = mcp._tool_manager._tools["move_body"]
        result = await tool.fn(body_id="body1", x=10.0, y=20.0, z=0.0)

        mock_client.move_body.assert_called_once_with(
            body_id="body1", x=10.0, y=20.0, z=0.0
        )
        assert result["feature_id"] == "move1"


class TestValidationTools:
    """Tests for validation tools."""

    @pytest.mark.asyncio
    async def test_measure_distance_registered(self, mcp):
        """Test that measure_distance tool is registered."""
        register_validation_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "measure_distance" in tools

    @pytest.mark.asyncio
    async def test_measure_angle_registered(self, mcp):
        """Test that measure_angle tool is registered."""
        register_validation_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "measure_angle" in tools

    @pytest.mark.asyncio
    async def test_check_interference_registered(self, mcp):
        """Test that check_interference tool is registered."""
        register_validation_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "check_interference" in tools

    @pytest.mark.asyncio
    async def test_get_body_properties_registered(self, mcp):
        """Test that get_body_properties tool is registered."""
        register_validation_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "get_body_properties" in tools

    @pytest.mark.asyncio
    async def test_get_sketch_status_registered(self, mcp):
        """Test that get_sketch_status tool is registered."""
        register_validation_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "get_sketch_status" in tools

    @pytest.mark.asyncio
    @patch('fusion360_mcp_server.tools.validation_tools.FusionClient')
    async def test_measure_distance_calls_client(self, MockClient, mcp, mock_client):
        """Test that measure_distance calls FusionClient correctly."""
        MockClient.return_value = mock_client
        mock_client.measure_distance.return_value = {
            "distance": 25.5,
            "point1": {"x": 0, "y": 0, "z": 0},
            "point2": {"x": 25.5, "y": 0, "z": 0},
        }

        register_validation_tools(mcp)
        tool = mcp._tool_manager._tools["measure_distance"]
        result = await tool.fn(entity1_id="body1", entity2_id="body2")

        mock_client.measure_distance.assert_called_once_with("body1", "body2")
        assert result["distance"] == 25.5

    @pytest.mark.asyncio
    @patch('fusion360_mcp_server.tools.validation_tools.FusionClient')
    async def test_check_interference_calls_client(self, MockClient, mcp, mock_client):
        """Test that check_interference calls FusionClient correctly."""
        MockClient.return_value = mock_client
        mock_client.check_interference.return_value = {
            "has_interference": False,
            "interferences": [],
        }

        register_validation_tools(mcp)
        tool = mcp._tool_manager._tools["check_interference"]
        result = await tool.fn(body_ids=["body1", "body2"])

        mock_client.check_interference.assert_called_once_with(["body1", "body2"])
        assert result["has_interference"] is False


class TestSystemTools:
    """Tests for system tools."""

    @pytest.mark.asyncio
    async def test_check_health_registered(self, mcp):
        """Test that check_health tool is registered."""
        register_system_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "check_health" in tools

    @pytest.mark.asyncio
    async def test_get_version_registered(self, mcp):
        """Test that get_version tool is registered."""
        register_system_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "get_version" in tools

    @pytest.mark.asyncio
    @patch('fusion360_mcp_server.tools.system_tools.FusionClient')
    async def test_check_health_returns_status(self, MockClient, mcp, mock_client):
        """Test that check_health returns health status."""
        MockClient.return_value = mock_client
        mock_client.health_check.return_value = {
            "healthy": True,
            "status": "healthy",
            "message": "All systems operational",
            "version": "0.1.0",
        }

        register_system_tools(mcp)
        tool = mcp._tool_manager._tools["check_health"]
        result = await tool.fn()

        assert result["healthy"] is True
        assert result["server_status"] == "running"
        assert "server_version" in result

    @pytest.mark.asyncio
    @patch('fusion360_mcp_server.tools.system_tools.FusionClient')
    async def test_get_version_returns_versions(self, MockClient, mcp, mock_client):
        """Test that get_version returns version info."""
        MockClient.return_value = mock_client
        mock_client.get_version.return_value = {
            "addin_name": "FusionMCP",
            "addin_version": "0.1.0",
            "fusion_version": "2.0.18719",
            "api_version": "1.0",
        }

        register_system_tools(mcp)
        tool = mcp._tool_manager._tools["get_version"]
        result = await tool.fn()

        assert result["server_version"] == "0.1.0"
        assert result["addin_version"] == "0.1.0"
        assert result["fusion_version"] == "2.0.18719"


class TestToolDocstrings:
    """Tests for tool documentation."""

    @pytest.mark.asyncio
    async def test_query_tools_have_docstrings(self, mcp):
        """Test that all query tools have docstrings."""
        register_query_tools(mcp)
        for name, tool in mcp._tool_manager._tools.items():
            assert tool.description, f"Tool {name} missing description"

    @pytest.mark.asyncio
    async def test_creation_tools_have_docstrings(self, mcp):
        """Test that all creation tools have docstrings."""
        register_creation_tools(mcp)
        for name, tool in mcp._tool_manager._tools.items():
            assert tool.description, f"Tool {name} missing description"

    @pytest.mark.asyncio
    async def test_modification_tools_have_docstrings(self, mcp):
        """Test that all modification tools have docstrings."""
        register_modification_tools(mcp)
        for name, tool in mcp._tool_manager._tools.items():
            assert tool.description, f"Tool {name} missing description"

    @pytest.mark.asyncio
    async def test_validation_tools_have_docstrings(self, mcp):
        """Test that all validation tools have docstrings."""
        register_validation_tools(mcp)
        for name, tool in mcp._tool_manager._tools.items():
            assert tool.description, f"Tool {name} missing description"

    @pytest.mark.asyncio
    async def test_system_tools_have_docstrings(self, mcp):
        """Test that all system tools have docstrings."""
        register_system_tools(mcp)
        for name, tool in mcp._tool_manager._tools.items():
            assert tool.description, f"Tool {name} missing description"


class TestLoftToolWithTargetBody:
    """Tests for loft tool with target_body_id parameter."""

    @pytest.mark.asyncio
    async def test_loft_registered(self, mcp):
        """Test that loft tool is registered."""
        register_creation_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "loft" in tools

    @pytest.mark.asyncio
    @patch('fusion360_mcp_server.tools.creation_tools.FusionClient')
    async def test_loft_new_body_no_target_required(self, MockClient, mcp, mock_client):
        """Test loft with new_body operation doesn't require target_body_id."""
        MockClient.return_value = mock_client
        mock_client.loft.return_value = {
            "feature_id": "loft1",
            "bodies": [{"id": "body1", "name": "Loft"}],
        }

        register_creation_tools(mcp)
        tool = mcp._tool_manager._tools["loft"]
        result = await tool.fn(
            sketch_ids=["sketch1", "sketch2"],
            operation="new_body"
        )

        mock_client.loft.assert_called_once()
        assert result["feature_id"] == "loft1"

    @pytest.mark.asyncio
    @patch('fusion360_mcp_server.tools.creation_tools.FusionClient')
    async def test_loft_cut_passes_target_body(self, MockClient, mcp, mock_client):
        """Test loft with cut operation passes target_body_id correctly."""
        MockClient.return_value = mock_client
        mock_client.loft.return_value = {
            "feature_id": "loft2",
            "bodies": [{"id": "body1", "volume": 50000.0}],
        }

        register_creation_tools(mcp)
        tool = mcp._tool_manager._tools["loft"]
        result = await tool.fn(
            sketch_ids=["inner1", "inner2"],
            operation="cut",
            target_body_id="outer_body"
        )

        # Verify target_body_id was passed to client
        call_kwargs = mock_client.loft.call_args.kwargs
        assert call_kwargs.get("target_body_id") == "outer_body"
        assert call_kwargs.get("operation") == "cut"
        assert result["feature_id"] == "loft2"

    @pytest.mark.asyncio
    @patch('fusion360_mcp_server.tools.creation_tools.FusionClient')
    async def test_loft_join_passes_target_body(self, MockClient, mcp, mock_client):
        """Test loft with join operation passes target_body_id correctly."""
        MockClient.return_value = mock_client
        mock_client.loft.return_value = {
            "feature_id": "loft3",
            "bodies": [{"id": "body1", "volume": 150000.0}],
        }

        register_creation_tools(mcp)
        tool = mcp._tool_manager._tools["loft"]
        result = await tool.fn(
            sketch_ids=["sketch1", "sketch2"],
            operation="join",
            target_body_id="existing_body"
        )

        call_kwargs = mock_client.loft.call_args.kwargs
        assert call_kwargs.get("target_body_id") == "existing_body"
        assert call_kwargs.get("operation") == "join"

    @pytest.mark.asyncio
    @patch('fusion360_mcp_server.tools.creation_tools.FusionClient')
    async def test_loft_intersect_passes_target_body(self, MockClient, mcp, mock_client):
        """Test loft with intersect operation passes target_body_id correctly."""
        MockClient.return_value = mock_client
        mock_client.loft.return_value = {
            "feature_id": "loft4",
            "bodies": [{"id": "body1"}],
        }

        register_creation_tools(mcp)
        tool = mcp._tool_manager._tools["loft"]
        result = await tool.fn(
            sketch_ids=["sketch1", "sketch2"],
            operation="intersect",
            target_body_id="intersect_body"
        )

        call_kwargs = mock_client.loft.call_args.kwargs
        assert call_kwargs.get("target_body_id") == "intersect_body"
        assert call_kwargs.get("operation") == "intersect"


class TestEmbossToolApiLimitation:
    """Tests for emboss tool with API limitation documentation."""

    @pytest.mark.asyncio
    async def test_emboss_registered(self, mcp):
        """Test that emboss tool is registered."""
        register_creation_tools(mcp)
        tools = mcp._tool_manager._tools
        assert "emboss" in tools

    @pytest.mark.asyncio
    async def test_emboss_has_warning_in_docstring(self, mcp):
        """Test that emboss tool docstring contains API limitation warning."""
        register_creation_tools(mcp)
        tool = mcp._tool_manager._tools["emboss"]
        description = tool.description

        # Check for warning about API limitation
        assert "NOT CURRENTLY SUPPORTED" in description or "WARNING" in description
        assert "preview" in description.lower() or "alternative" in description.lower()

    @pytest.mark.asyncio
    @patch('fusion360_mcp_server.tools.creation_tools.FusionClient')
    async def test_emboss_calls_client(self, MockClient, mcp, mock_client):
        """Test that emboss tool calls FusionClient (which returns error)."""
        MockClient.return_value = mock_client
        # Simulate the error that the backend returns
        from fusion360_mcp_server.exceptions import FusionMCPError
        mock_client.emboss.side_effect = FusionMCPError(
            "EmbossFeatures API does not support programmatic creation"
        )

        register_creation_tools(mcp)
        tool = mcp._tool_manager._tools["emboss"]

        with pytest.raises(FusionMCPError):
            await tool.fn(
                sketch_id="text_sketch",
                face_id="body1_face_0",
                depth=0.5,
                is_emboss=True
            )
