#!/usr/bin/env python3
"""
FastAPI router for server management endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import sys
from pathlib import Path

from ..models.servers import (
    ServerListResponse, ServerDetails, SearchResponse, 
    CategoriesResponse, CategoryInfo, ServerSummary,
    ServersToolsResponse, ServerWithTools, ServerTool
)
from ..dependencies import get_server_registry, get_server_by_id

# Add engine root directory to path to import subprocess_manager
engine_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(engine_root))

try:
    from subprocess_manager import get_subprocess_manager
except ImportError:
    # For testing or when subprocess_manager isn't available
    def get_subprocess_manager():
        from unittest.mock import MagicMock, AsyncMock
        mock = MagicMock()
        mock.processes = {}
        mock.cleanup = AsyncMock()
        mock.start_server = AsyncMock(return_value=False)
        mock.list_tools = AsyncMock(return_value={"tools": []})
        return mock

router = APIRouter()

@router.get("/servers", response_model=ServerListResponse)
async def list_available_servers():
    """List all available MCP servers"""
    registry = get_server_registry()
    
    servers = []
    for server_id, server_config in registry.items():
        servers.append(ServerSummary(
            id=server_id,
            name=server_config.get("name", server_id),
            description=server_config.get("description", ""),
            category=server_config.get("category", "other"),
            homepage=server_config.get("homepage", ""),
            vendor=server_config.get("vendor", "community")
        ))
    
    return ServerListResponse(
        servers=servers,
        total=len(servers)
    )

@router.get("/servers/search", response_model=SearchResponse)
async def search_servers(
    q: Optional[str] = Query(None, description="Search query"),
    category: Optional[str] = Query(None, description="Category filter")
):
    """Search MCP servers by query and/or category"""
    if not q and not category:
        raise HTTPException(status_code=400, detail="Query parameter 'q' or 'category' required")
    
    registry = get_server_registry()
    results = []
    
    for server_id, server_config in registry.items():
        # Check if matches query
        matches_query = True
        if q:
            q_lower = q.lower()
            matches_query = (
                q_lower in server_id.lower() or
                q_lower in server_config.get("name", "").lower() or
                q_lower in server_config.get("description", "").lower()
            )
        
        # Check category filter
        matches_category = (
            category is None or 
            server_config.get("category", "other") == category
        )
        
        if matches_query and matches_category:
            results.append(ServerSummary(
                id=server_id,
                name=server_config.get("name", server_id),
                description=server_config.get("description", ""),
                category=server_config.get("category", "other"),
                vendor=server_config.get("vendor", "community")
            ))
    
    return SearchResponse(
        results=results,
        total=len(results),
        query=q,
        category=category
    )

@router.get("/servers/tools", response_model=ServersToolsResponse)
async def get_servers_with_tools():
    """Get all servers with their available tools by dynamically querying each MCP server"""
    import httpx
    import asyncio
    import os
    
    registry = get_server_registry()
    servers_with_tools = []
    total_tools = 0
    
    # Get subprocess manager for stdio servers
    subprocess_manager = get_subprocess_manager()
    
    async def query_http_server_tools(server_id: str, server_config: dict, mcp_url: str):
        """Query an HTTP/SSE MCP server for its available tools"""
        tools = []
        
        try:
            async with httpx.AsyncClient() as client:
                # Standard MCP tools listing endpoint
                response = await client.post(
                    f"{mcp_url}/mcp/v1/list_tools",
                    json={},
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    for tool in result.get("tools", []):
                        tools.append(ServerTool(
                            name=tool.get("name", ""),
                            description=tool.get("description", ""),
                            parameters=tool.get("inputSchema", {})
                        ))
        except Exception as e:
            print(f"Could not query HTTP tools for {server_id}: {e}")
            
        return tools
    
    async def query_stdio_server_tools(server_id: str, server_config: dict):
        """Query a stdio-based MCP server for its available tools"""
        tools = []
        
        try:
            # Check if server has required environment variables
            env_vars = server_config.get("environment", {})
            missing_vars = []
            
            for var_name, var_config in env_vars.items():
                if var_config.get("required", False) and not os.getenv(var_name):
                    missing_vars.append(var_name)
            
            if missing_vars:
                print(f"Server {server_id} missing required env vars: {missing_vars}")
                return tools
            
            # Start server if not running
            if server_id not in subprocess_manager.processes:
                print(f"Starting stdio server {server_id}...")
                started = await subprocess_manager.start_server(server_id, server_config)
                if not started:
                    print(f"Failed to start server {server_id}")
                    return tools
                # Give server time to initialize
                await asyncio.sleep(2.0)
            
            # Query tools via subprocess
            tools_response = await subprocess_manager.list_tools(server_id)
            
            if tools_response and "error" not in tools_response:
                for tool in tools_response.get("tools", []):
                    tools.append(ServerTool(
                        name=tool.get("name", ""),
                        description=tool.get("description", ""),
                        parameters=tool.get("inputSchema", {})
                    ))
            else:
                error = tools_response.get("error", "Unknown error") if tools_response else "No response"
                print(f"Error getting tools from {server_id}: {error}")
                    
        except Exception as e:
            print(f"Could not query stdio tools for {server_id}: {e}")
            
        return tools
    
    async def query_mcp_server_tools(server_id: str, server_config: dict):
        """Query an MCP server for its available tools based on transport type"""
        
        # Check for explicit MCP endpoint (HTTP/SSE/WebSocket)
        mcp_url = server_config.get("mcp_endpoint")
        transport = server_config.get("transport", "stdio")
        
        if mcp_url:
            # HTTP, SSE, or WebSocket server
            if mcp_url.startswith(("http://", "https://", "ws://", "wss://")):
                if mcp_url.startswith("ws"):
                    # WebSocket not implemented yet
                    print(f"WebSocket transport not implemented for {server_id}")
                    return []
                else:
                    # HTTP or SSE
                    return await query_http_server_tools(server_id, server_config, mcp_url)
        
        # Check for execution configuration (stdio servers)
        if "execution" in server_config or transport == "stdio":
            return await query_stdio_server_tools(server_id, server_config)
        
        # Unknown transport type
        print(f"Unknown transport type for {server_id}: {transport}")
        return []
    
    # Query all servers in parallel
    tasks = []
    for server_id, server_config in registry.items():
        task = query_mcp_server_tools(server_id, server_config)
        tasks.append((server_id, server_config, task))
    
    # Gather results
    for server_id, server_config, task in tasks:
        tools = await task
        tool_count = len(tools)
        total_tools += tool_count
        
        servers_with_tools.append(ServerWithTools(
            id=server_id,
            name=server_config.get("name", server_id),
            description=server_config.get("description", ""),
            tools=tools,
            tool_count=tool_count
        ))
    
    # Clean up subprocess manager
    await subprocess_manager.cleanup()
    
    return ServersToolsResponse(
        servers=servers_with_tools,
        total_servers=len(servers_with_tools),
        total_tools=total_tools
    )

@router.get("/servers/{server_id}", response_model=ServerDetails)
async def get_server_info(server_id: str):
    """Get detailed information about a specific MCP server"""
    server_config = get_server_by_id(server_id)
    
    if not server_config:
        raise HTTPException(status_code=404, detail=f"Server '{server_id}' not found")
    
    # Build detailed response
    server_details = ServerDetails(
        id=server_id,
        name=server_config.get("name", server_id),
        description=server_config.get("description", ""),
        category=server_config.get("category", "other"),
        vendor=server_config.get("vendor", "community"),
        homepage=server_config.get("homepage", ""),
        license=server_config.get("license", "Unknown"),
        installation=server_config.get("installation", {}),
        config=server_config.get("config", {}),
        features=server_config.get("features", []),
        supported_platforms=server_config.get("supported_platforms", ["all"])
    )
    
    # Add capabilities if available
    if "capabilities" in server_config:
        server_details.capabilities = server_config["capabilities"]
    
    return server_details

@router.get("/categories", response_model=CategoriesResponse)
async def list_categories():
    """List all available server categories"""
    registry = get_server_registry()
    categories = {}
    
    for server_config in registry.values():
        category = server_config.get("category", "other")
        if category not in categories:
            categories[category] = 0
        categories[category] += 1
    
    category_list = [
        CategoryInfo(name=cat, count=count)
        for cat, count in sorted(categories.items())
    ]
    
    return CategoriesResponse(categories=category_list)