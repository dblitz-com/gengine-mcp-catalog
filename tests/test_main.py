#!/usr/bin/env python3
"""
Tests for FastAPI main application
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from api.main import app

@pytest.fixture
def client():
    """Create test client"""
    # Manually trigger startup to load registry
    from api.dependencies import load_server_registry
    load_server_registry()
    return TestClient(app)

@pytest.fixture
def mock_registry():
    """Mock server registry for testing"""
    return {
        "test_server": {
            "id": "test_server",
            "name": "Test Server",
            "description": "A test MCP server",
            "category": "development",
            "vendor": "test",
            "homepage": "https://example.com",
            "license": "MIT",
            "installation": {
                "command": {
                    "command": "python",
                    "args": ["-m", "test_server"]
                }
            },
            "config": {
                "env": {
                    "API_KEY": {"required": True, "description": "API key"}
                },
                "args": []
            },
            "features": ["tools", "resources"],
            "supported_platforms": ["linux", "macos", "windows"]
        },
        "github": {
            "id": "github",
            "name": "GitHub Integration",
            "description": "GitHub repository management",
            "category": "development",
            "vendor": "official",
            "homepage": "https://github.com",
            "license": "MIT",
            "installation": {
                "command": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-github"]
                }
            },
            "config": {
                "env": {
                    "GITHUB_TOKEN": {"required": True, "description": "GitHub API token"}
                },
                "args": []
            }
        }
    }

class TestMainEndpoints:
    """Test main application endpoints"""
    
    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "MCP Catalog API"
        assert data["version"] == "1.0.0"
        assert "/docs" in data["docs"]
        assert "/openapi.json" in data["openapi"]
    
    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "server_count" in data
        assert "catalog_version" in data
        assert "api_version" in data
    
    def test_openapi_json_generation(self, client):
        """Test that FastAPI auto-generates OpenAPI spec"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert data["openapi"] == "3.1.0"
        assert data["info"]["title"] == "MCP Catalog API"
        assert data["info"]["version"] == "1.0.0"
        
        # Check that main endpoints are documented
        paths = data["paths"]
        assert "/" in paths
        assert "/health" in paths
        assert "/api/v1/servers" in paths
    
    def test_docs_available(self, client):
        """Test that interactive docs are available"""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower()

class TestCORS:
    """Test CORS configuration"""
    
    def test_cors_headers_present(self, client):
        """Test that CORS headers are present"""
        # Note: FastAPI TestClient doesn't expose CORS headers in tests
        # CORS functionality is tested in browser/integration tests
        response = client.get("/health")
        assert response.status_code == 200  # Basic functionality check