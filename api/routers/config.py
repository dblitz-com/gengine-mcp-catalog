#!/usr/bin/env python3
"""
FastAPI router for configuration management endpoints
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List

from ..models.servers import (
    ConfigGenerationRequest, ConfigGenerationResponse, 
    ConfigValidationRequest, ConfigValidationResponse,
    MCPServerConfig
)
from ..dependencies import get_server_registry, get_server_by_id

router = APIRouter()

@router.post("/servers/generate-config", response_model=ConfigGenerationResponse)
async def generate_mcp_config(request: ConfigGenerationRequest):
    """Generate MCP configuration for specified servers"""
    registry = get_server_registry()
    
    if not request.servers:
        raise HTTPException(status_code=400, detail="No servers specified")
    
    # Generate configuration
    config = {"mcpServers": {}}
    
    for server_id in request.servers:
        server_config = get_server_by_id(server_id)
        if not server_config:
            continue  # Skip unknown servers
        
        # Get installation command based on format
        installation = server_config.get("installation", {})
        if request.format == "docker" and "docker" in installation:
            mcp_config = MCPServerConfig(
                command="docker",
                args=["run", "-i", "--rm", f"mcp/{server_id}"]
            )
        elif "command" in installation:
            command_info = installation["command"]
            mcp_config = MCPServerConfig(
                command=command_info["command"],
                args=command_info.get("args", [])
            )
        else:
            # Default NPX installation
            mcp_config = MCPServerConfig(
                command="npx",
                args=["-y", f"@modelcontextprotocol/server-{server_id}"]
            )
        
        # Add environment variables if requested
        if request.include_env_vars and "env" in server_config.get("config", {}):
            env_config = {}
            for env_var, env_config_item in server_config["config"]["env"].items():
                if env_config_item.get("required"):
                    env_config[env_var] = f"${{{env_var}}}"
            if env_config:
                mcp_config.env = env_config
        
        config["mcpServers"][server_id] = mcp_config.model_dump(exclude_none=True)
    
    return ConfigGenerationResponse(
        format=request.format,
        config=config,
        servers_included=request.servers,
        installation_notes=f"Add this to your {request.format} configuration file"
    )

@router.post("/servers/validate-config", response_model=ConfigValidationResponse)
async def validate_server_config(request: ConfigValidationRequest):
    """Validate an MCP server configuration"""
    config = request.config
    
    # Basic validation
    errors = []
    warnings = []
    
    # Check for required fields
    if "command" not in config:
        errors.append("Missing required field: 'command'")
    
    # Check command type
    command = config.get("command", "")
    if command not in ["npx", "node", "python", "docker", "deno", "bun"]:
        warnings.append(f"Unusual command: '{command}'")
    
    # Check args
    if "args" in config and not isinstance(config["args"], list):
        errors.append("Field 'args' must be an array")
    
    # Check env
    if "env" in config:
        if not isinstance(config["env"], dict):
            errors.append("Field 'env' must be an object")
        else:
            for key, value in config["env"].items():
                if not isinstance(key, str):
                    errors.append(f"Environment variable key must be string: {key}")
                if not isinstance(value, str):
                    warnings.append(f"Environment variable '{key}' value should be string")
    
    is_valid = len(errors) == 0
    
    return ConfigValidationResponse(
        valid=is_valid,
        errors=errors,
        warnings=warnings,
        config=config
    )