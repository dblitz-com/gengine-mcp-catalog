#!/usr/bin/env python3
"""
Test configuration endpoints (/api/v1/servers/generate-config and /api/v1/servers/validate-config)
"""

import pytest
from unittest.mock import patch
from httpx import AsyncClient

from api.models.servers import ConfigGenerationRequest, ConfigValidationRequest


@pytest.mark.asyncio
class TestConfigEndpoints:
    """Test configuration generation and validation endpoints"""
    
    @pytest.fixture
    def mock_registry(self):
        """Mock server registry with test servers"""
        return {
            "github": {
                "id": "github",
                "name": "GitHub MCP",
                "description": "GitHub operations",
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
                }
            },
            "filesystem": {
                "id": "filesystem",
                "name": "Filesystem MCP",
                "description": "File operations",
                "installation": {
                    "docker": {
                        "image": "mcp/filesystem:latest"
                    }
                },
                "config": {
                    "env": {}
                }
            },
            "weather": {
                "id": "weather",
                "name": "Weather API",
                "description": "Weather data",
                # No installation config - should default to NPX
            }
        }
    
    @pytest.mark.asyncio
    async def test_generate_config_success(self, client: AsyncClient, mock_registry):
        """Test successful configuration generation"""
        with patch("api.routers.config.get_server_registry", return_value=mock_registry), \
             patch("api.routers.config.get_server_by_id", side_effect=lambda x: mock_registry.get(x)):
            
            # Test basic config generation
            response = await client.post("/api/v1/servers/generate-config", json={
                "servers": ["github", "filesystem"],
                "format": "claude_desktop",
                "include_env_vars": True
            })
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["format"] == "claude_desktop"
            assert "config" in data
            assert "mcpServers" in data["config"]
            assert len(data["servers_included"]) == 2
            assert "github" in data["config"]["mcpServers"]
            assert "filesystem" in data["config"]["mcpServers"]
            
            # Check GitHub config
            github_config = data["config"]["mcpServers"]["github"]
            assert github_config["command"] == "npx"
            assert github_config["args"] == ["-y", "@modelcontextprotocol/server-github"]
            assert "env" in github_config
            assert "GITHUB_PERSONAL_ACCESS_TOKEN" in github_config["env"]
    
    @pytest.mark.asyncio
    async def test_generate_config_docker_format(self, client: AsyncClient, mock_registry):
        """Test Docker format configuration generation"""
        with patch("api.routers.config.get_server_registry", return_value=mock_registry), \
             patch("api.routers.config.get_server_by_id", side_effect=lambda x: mock_registry.get(x)):
            
            response = await client.post("/api/v1/servers/generate-config", json={
                "servers": ["filesystem"],
                "format": "docker",
                "include_env_vars": False
            })
            
            assert response.status_code == 200
            data = response.json()
            
            filesystem_config = data["config"]["mcpServers"]["filesystem"]
            assert filesystem_config["command"] == "docker"
            assert "run" in filesystem_config["args"]
            assert "mcp/filesystem" in filesystem_config["args"]
    
    @pytest.mark.asyncio
    async def test_generate_config_default_npx(self, client: AsyncClient, mock_registry):
        """Test default NPX configuration for servers without installation config"""
        with patch("api.routers.config.get_server_registry", return_value=mock_registry), \
             patch("api.routers.config.get_server_by_id", side_effect=lambda x: mock_registry.get(x)):
            
            response = await client.post("/api/v1/servers/generate-config", json={
                "servers": ["weather"],
                "format": "claude_desktop",
                "include_env_vars": False
            })
            
            assert response.status_code == 200
            data = response.json()
            
            weather_config = data["config"]["mcpServers"]["weather"]
            assert weather_config["command"] == "npx"
            assert weather_config["args"] == ["-y", "@modelcontextprotocol/server-weather"]
    
    @pytest.mark.asyncio
    async def test_generate_config_no_servers(self, client: AsyncClient):
        """Test config generation with empty server list"""
        response = await client.post("/api/v1/servers/generate-config", json={
            "servers": [],
            "format": "claude_desktop"
        })
        
        assert response.status_code == 400
        assert "No servers specified" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_generate_config_unknown_servers(self, client: AsyncClient, mock_registry):
        """Test config generation with unknown servers (should skip them)"""
        with patch("api.routers.config.get_server_registry", return_value=mock_registry), \
             patch("api.routers.config.get_server_by_id", side_effect=lambda x: mock_registry.get(x)):
            
            response = await client.post("/api/v1/servers/generate-config", json={
                "servers": ["github", "unknown-server", "filesystem"],
                "format": "claude_desktop",
                "include_env_vars": False
            })
            
            assert response.status_code == 200
            data = response.json()
            
            # Should only include known servers
            assert len(data["config"]["mcpServers"]) == 2
            assert "github" in data["config"]["mcpServers"]
            assert "filesystem" in data["config"]["mcpServers"]
            assert "unknown-server" not in data["config"]["mcpServers"]
    
    @pytest.mark.asyncio
    async def test_validate_config_valid(self, client: AsyncClient):
        """Test validation of valid configuration"""
        valid_config = {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {
                "GITHUB_PERSONAL_ACCESS_TOKEN": "token_value"
            }
        }
        
        response = await client.post("/api/v1/servers/validate-config", json={
            "config": valid_config
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is True
        assert len(data["errors"]) == 0
        assert data["config"] == valid_config
    
    @pytest.mark.asyncio
    async def test_validate_config_missing_command(self, client: AsyncClient):
        """Test validation with missing command field"""
        invalid_config = {
            "args": ["-y", "some-package"],
            "env": {}
        }
        
        response = await client.post("/api/v1/servers/validate-config", json={
            "config": invalid_config
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is False
        assert "Missing required field: 'command'" in data["errors"]
    
    @pytest.mark.asyncio
    async def test_validate_config_unusual_command(self, client: AsyncClient):
        """Test validation with unusual command (should generate warning)"""
        config_with_unusual_command = {
            "command": "unusual-command",
            "args": ["some", "args"]
        }
        
        response = await client.post("/api/v1/servers/validate-config", json={
            "config": config_with_unusual_command
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is True  # Still valid, just has warnings
        assert len(data["errors"]) == 0
        assert "Unusual command: 'unusual-command'" in data["warnings"]
    
    @pytest.mark.asyncio
    async def test_validate_config_invalid_args(self, client: AsyncClient):
        """Test validation with invalid args type"""
        invalid_config = {
            "command": "npx",
            "args": "should-be-array-not-string"
        }
        
        response = await client.post("/api/v1/servers/validate-config", json={
            "config": invalid_config
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is False
        assert "Field 'args' must be an array" in data["errors"]
    
    @pytest.mark.asyncio
    async def test_validate_config_invalid_env_type(self, client: AsyncClient):
        """Test validation with invalid env type"""
        invalid_config = {
            "command": "npx",
            "env": "should-be-object-not-string"
        }
        
        response = await client.post("/api/v1/servers/validate-config", json={
            "config": invalid_config
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is False
        assert "Field 'env' must be an object" in data["errors"]
    
    @pytest.mark.asyncio
    async def test_validate_config_invalid_env_keys(self, client: AsyncClient):
        """Test validation with invalid environment variable keys"""
        invalid_config = {
            "command": "npx",
            "env": {
                "VALID_KEY": 456  # Invalid value type, but valid key type
            }
        }
        
        response = await client.post("/api/v1/servers/validate-config", json={
            "config": invalid_config
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is True  # No errors, just warnings
        assert len(data["errors"]) == 0
        assert any("Environment variable 'VALID_KEY' value should be string" in warning for warning in data["warnings"])