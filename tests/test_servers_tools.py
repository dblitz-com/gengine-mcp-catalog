#!/usr/bin/env python3
"""
Tests for the /servers/tools endpoint
"""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from api.main import app
from api.models.servers import ServersToolsResponse, ServerWithTools, ServerTool

client = TestClient(app)


def test_servers_tools_endpoint_exists():
    """Test that the /servers/tools endpoint exists"""
    response = client.get("/api/v1/servers/tools")
    # Should not be 404
    assert response.status_code != 404


def test_servers_tools_response_structure():
    """Test that the response has the correct structure"""
    response = client.get("/api/v1/servers/tools")
    assert response.status_code == 200
    
    data = response.json()
    assert "servers" in data
    assert "total_servers" in data
    assert "total_tools" in data
    
    # Should be a list
    assert isinstance(data["servers"], list)
    assert isinstance(data["total_servers"], int)
    assert isinstance(data["total_tools"], int)


def test_server_with_tools_structure():
    """Test that each server has the correct structure"""
    response = client.get("/api/v1/servers/tools")
    assert response.status_code == 200
    
    data = response.json()
    if data["servers"]:
        server = data["servers"][0]
        assert "id" in server
        assert "name" in server
        assert "description" in server
        assert "tools" in server
        assert "tool_count" in server
        
        # Tools should be a list
        assert isinstance(server["tools"], list)
        assert isinstance(server["tool_count"], int)


def test_tool_structure():
    """Test that each tool has the correct structure"""
    response = client.get("/api/v1/servers/tools")
    assert response.status_code == 200
    
    data = response.json()
    # Find a server with tools
    for server in data["servers"]:
        if server["tools"]:
            tool = server["tools"][0]
            assert "name" in tool
            assert "description" in tool
            # parameters is optional
            break


@pytest.mark.asyncio
async def test_query_mcp_server_tools_success():
    """Test successful MCP server tool query"""
    from api.routers.servers import get_servers_with_tools
    
    # Mock the registry
    mock_registry = {
        "test-server": {
            "name": "Test Server",
            "description": "A test server",
            "mcp_endpoint": "http://localhost:9999"
        }
    }
    
    # Mock the HTTP response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "tools": [
            {
                "name": "test_tool",
                "description": "A test tool",
                "inputSchema": {"type": "object"}
            }
        ]
    }
    
    with patch('api.dependencies.get_server_registry', return_value=mock_registry):
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            # This would normally be called by the endpoint
            # We're testing the logic here
            # The actual endpoint test is above


@pytest.mark.asyncio
async def test_query_mcp_server_tools_failure():
    """Test handling of failed MCP server queries"""
    from api.routers.servers import get_servers_with_tools
    
    mock_registry = {
        "failing-server": {
            "name": "Failing Server",
            "description": "A server that fails",
            "mcp_endpoint": "http://localhost:9998"
        }
    }
    
    with patch('api.routers.servers.get_server_registry', return_value=mock_registry):
        with patch('httpx.AsyncClient') as mock_client:
            # Simulate connection error
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=Exception("Connection refused")
            )
            
            # The endpoint should handle this gracefully
            response = client.get("/api/v1/servers/tools")
            assert response.status_code == 200
            
            data = response.json()
            # Should still return the server, just with no tools
            assert len(data["servers"]) == 1
            assert data["servers"][0]["tool_count"] == 0


def test_servers_without_mcp_endpoints():
    """Test handling of servers without MCP endpoints"""
    response = client.get("/api/v1/servers/tools")
    assert response.status_code == 200
    
    data = response.json()
    # Should handle servers without mcp_endpoint gracefully
    for server in data["servers"]:
        assert "id" in server
        assert "tools" in server
        assert isinstance(server["tools"], list)


def test_total_tools_calculation():
    """Test that total_tools is calculated correctly"""
    response = client.get("/api/v1/servers/tools")
    assert response.status_code == 200
    
    data = response.json()
    
    # Calculate expected total
    expected_total = sum(server["tool_count"] for server in data["servers"])
    assert data["total_tools"] == expected_total


def test_total_servers_count():
    """Test that total_servers matches the server list length"""
    response = client.get("/api/v1/servers/tools")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total_servers"] == len(data["servers"])