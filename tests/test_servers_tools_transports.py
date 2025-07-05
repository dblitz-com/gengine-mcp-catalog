#!/usr/bin/env python3
"""
Test /servers/tools endpoint with different MCP transport types
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
import json

from api.models.servers import ServerTool


@pytest.mark.asyncio
class TestServersToolsTransports:
    """Test /servers/tools endpoint with various transport types"""
    
    @pytest.fixture
    def mock_registry(self):
        """Mock server registry with various transport configurations"""
        return {
            # HTTP server with explicit endpoint
            "weather-api": {
                "id": "weather-api",
                "name": "Weather API",
                "description": "Weather data via HTTP",
                "mcp_endpoint": "https://weather.example.com/mcp",
                "transport": "http",
                "package": {
                    "name": "weather-api-mcp",
                    "registry": "npm"
                },
                "config": {
                    "env": {},
                    "args": []
                }
            },
            # SSE server
            "live-data": {
                "id": "live-data",
                "name": "Live Data Stream", 
                "description": "Real-time data via SSE",
                "mcp_endpoint": "https://stream.example.com/sse",
                "transport": "sse",
                "package": {
                    "name": "live-data-mcp",
                    "registry": "npm"
                },
                "config": {
                    "env": {},
                    "args": []
                }
            },
            # NPX server (stdio)
            "github": {
                "id": "github",
                "name": "GitHub MCP",
                "description": "GitHub operations via NPX",
                "package": {
                    "name": "@modelcontextprotocol/server-github",
                    "registry": "npm"
                },
                "config": {
                    "env": {
                        "GITHUB_PERSONAL_ACCESS_TOKEN": {"required": True}
                    },
                    "args": []
                }
            },
            # Python server (stdio)
            "filesystem": {
                "id": "filesystem",
                "name": "Filesystem MCP",
                "description": "File operations via Python",
                "package": {
                    "name": "@modelcontextprotocol/server-filesystem",
                    "registry": "npm"
                },
                "config": {
                    "env": {},
                    "args": []
                }
            }
        }
    
    @pytest.mark.asyncio
    async def test_http_server_tools(self, client: AsyncClient, mock_registry):
        """Test querying tools from HTTP MCP servers"""
        with patch("api.routers.servers.get_server_registry", 
                   return_value=mock_registry):
            
            # Mock successful HTTP response
            mock_http_response = {
                "tools": [
                    {
                        "name": "get_weather",
                        "description": "Get weather for a city",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "city": {"type": "string"}
                            }
                        }
                    },
                    {
                        "name": "get_forecast",
                        "description": "Get weather forecast",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "city": {"type": "string"},
                                "days": {"type": "integer"}
                            }
                        }
                    }
                ]
            }
            
            with patch("httpx.AsyncClient.post", 
                       return_value=AsyncMock(status_code=200, 
                                             json=lambda: mock_http_response)):
                
                response = await client.get("/api/v1/servers/tools")
                assert response.status_code == 200
                
                data = response.json()
                
                # Find weather-api server
                weather_server = next((s for s in data["servers"] if s["id"] == "weather-api"), None)
                assert weather_server is not None, f"weather-api server not found in {[s['id'] for s in data['servers']]}"
                assert weather_server["tool_count"] == 2
                assert len(weather_server["tools"]) == 2
                assert weather_server["tools"][0]["name"] == "get_weather"
    
    @pytest.mark.asyncio
    async def test_sse_server_tools(self, client: AsyncClient, mock_registry):
        """Test querying tools from SSE MCP servers"""
        with patch("api.routers.servers.get_server_registry", 
                   return_value=mock_registry):
            
            # Mock SSE response
            mock_sse_response = {
                "tools": [
                    {
                        "name": "subscribe_updates",
                        "description": "Subscribe to live updates"
                    }
                ]
            }
            
            with patch("httpx.AsyncClient.post",
                       return_value=AsyncMock(status_code=200,
                                             json=lambda: mock_sse_response)):
                
                response = await client.get("/api/v1/servers/tools")
                assert response.status_code == 200
                
                data = response.json()
                
                # Find live-data server
                live_server = next(s for s in data["servers"] if s["id"] == "live-data")
                assert live_server["tool_count"] == 1
                assert live_server["tools"][0]["name"] == "subscribe_updates"
    
    @pytest.mark.asyncio
    async def test_stdio_server_tools(self, client: AsyncClient, mock_registry):
        """Test querying tools from stdio-based MCP servers"""
        with patch("api.routers.servers.get_server_registry", 
                   return_value=mock_registry):
            
            # Mock subprocess manager for stdio servers
            mock_subprocess_manager = MagicMock()
            
            # Mock different tool responses for each server type
            tool_responses = {
                "github": {
                    "tools": [
                        {"name": "create_issue", "description": "Create GitHub issue"},
                        {"name": "list_repos", "description": "List repositories"}
                    ]
                },
                "filesystem": {
                    "tools": [
                        {"name": "read_file", "description": "Read file contents"},
                        {"name": "write_file", "description": "Write to file"},
                        {"name": "list_directory", "description": "List directory"}
                    ]
                },
                "database": {
                    "tools": [
                        {"name": "query", "description": "Execute SQL query"},
                        {"name": "list_tables", "description": "List database tables"}
                    ]
                },
                "analyzer": {
                    "tools": [
                        {"name": "analyze_code", "description": "Analyze code quality"}
                    ]
                }
            }
            
            async def mock_list_tools(server_name):
                return tool_responses.get(server_name, {"tools": []})
            
            async def mock_start_server(server_name, config):
                return True
            
            mock_subprocess_manager.list_tools = AsyncMock(side_effect=mock_list_tools)
            mock_subprocess_manager.start_server = AsyncMock(side_effect=mock_start_server)
            mock_subprocess_manager.cleanup = AsyncMock()
            mock_subprocess_manager.processes = {}
            
            with patch("api.routers.servers.get_subprocess_manager",
                       return_value=mock_subprocess_manager):
                
                response = await client.get("/api/v1/servers/tools")
                assert response.status_code == 200
                
                data = response.json()
                assert data["total_servers"] >= 4  # At least our stdio servers
                
                # Check each stdio server
                for server_id, expected_tools in tool_responses.items():
                    server = next((s for s in data["servers"] if s["id"] == server_id), None)
                    if server:  # Server might be filtered by env vars
                        assert server["tool_count"] == len(expected_tools["tools"])
                        assert len(server["tools"]) == server["tool_count"]
    
    @pytest.mark.asyncio
    async def test_mixed_transport_types(self, client: AsyncClient, mock_registry):
        """Test endpoint handles mixed transport types correctly"""
        with patch("api.routers.servers.get_server_registry", 
                   return_value=mock_registry):
            
            # Mock both HTTP and subprocess responses
            mock_http_response = {
                "tools": [{"name": "http_tool", "description": "HTTP tool"}]
            }
            
            mock_subprocess_manager = MagicMock()
            async def mock_list_tools(server_name):
                return {"tools": [{"name": f"{server_name}_tool", "description": f"{server_name} tool"}]}
            
            mock_subprocess_manager.list_tools = AsyncMock(side_effect=mock_list_tools)
            mock_subprocess_manager.start_server = AsyncMock(return_value=True)
            mock_subprocess_manager.cleanup = AsyncMock()
            mock_subprocess_manager.processes = {}
            
            with patch("httpx.AsyncClient.post",
                       return_value=AsyncMock(status_code=200,
                                             json=lambda: mock_http_response)), \
                 patch("api.routers.servers.get_subprocess_manager",
                       return_value=mock_subprocess_manager):
                
                response = await client.get("/api/v1/servers/tools")
                assert response.status_code == 200
                
                data = response.json()
                assert data["total_servers"] == len(mock_registry)
                
                # Verify we got tools from both HTTP and stdio servers
                http_servers = [s for s in data["servers"] 
                               if s["id"] in ["weather-api", "live-data"]]
                stdio_servers = [s for s in data["servers"] 
                                if s["id"] in ["github", "filesystem", "database", "analyzer"]]
                
                assert len(http_servers) >= 1
                assert len(stdio_servers) >= 1
                
                # All servers should have at least one tool
                for server in data["servers"]:
                    assert server["tool_count"] >= 1
    
    @pytest.mark.asyncio
    async def test_server_connection_failures(self, client: AsyncClient, mock_registry):
        """Test handling of connection failures for different transport types"""
        with patch("api.routers.servers.get_server_registry", 
                   return_value=mock_registry):
            
            # Mock HTTP connection failure
            with patch("httpx.AsyncClient.post",
                       side_effect=Exception("Connection refused")):
                
                # Mock subprocess manager that also fails
                mock_subprocess_manager = MagicMock()
                mock_subprocess_manager.list_tools = AsyncMock(
                    return_value={"error": "Failed to start server"})
                mock_subprocess_manager.start_server = AsyncMock(return_value=False)
                mock_subprocess_manager.cleanup = AsyncMock()
                mock_subprocess_manager.processes = {}
                
                with patch("api.routers.servers.get_subprocess_manager",
                          return_value=mock_subprocess_manager):
                    
                    response = await client.get("/api/v1/servers/tools")
                    assert response.status_code == 200
                    
                    data = response.json()
                    
                    # All servers should be present but with 0 tools
                    assert data["total_servers"] == len(mock_registry)
                    assert data["total_tools"] == 0
                    
                    for server in data["servers"]:
                        assert server["tool_count"] == 0
                        assert len(server["tools"]) == 0
    
    @pytest.mark.asyncio
    async def test_websocket_transport(self, client: AsyncClient):
        """Test handling WebSocket transport (future support)"""
        mock_registry = {
            "realtime": {
                "name": "Realtime Server",
                "description": "WebSocket-based MCP server",
                "mcp_endpoint": "wss://realtime.example.com/mcp",
                "transport": "websocket"
            }
        }
        
        with patch("api.routers.servers.get_server_registry", 
                   return_value=mock_registry):
            
            response = await client.get("/api/v1/servers/tools")
            assert response.status_code == 200
            
            data = response.json()
            
            # WebSocket servers should be included but may have 0 tools
            # (not implemented yet)
            ws_server = next(s for s in data["servers"] if s["id"] == "realtime")
            assert ws_server["name"] == "Realtime Server"
            assert ws_server["tool_count"] == 0  # Not implemented yet
    
    @pytest.mark.asyncio
    async def test_environment_variable_requirements(self, client: AsyncClient, mock_registry):
        """Test servers with missing environment variables return empty tools"""
        with patch("api.routers.servers.get_server_registry", 
                   return_value=mock_registry):
            
            # Mock subprocess manager
            mock_subprocess_manager = MagicMock()
            mock_subprocess_manager.list_tools = AsyncMock(
                return_value={"error": "Missing environment variables"})
            mock_subprocess_manager.start_server = AsyncMock(return_value=False)
            mock_subprocess_manager.cleanup = AsyncMock()
            mock_subprocess_manager.processes = {}
            
            # Remove required env vars
            with patch.dict("os.environ", {}, clear=True), \
                 patch("api.routers.servers.get_subprocess_manager",
                       return_value=mock_subprocess_manager):
                
                response = await client.get("/api/v1/servers/tools")
                assert response.status_code == 200
                
                data = response.json()
                
                # GitHub server requires GITHUB_PERSONAL_ACCESS_TOKEN
                github_server = next(s for s in data["servers"] if s["id"] == "github")
                assert github_server["tool_count"] == 0
                
                # Filesystem server should have 0 tools (no env vars required, but no mocked tools)
                filesystem_server = next(s for s in data["servers"] if s["id"] == "filesystem")
                assert filesystem_server["tool_count"] == 0