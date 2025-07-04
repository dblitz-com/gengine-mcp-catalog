#!/usr/bin/env python3
"""
Tests for servers router endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from api.main import app

@pytest.fixture
def client():
    """Create test client"""
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
            "homepage": "https://example.com"
        },
        "github": {
            "id": "github",
            "name": "GitHub Integration", 
            "description": "GitHub repository management",
            "category": "development",
            "vendor": "official",
            "homepage": "https://github.com"
        }
    }

class TestServerEndpoints:
    """Test server management endpoints"""
    
    @patch('api.routers.servers.get_server_registry')
    def test_list_servers_empty(self, mock_get_registry, client):
        """Test listing servers when registry is empty"""
        mock_get_registry.return_value = {}
        
        response = client.get("/api/v1/servers")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["servers"] == []
    
    @patch('api.routers.servers.get_server_registry')
    def test_list_servers_with_data(self, mock_get_registry, client, mock_registry):
        """Test listing servers with mock data"""
        mock_get_registry.return_value = mock_registry
        
        response = client.get("/api/v1/servers")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["servers"]) == 2
        
        # Check server structure
        server = data["servers"][0]
        assert "id" in server
        assert "name" in server
        assert "description" in server
        assert "category" in server
        assert "vendor" in server
    
    @patch('api.routers.servers.get_server_by_id')
    def test_get_server_info(self, mock_get_server, client, mock_registry):
        """Test getting specific server info"""
        mock_get_server.return_value = mock_registry["github"]
        
        response = client.get("/api/v1/servers/github")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "github"
        assert data["name"] == "GitHub Integration"
        assert data["category"] == "development"
    
    @patch('api.routers.servers.get_server_by_id')
    def test_get_server_info_not_found(self, mock_get_server, client):
        """Test getting info for non-existent server"""
        mock_get_server.return_value = None
        
        response = client.get("/api/v1/servers/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    @patch('api.routers.servers.get_server_registry')
    def test_search_servers_by_query(self, mock_get_registry, client, mock_registry):
        """Test server search by query"""
        mock_get_registry.return_value = mock_registry
        
        response = client.get("/api/v1/servers/search?q=github")
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "github"
        assert data["total"] >= 0
        assert "results" in data
    
    @patch('api.routers.servers.get_server_registry')
    def test_search_servers_by_category(self, mock_get_registry, client, mock_registry):
        """Test server search by category"""
        mock_get_registry.return_value = mock_registry
        
        response = client.get("/api/v1/servers/search?category=development")
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "development"
        assert "results" in data
    
    def test_search_servers_no_params(self, client):
        """Test search without query or category fails"""
        response = client.get("/api/v1/servers/search")
        assert response.status_code == 400
        data = response.json()
        assert "required" in data["detail"].lower()
    
    @patch('api.routers.servers.get_server_registry')
    def test_list_categories(self, mock_get_registry, client, mock_registry):
        """Test listing categories"""
        mock_get_registry.return_value = mock_registry
        
        response = client.get("/api/v1/categories")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        
        categories = data["categories"]
        assert len(categories) > 0
        
        # Check category structure
        category = categories[0]
        assert "name" in category
        assert "count" in category
        assert isinstance(category["count"], int)