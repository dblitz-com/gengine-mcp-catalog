#!/usr/bin/env python3
"""
FastMCP server for MCP Catalog - Generated from OpenAPI spec
This provides MCP protocol access to the MCP Catalog REST API
"""

import os
import httpx
from fastmcp import FastMCP
from fastmcp.server.openapi import RouteMap, MCPType

# Create HTTP client for the REST API
client = httpx.AsyncClient(
    base_url=os.getenv("MCP_CATALOG_API_URL", "http://localhost:8000"),
    timeout=30.0
)

# Fetch OpenAPI spec
response = httpx.get(f"{client.base_url}/openapi.json")
openapi_spec = response.json()

# Create FastMCP server from OpenAPI
mcp = FastMCP.from_openapi(
    openapi_spec=openapi_spec,
    client=client,
    name="MCP Catalog",
    instructions="""
    MCP Catalog - Configuration Oracle
    
    This server provides access to the MCP server catalog through the MCP protocol.
    Use it to discover, configure, and validate MCP servers for your projects.
    
    Available operations:
    - List all available MCP servers
    - Get detailed information about specific servers
    - Search servers by name or category
    - Generate MCP configurations for Claude Desktop or other clients
    - Validate MCP server configurations
    """,
    route_maps=[
        # GET endpoints that list data become Resources
        RouteMap(
            methods=["GET"], 
            pattern=r"^/api/v1/servers$", 
            mcp_type=MCPType.RESOURCE,
            mcp_tags={"catalog", "list"}
        ),
        RouteMap(
            methods=["GET"], 
            pattern=r"^/api/v1/categories$", 
            mcp_type=MCPType.RESOURCE,
            mcp_tags={"catalog", "metadata"}
        ),
        
        # GET endpoints with parameters become ResourceTemplates
        RouteMap(
            methods=["GET"], 
            pattern=r".*\{.*\}.*", 
            mcp_type=MCPType.RESOURCE_TEMPLATE,
            mcp_tags={"catalog", "detail"}
        ),
        
        # Search endpoint becomes a Tool (it has query params)
        RouteMap(
            methods=["GET"],
            pattern=r"^/api/v1/servers/search$",
            mcp_type=MCPType.TOOL,
            mcp_tags={"catalog", "search"}
        ),
        
        # All POST endpoints become Tools
        RouteMap(
            methods=["POST"], 
            pattern=r".*", 
            mcp_type=MCPType.TOOL,
            mcp_tags={"catalog", "action"}
        ),
        
        # Health check is a simple Resource
        RouteMap(
            methods=["GET"],
            pattern=r"^/health$",
            mcp_type=MCPType.RESOURCE,
            mcp_tags={"system", "health"}
        )
    ]
)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP Catalog Server (via FastMCP)")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio",
                       help="Transport protocol (default: stdio)")
    parser.add_argument("--port", type=int, default=8001,
                       help="Port for HTTP transport (default: 8001)")
    
    args = parser.parse_args()
    
    if args.transport == "http":
        print(f"🚀 Starting MCP Catalog server on http://localhost:{args.port}/mcp")
        mcp.run(transport="http", port=args.port)
    else:
        print("📡 Starting MCP Catalog server with stdio transport")
        mcp.run(transport="stdio")
