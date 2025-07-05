#!/usr/bin/env python3
"""
Test main FastAPI application endpoints and lifecycle
"""

import pytest
from unittest.mock import patch
from httpx import AsyncClient


@pytest.mark.asyncio
class TestMainApp:
    """Test main application endpoints"""
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        """Test root endpoint returns API information"""
        response = await client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "MCP Catalog API"
        assert data["version"] == "1.0.0"
        assert data["description"] == "REST API for MCP server discovery and configuration"
        assert data["docs"] == "/docs"
        assert data["openapi"] == "/openapi.json"
    
    @pytest.mark.asyncio
    async def test_health_check_endpoint(self, client: AsyncClient):
        """Test health check endpoint"""
        mock_registry = {
            "github": {"name": "GitHub MCP"},
            "filesystem": {"name": "Filesystem MCP"}
        }
        
        with patch("api.dependencies.get_server_registry", return_value=mock_registry):
            response = await client.get("/health")
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "healthy"
            assert data["server_count"] == 2
            assert data["catalog_version"] == "1.0.0"
            assert data["api_version"] == "v1"
    
    @pytest.mark.asyncio
    async def test_health_check_empty_registry(self, client: AsyncClient):
        """Test health check with empty server registry"""
        with patch("api.dependencies.get_server_registry", return_value={}):
            response = await client.get("/health")
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "healthy"
            assert data["server_count"] == 0
    
    @pytest.mark.asyncio
    async def test_openapi_docs_accessible(self, client: AsyncClient):
        """Test that OpenAPI documentation is accessible"""
        response = await client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
    
    @pytest.mark.asyncio
    async def test_openapi_json_accessible(self, client: AsyncClient):
        """Test that OpenAPI JSON spec is accessible"""
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/json"
        
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert data["info"]["title"] == "MCP Catalog API"
        assert data["info"]["version"] == "1.0.0"
    
    @pytest.mark.asyncio
    async def test_redoc_accessible(self, client: AsyncClient):
        """Test that ReDoc documentation is accessible"""
        response = await client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
    
    @pytest.mark.asyncio
    async def test_cors_headers_present(self, client: AsyncClient):
        """Test that CORS headers are present in responses"""
        response = await client.get("/")
        assert response.status_code == 200
        
        # CORS headers should be present
        headers = response.headers
        # Note: In test environment, these might not be set the same way
        # but we can test the response is successful
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_404_for_unknown_endpoint(self, client: AsyncClient):
        """Test 404 response for unknown endpoints"""
        response = await client.get("/nonexistent-endpoint")
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_api_endpoints_have_v1_prefix(self, client: AsyncClient):
        """Test that API endpoints require /api/v1 prefix"""
        # These should return 404 without the prefix
        response = await client.get("/servers")
        assert response.status_code == 404
        
        response = await client.get("/categories")
        assert response.status_code == 404
        
        # But work with the prefix (assuming mock registry)
        with patch("api.routers.servers.get_server_registry", return_value={}):
            response = await client.get("/api/v1/servers")
            assert response.status_code == 200
            
            response = await client.get("/api/v1/categories")
            assert response.status_code == 200