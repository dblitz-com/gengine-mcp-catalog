#!/usr/bin/env python3
"""
Test server endpoints not covered in other test files
"""

import pytest
from unittest.mock import patch
from httpx import AsyncClient


@pytest.mark.asyncio
class TestServerEndpoints:
    """Test server endpoints for better coverage"""
    
    @pytest.fixture
    def mock_registry(self):
        """Mock server registry with test servers"""
        return {
            "github": {
                "id": "github",
                "name": "GitHub MCP",
                "description": "GitHub operations",
                "category": "development",
                "vendor": "Anthropic",
                "homepage": "https://github.com/anthropics/mcp-server-github",
                "license": "MIT",
                "installation": {
                    "command": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-github"]
                    }
                },
                "config": {
                    "env": {
                        "GITHUB_PERSONAL_ACCESS_TOKEN": {"required": True}
                    }
                },
                "features": ["repository-management", "issue-tracking"],
                "supported_platforms": ["linux", "macos", "windows"],
                "capabilities": {
                    "tools": True,
                    "resources": False,
                    "prompts": False
                }
            },
            "filesystem": {
                "id": "filesystem",
                "name": "Filesystem MCP",
                "description": "File operations",
                "category": "utility",
                "vendor": "community",
                "homepage": "https://github.com/modelcontextprotocol/filesystem",
                "license": "Apache-2.0",
                "features": ["file-reading", "file-writing"],
                "supported_platforms": ["all"]
            },
            "weather": {
                "id": "weather",
                "name": "Weather API",
                "description": "Weather data provider",
                "category": "data",
                # Missing some optional fields to test defaults
            }
        }
    
    @pytest.mark.asyncio
    async def test_list_servers_success(self, client: AsyncClient, mock_registry):
        """Test successful server listing"""
        with patch("api.routers.servers.get_server_registry", return_value=mock_registry):
            response = await client.get("/api/v1/servers")
            assert response.status_code == 200
            
            data = response.json()
            assert data["total"] == 3
            assert len(data["servers"]) == 3
            
            # Check server details
            github_server = next(s for s in data["servers"] if s["id"] == "github")
            assert github_server["name"] == "GitHub MCP"
            assert github_server["category"] == "development"
            assert github_server["vendor"] == "Anthropic"
            
            # Check defaults for weather server
            weather_server = next(s for s in data["servers"] if s["id"] == "weather")
            assert weather_server["category"] == "data"  # from mock_registry
            assert weather_server["vendor"] == "community"  # default
            assert weather_server["homepage"] == ""  # default
    
    @pytest.mark.asyncio
    async def test_search_servers_by_query(self, client: AsyncClient, mock_registry):
        """Test server search by query"""
        with patch("api.routers.servers.get_server_registry", return_value=mock_registry):
            # Search by name
            response = await client.get("/api/v1/servers/search?q=GitHub")
            assert response.status_code == 200
            
            data = response.json()
            assert data["total"] == 1
            assert data["query"] == "GitHub"
            assert data["results"][0]["id"] == "github"
            
            # Search by description
            response = await client.get("/api/v1/servers/search?q=file")
            assert response.status_code == 200
            
            data = response.json()
            assert data["total"] == 1
            assert data["results"][0]["id"] == "filesystem"
            
            # Search by ID
            response = await client.get("/api/v1/servers/search?q=weather")
            assert response.status_code == 200
            
            data = response.json()
            assert data["total"] == 1
            assert data["results"][0]["id"] == "weather"
    
    @pytest.mark.asyncio
    async def test_search_servers_by_category(self, client: AsyncClient, mock_registry):
        """Test server search by category"""
        with patch("api.routers.servers.get_server_registry", return_value=mock_registry):
            response = await client.get("/api/v1/servers/search?category=development")
            assert response.status_code == 200
            
            data = response.json()
            assert data["total"] == 1
            assert data["category"] == "development"
            assert data["results"][0]["id"] == "github"
    
    @pytest.mark.asyncio
    async def test_search_servers_query_and_category(self, client: AsyncClient, mock_registry):
        """Test server search with both query and category"""
        with patch("api.routers.servers.get_server_registry", return_value=mock_registry):
            # Should match both query and category
            response = await client.get("/api/v1/servers/search?q=GitHub&category=development")
            assert response.status_code == 200
            
            data = response.json()
            assert data["total"] == 1
            assert data["query"] == "GitHub"
            assert data["category"] == "development"
            assert data["results"][0]["id"] == "github"
            
            # Should not match - wrong category
            response = await client.get("/api/v1/servers/search?q=GitHub&category=utility")
            assert response.status_code == 200
            
            data = response.json()
            assert data["total"] == 0
    
    @pytest.mark.asyncio
    async def test_search_servers_no_params(self, client: AsyncClient):
        """Test search with no query or category parameters"""
        response = await client.get("/api/v1/servers/search")
        assert response.status_code == 400
        assert "Query parameter 'q' or 'category' required" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_search_servers_case_insensitive(self, client: AsyncClient, mock_registry):
        """Test search is case insensitive"""
        with patch("api.routers.servers.get_server_registry", return_value=mock_registry):
            response = await client.get("/api/v1/servers/search?q=github")  # lowercase
            assert response.status_code == 200
            
            data = response.json()
            assert data["total"] == 1
            assert data["results"][0]["id"] == "github"
    
    @pytest.mark.asyncio
    async def test_get_server_info_success(self, client: AsyncClient, mock_registry):
        """Test successful server info retrieval"""
        with patch("api.routers.servers.get_server_by_id", side_effect=lambda x: mock_registry.get(x)):
            response = await client.get("/api/v1/servers/github")
            assert response.status_code == 200
            
            data = response.json()
            assert data["id"] == "github"
            assert data["name"] == "GitHub MCP"
            assert data["description"] == "GitHub operations"
            assert data["category"] == "development"
            assert data["vendor"] == "Anthropic"
            assert data["homepage"] == "https://github.com/anthropics/mcp-server-github"
            assert data["license"] == "MIT"
            assert "installation" in data
            assert "config" in data
            assert data["features"] == ["repository-management", "issue-tracking"]
            assert data["supported_platforms"] == ["linux", "macos", "windows"]
            assert "capabilities" in data
            assert data["capabilities"]["tools"] is True
    
    @pytest.mark.asyncio
    async def test_get_server_info_not_found(self, client: AsyncClient):
        """Test server info for non-existent server"""
        with patch("api.routers.servers.get_server_by_id", return_value=None):
            response = await client.get("/api/v1/servers/nonexistent")
            assert response.status_code == 404
            assert "Server 'nonexistent' not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_server_info_defaults(self, client: AsyncClient, mock_registry):
        """Test server info with default values"""
        with patch("api.routers.servers.get_server_by_id", side_effect=lambda x: mock_registry.get(x)):
            response = await client.get("/api/v1/servers/weather")
            assert response.status_code == 200
            
            data = response.json()
            assert data["id"] == "weather"
            assert data["category"] == "data"  # from mock_registry, not default
            assert data["vendor"] == "community"  # default
            assert data["homepage"] == ""  # default
            assert data["license"] == "Unknown"  # default
            assert "installation" in data  # installation field is present
            assert "config" in data  # config field is present
            assert data["features"] == []  # default
            assert data["supported_platforms"] == ["all"]  # default
            # capabilities field should not exist if not in server config
    
    @pytest.mark.asyncio
    async def test_list_categories_success(self, client: AsyncClient, mock_registry):
        """Test successful category listing"""
        with patch("api.routers.servers.get_server_registry", return_value=mock_registry):
            response = await client.get("/api/v1/categories")
            assert response.status_code == 200
            
            data = response.json()
            assert "categories" in data
            
            # Convert to dict for easier testing
            categories = {cat["name"]: cat["count"] for cat in data["categories"]}
            
            assert categories["development"] == 1  # github
            assert categories["utility"] == 1      # filesystem
            assert categories["data"] == 1         # weather
            
    @pytest.mark.asyncio
    async def test_list_categories_empty_registry(self, client: AsyncClient):
        """Test category listing with empty registry"""
        with patch("api.routers.servers.get_server_registry", return_value={}):
            response = await client.get("/api/v1/categories")
            assert response.status_code == 200
            
            data = response.json()
            assert data["categories"] == []
    
    @pytest.mark.asyncio
    async def test_search_servers_no_results(self, client: AsyncClient, mock_registry):
        """Test search with no matching results"""
        with patch("api.routers.servers.get_server_registry", return_value=mock_registry):
            response = await client.get("/api/v1/servers/search?q=nonexistent")
            assert response.status_code == 200
            
            data = response.json()
            assert data["total"] == 0
            assert data["results"] == []
            assert data["query"] == "nonexistent"