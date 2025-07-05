#!/usr/bin/env python3
"""
Pydantic models for MCP server catalog endpoints
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class ServerSummary(BaseModel):
    """Summary information for a server in listings"""
    id: str = Field(..., description="Unique server identifier")
    name: str = Field(..., description="Display name of the server")
    description: str = Field("", description="Brief description of server functionality")
    category: str = Field("other", description="Server category")
    homepage: str = Field("", description="Server homepage URL")
    vendor: str = Field("community", description="Server vendor/maintainer")

class ServerInstallation(BaseModel):
    """Server installation configuration"""
    command: Dict[str, Any] = Field(default_factory=dict, description="Installation command configuration")
    docker: Optional[str] = Field(None, description="Docker image for installation")
    npm: Optional[str] = Field(None, description="NPM package name")
    pip: Optional[str] = Field(None, description="Python package name")

class ServerConfig(BaseModel):
    """Server configuration options"""
    env: Dict[str, Any] = Field(default_factory=dict, description="Environment variables")
    args: List[str] = Field(default_factory=list, description="Command arguments")

class ServerCapabilities(BaseModel):
    """Server capabilities"""
    tools: Optional[bool] = Field(None, description="Supports tools")
    resources: Optional[bool] = Field(None, description="Supports resources")  
    prompts: Optional[bool] = Field(None, description="Supports prompts")

class ServerDetails(ServerSummary):
    """Detailed server information"""
    license: str = Field("Unknown", description="Software license")
    installation: ServerInstallation = Field(default_factory=ServerInstallation, description="Installation options")
    config: ServerConfig = Field(default_factory=ServerConfig, description="Configuration options")
    features: List[str] = Field(default_factory=list, description="Server features")
    supported_platforms: List[str] = Field(default_factory=lambda: ["all"], description="Supported platforms")
    capabilities: Optional[ServerCapabilities] = Field(None, description="Server capabilities")

class ServerListResponse(BaseModel):
    """Response for listing servers"""
    servers: List[ServerSummary] = Field(..., description="List of available servers")
    total: int = Field(..., description="Total number of servers")

class SearchResponse(BaseModel):
    """Response for server search"""
    results: List[ServerSummary] = Field(..., description="Search results")
    total: int = Field(..., description="Total number of results")
    query: Optional[str] = Field(None, description="Search query used")
    category: Optional[str] = Field(None, description="Category filter applied")

class ConfigGenerationRequest(BaseModel):
    """Request for generating MCP configuration"""
    servers: List[str] = Field(..., description="List of server IDs to include in configuration")
    format: str = Field("claude_desktop", description="Configuration format")
    include_env_vars: bool = Field(True, description="Include environment variables in configuration")

class MCPServerConfig(BaseModel):
    """MCP server configuration block"""
    command: str = Field(..., description="Command to run the server")
    args: List[str] = Field(default_factory=list, description="Command arguments")
    env: Optional[Dict[str, str]] = Field(None, description="Environment variables")

class ConfigGenerationResponse(BaseModel):
    """Response for configuration generation"""
    format: str = Field(..., description="Configuration format used")
    config: Dict[str, Dict[str, MCPServerConfig]] = Field(..., description="Generated configuration")
    servers_included: List[str] = Field(..., description="List of servers included")
    installation_notes: str = Field(..., description="Installation instructions")

class ConfigValidationRequest(BaseModel):
    """Request for validating configuration"""
    config: Dict[str, Any] = Field(..., description="Configuration to validate")

class ConfigValidationResponse(BaseModel):
    """Response for configuration validation"""
    valid: bool = Field(..., description="Whether configuration is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    config: Dict[str, Any] = Field(..., description="Validated configuration")

class CategoryInfo(BaseModel):
    """Category information"""
    name: str = Field(..., description="Category name")
    count: int = Field(..., description="Number of servers in category")

class CategoriesResponse(BaseModel):
    """Response for listing categories"""
    categories: List[CategoryInfo] = Field(..., description="Available categories")


class ServerTool(BaseModel):
    """Information about a server tool"""
    name: str = Field(..., description="Tool name")
    description: Optional[str] = Field(None, description="Tool description")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Tool parameters schema")


class ServerWithTools(BaseModel):
    """Server information with available tools"""
    id: str = Field(..., description="Server ID")
    name: str = Field(..., description="Server name")
    description: str = Field(..., description="Server description")
    tools: List[ServerTool] = Field(default_factory=list, description="Available tools")
    tool_count: int = Field(0, description="Number of tools")


class ServersToolsResponse(BaseModel):
    """Response for servers with tools endpoint"""
    servers: List[ServerWithTools] = Field(..., description="Servers with their tools")
    total_servers: int = Field(..., description="Total number of servers")
    total_tools: int = Field(..., description="Total number of tools across all servers")