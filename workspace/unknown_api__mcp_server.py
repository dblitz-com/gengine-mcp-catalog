#!/usr/bin/env python3
"""
FastMCP server generated from captured OpenAPI specification
Source: workspace/captured-openapi.json
API: Untitled service

This MCP server was generated from traffic-captured OpenAPI spec - language agnostic!
"""

import os
import json
import httpx
from fastmcp import FastMCP
from fastmcp.server.openapi import RouteMap, MCPType

# Load the OpenAPI specification
OPENAPI_SPEC_FILE = "workspace/captured-openapi.json"

def load_openapi_spec():
    """Load OpenAPI spec from file or API"""
    if os.path.exists(OPENAPI_SPEC_FILE):
        with open(OPENAPI_SPEC_FILE, 'r') as f:
            return json.load(f)
    else:
        # Fallback to fetching from API
        response = httpx.get("http://localhost:8000/openapi.json")
        return response.json()

# Load OpenAPI spec
openapi_spec = load_openapi_spec()

# Create HTTP client for the REST API
client = httpx.AsyncClient(
    base_url=os.getenv("API_BASE_URL", "http://localhost:8000"),
    timeout=30.0
)

# Create FastMCP server from captured OpenAPI
mcp = FastMCP.from_openapi(
    openapi_spec=openapi_spec,
    client=client,
    name="Generated MCP Server",
    instructions=f"""
    Generated MCP Server from Traffic Capture
    
    Original API: Untitled service
    Generated from: workspace/captured-openapi.json
    
    This server provides MCP protocol access to the captured REST API.
    All functionality is automatically inferred from real traffic patterns.
    
    Language-agnostic generation - works with APIs built in any language!
    """,
    route_maps=[
        # GET endpoints that list data become Resources
        RouteMap(
            methods=["GET"], 
            pattern=r".*/(servers|categories|items|list)$", 
            mcp_type=MCPType.RESOURCE,
            mcp_tags={"catalog", "list"}
        ),
        
        # GET endpoints with path parameters become ResourceTemplates
        RouteMap(
            methods=["GET"], 
            pattern=r".*/{[^}]+}.*", 
            mcp_type=MCPType.RESOURCE_TEMPLATE,
            mcp_tags={"catalog", "detail"}
        ),
        
        # GET endpoints with query parameters become Tools
        RouteMap(
            methods=["GET"],
            pattern=r".*/search.*",
            mcp_type=MCPType.TOOL,
            mcp_tags={"catalog", "search"}
        ),
        
        # All POST/PUT/PATCH/DELETE endpoints become Tools
        RouteMap(
            methods=["POST", "PUT", "PATCH", "DELETE"], 
            pattern=r".*", 
            mcp_type=MCPType.TOOL,
            mcp_tags={"api", "action"}
        ),
        
        # Health checks are Resources
        RouteMap(
            methods=["GET"],
            pattern=r".*/health.*",
            mcp_type=MCPType.RESOURCE,
            mcp_tags={"system", "health"}
        )
    ]
)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generated MCP Server from Traffic Capture")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio",
                       help="Transport protocol (default: stdio)")
    parser.add_argument("--port", type=int, default=8001,
                       help="Port for HTTP transport (default: 8001)")
    
    args = parser.parse_args()
    
    if args.transport == "http":
        print(f"🚀 Starting generated MCP server on http://localhost:{args.port}/mcp")
        print(f"📡 Proxying to API: {client.base_url}")
        mcp.run(transport="http", port=args.port)
    else:
        print("📡 Starting generated MCP server with stdio transport")
        print(f"📡 Proxying to API: {client.base_url}")
        mcp.run(transport="stdio")
