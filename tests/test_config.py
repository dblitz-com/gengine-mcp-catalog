#!/usr/bin/env python3
"""
Tests for configuration router endpoints
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
                },
                "docker": {
                    "image": "mcp/github",
                    "tag": "latest"
                }
            },
            "config": {
                "env": {
                    "GITHUB_TOKEN": {"required": True, "description": "GitHub API token"},
                    "GITHUB_ORG": {"required": False, "description": "GitHub organization"}
                },
                "args": []
            }
        },
        "filesystem": {
            "id": "filesystem",
            "name": "Filesystem Access",
            "description": "Local filesystem operations",
            "category": "system",
            "vendor": "official",
            "installation": {
                "command": {
                    "command": "python",
                    "args": ["-m", "filesystem_server"]
                }
            },
            "config": {
                "env": {},
                "args": ["--root", "/path/to/files"]
            }
        }
    }

class TestConfigEndpoints:
    """Test configuration management endpoints"""
    
    @patch('api.routers.config.get_server_registry')
    @patch('api.routers.config.get_server_by_id')
    def test_generate_config_simple(self, mock_get_server, mock_get_registry, client, mock_registry):
        """Test basic config generation"""
        mock_get_registry.return_value = mock_registry
        mock_get_server.side_effect = lambda server_id: mock_registry.get(server_id)
        
        request_data = {
            "servers": ["github"],
            "format": "mcp",
            "include_env_vars": False
        }
        
        response = client.post("/api/v1/servers/generate-config", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["format"] == "mcp"
        assert "config" in data
        assert "mcpServers" in data["config"]
        assert "github" in data["config"]["mcpServers"]
        
        # Check generated config structure
        github_config = data["config"]["mcpServers"]["github"]
        assert github_config["command"] == "npx"
        assert "-y" in github_config["args"]
        assert "@modelcontextprotocol/server-github" in github_config["args"]
        
        assert data["servers_included"] == ["github"]
        assert "installation_notes" in data
    
    @patch('api.routers.config.get_server_registry')
    @patch('api.routers.config.get_server_by_id')
    def test_generate_config_with_env_vars(self, mock_get_server, mock_get_registry, client, mock_registry):
        """Test config generation including environment variables"""
        mock_get_registry.return_value = mock_registry
        mock_get_server.side_effect = lambda server_id: mock_registry.get(server_id)
        
        request_data = {
            "servers": ["github"],
            "format": "mcp",
            "include_env_vars": True
        }
        
        response = client.post("/api/v1/servers/generate-config", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        github_config = data["config"]["mcpServers"]["github"]
        
        # Should include required env vars
        assert "env" in github_config
        assert "GITHUB_TOKEN" in github_config["env"]
        assert github_config["env"]["GITHUB_TOKEN"] == "${GITHUB_TOKEN}"
    
    @patch('api.routers.config.get_server_registry')
    @patch('api.routers.config.get_server_by_id')
    def test_generate_config_docker_format(self, mock_get_server, mock_get_registry, client, mock_registry):
        """Test config generation with Docker format"""
        mock_get_registry.return_value = mock_registry
        mock_get_server.side_effect = lambda server_id: mock_registry.get(server_id)
        
        request_data = {
            "servers": ["github"],
            "format": "docker",
            "include_env_vars": False
        }
        
        response = client.post("/api/v1/servers/generate-config", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        github_config = data["config"]["mcpServers"]["github"]
        
        # Should use Docker command when format is docker
        assert github_config["command"] == "docker"
        assert "run" in github_config["args"]
        assert "-i" in github_config["args"]
        assert "--rm" in github_config["args"]
        assert "mcp/github" in github_config["args"]
    
    @patch('api.routers.config.get_server_registry')
    @patch('api.routers.config.get_server_by_id')
    def test_generate_config_multiple_servers(self, mock_get_server, mock_get_registry, client, mock_registry):
        """Test config generation for multiple servers"""
        mock_get_registry.return_value = mock_registry
        mock_get_server.side_effect = lambda server_id: mock_registry.get(server_id)
        
        request_data = {
            "servers": ["github", "filesystem"],
            "format": "mcp",
            "include_env_vars": True
        }
        
        response = client.post("/api/v1/servers/generate-config", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        config = data["config"]["mcpServers"]
        
        # Should include both servers
        assert "github" in config
        assert "filesystem" in config
        
        # GitHub should have npx command
        assert config["github"]["command"] == "npx"
        
        # Filesystem should have python command
        assert config["filesystem"]["command"] == "python"
        assert "-m" in config["filesystem"]["args"]
        assert "filesystem_server" in config["filesystem"]["args"]
    
    def test_generate_config_no_servers(self, client):
        """Test config generation with no servers specified"""
        request_data = {
            "servers": [],
            "format": "mcp",
            "include_env_vars": False
        }
        
        response = client.post("/api/v1/servers/generate-config", json=request_data)
        assert response.status_code == 400
        assert "no servers specified" in response.json()["detail"].lower()
    
    @patch('api.routers.config.get_server_registry')
    @patch('api.routers.config.get_server_by_id')
    def test_generate_config_unknown_server(self, mock_get_server, mock_get_registry, client, mock_registry):
        """Test config generation with unknown server (should skip)"""
        mock_get_registry.return_value = mock_registry
        mock_get_server.side_effect = lambda server_id: mock_registry.get(server_id)
        
        request_data = {
            "servers": ["github", "nonexistent"],
            "format": "mcp",
            "include_env_vars": False
        }
        
        response = client.post("/api/v1/servers/generate-config", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        config = data["config"]["mcpServers"]
        
        # Should only include known server
        assert "github" in config
        assert "nonexistent" not in config
        assert data["servers_included"] == ["github", "nonexistent"]  # Original request preserved

class TestConfigValidation:
    """Test configuration validation endpoints"""
    
    def test_validate_valid_config(self, client):
        """Test validation of a valid configuration"""
        config_data = {
            "config": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {
                    "GITHUB_TOKEN": "ghp_example"
                }
            }
        }
        
        response = client.post("/api/v1/servers/validate-config", json=config_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["valid"] is True
        assert len(data["errors"]) == 0
        assert data["config"] == config_data["config"]
    
    def test_validate_config_missing_command(self, client):
        """Test validation with missing command field"""
        config_data = {
            "config": {
                "args": ["-y", "@modelcontextprotocol/server-github"]
            }
        }
        
        response = client.post("/api/v1/servers/validate-config", json=config_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0
        assert any("command" in error.lower() for error in data["errors"])
    
    def test_validate_config_unusual_command(self, client):
        """Test validation with unusual command (should warn)"""
        config_data = {
            "config": {
                "command": "some-custom-command",
                "args": ["--option", "value"]
            }
        }
        
        response = client.post("/api/v1/servers/validate-config", json=config_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["valid"] is True  # Valid but has warnings
        assert len(data["warnings"]) > 0
        assert any("unusual command" in warning.lower() for warning in data["warnings"])
    
    def test_validate_config_invalid_args_type(self, client):
        """Test validation with invalid args type"""
        config_data = {
            "config": {
                "command": "npx",
                "args": "not-an-array"
            }
        }
        
        response = client.post("/api/v1/servers/validate-config", json=config_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["valid"] is False
        assert any("args" in error.lower() and "array" in error.lower() for error in data["errors"])
    
    def test_validate_config_invalid_env_type(self, client):
        """Test validation with invalid env type"""
        config_data = {
            "config": {
                "command": "npx",
                "env": "not-an-object"
            }
        }
        
        response = client.post("/api/v1/servers/validate-config", json=config_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["valid"] is False
        assert any("env" in error.lower() and "object" in error.lower() for error in data["errors"])
    
    def test_validate_config_non_string_env_values(self, client):
        """Test validation with non-string environment values"""
        config_data = {
            "config": {
                "command": "python",
                "env": {
                    "PORT": 8080,  # Number instead of string
                    "DEBUG": True  # Boolean instead of string
                }
            }
        }
        
        response = client.post("/api/v1/servers/validate-config", json=config_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["valid"] is True  # Valid but has warnings
        assert len(data["warnings"]) >= 2  # Should warn about both non-string values