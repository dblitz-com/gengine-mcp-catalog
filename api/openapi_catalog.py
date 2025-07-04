#!/usr/bin/env python3
"""
OpenAPI Catalog Server - OpenAPI Discovery and Management

A simple server that provides OpenAPI spec discovery, cataloging,
and conversion capabilities without any MCP dependencies.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import httpx
from flask import Flask, jsonify, request

app = Flask(__name__)

# OpenAPI registry - loaded from openapi_specs.json
_openapi_registry: Dict[str, Any] = {}

def load_openapi_registry():
    """Load the known OpenAPI specs registry"""
    global _openapi_registry
    
    # Look for openapi_specs.json in current directory
    registry_path = Path(__file__).parent / "openapi_specs.json"
    if registry_path.exists():
        with open(registry_path, 'r') as f:
            _openapi_registry = json.load(f)
        print(f"📚 Loaded {len(_openapi_registry)} OpenAPI specs from {registry_path}")
    else:
        # Create sample registry
        _openapi_registry = {
            "petstore": {
                "name": "Petstore API",
                "description": "Sample Pet Store API",
                "openapi_url": "https://petstore3.swagger.io/api/v3/openapi.json",
                "base_url": "https://petstore3.swagger.io/api/v3",
                "category": "demo",
                "auth": {
                    "type": "api_key",
                    "header": "api_key"
                }
            },
            "github": {
                "name": "GitHub API",
                "description": "GitHub REST API v3",
                "openapi_url": "https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.json",
                "base_url": "https://api.github.com",
                "category": "developer-tools",
                "auth": {
                    "type": "bearer",
                    "header": "Authorization"
                }
            }
        }
        # Save the sample registry
        with open(registry_path, 'w') as f:
            json.dump(_openapi_registry, f, indent=2)
        print(f"📝 Created sample registry with {len(_openapi_registry)} specs")

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "spec_count": len(_openapi_registry),
        "catalog_version": "1.0.0",
        "type": "openapi-catalog"
    })

@app.route('/specs', methods=['GET'])
def list_specs():
    """List all available OpenAPI specs"""
    return jsonify({
        "specs": [
            {
                "id": spec_id,
                "name": spec_config.get("name", spec_id),
                "description": spec_config.get("description", ""),
                "category": spec_config.get("category", "other"),
                "openapi_url": spec_config.get("openapi_url", ""),
                "base_url": spec_config.get("base_url", "")
            }
            for spec_id, spec_config in _openapi_registry.items()
        ]
    })

@app.route('/specs/<spec_id>', methods=['GET'])
def get_spec_info(spec_id):
    """Get detailed information about a specific OpenAPI spec"""
    if spec_id not in _openapi_registry:
        return jsonify({"error": f"Spec '{spec_id}' not found"}), 404
    
    spec_config = _openapi_registry[spec_id]
    
    # Try to fetch the actual OpenAPI spec
    openapi_spec = None
    if "openapi_url" in spec_config:
        try:
            response = httpx.get(spec_config["openapi_url"], timeout=10.0)
            if response.status_code == 200:
                openapi_spec = response.json()
        except Exception as e:
            print(f"⚠️  Failed to fetch OpenAPI spec: {e}")
    
    return jsonify({
        "id": spec_id,
        "config": spec_config,
        "openapi_spec": openapi_spec
    })

@app.route('/specs/<spec_id>/generate', methods=['POST'])
def generate_server_code(spec_id):
    """Generate server code from OpenAPI spec"""
    if spec_id not in _openapi_registry:
        return jsonify({"error": f"Spec '{spec_id}' not found"}), 404
    
    spec_config = _openapi_registry[spec_id]
    
    # Get generation options from request
    options = request.json or {}
    server_type = options.get("type", "fastmcp")  # Default to FastMCP
    
    if server_type == "fastmcp":
        # Generate FastMCP server code
        code = generate_fastmcp_code(spec_id, spec_config, options)
    else:
        return jsonify({"error": f"Unknown server type: {server_type}"}), 400
    
    return jsonify({
        "spec_id": spec_id,
        "server_type": server_type,
        "code": code,
        "filename": f"{spec_id}_server.py"
    })

def generate_fastmcp_code(spec_id: str, spec_config: Dict[str, Any], options: Dict[str, Any]) -> str:
    """Generate FastMCP server code from OpenAPI spec"""
    auth_setup = ""
    if "auth" in spec_config:
        auth_type = spec_config["auth"]["type"]
        if auth_type == "bearer":
            auth_setup = '''    headers={"Authorization": f"Bearer {os.getenv('API_TOKEN')}"}'''
        elif auth_type == "api_key":
            header = spec_config["auth"].get("header", "X-API-Key")
            auth_setup = f'''    headers={{"{header}": os.getenv('API_KEY')}}'''
    
    route_maps = options.get("route_maps", "")
    if not route_maps:
        # Default semantic mapping
        route_maps = """    route_maps=[
        # GET requests with path parameters become ResourceTemplates
        RouteMap(methods=["GET"], pattern=r".*\\{.*\\}.*", mcp_type=MCPType.RESOURCE_TEMPLATE),
        # All other GET requests become Resources
        RouteMap(methods=["GET"], pattern=r".*", mcp_type=MCPType.RESOURCE),
        # Everything else becomes Tools
    ],"""
    
    code = f'''#!/usr/bin/env python3
"""
FastMCP server generated from {spec_config.get("name", spec_id)} OpenAPI spec
Generated by OpenAPI Catalog
"""

import os
import httpx
from fastmcp import FastMCP
from fastmcp.server.openapi import RouteMap, MCPType

# Create HTTP client
client = httpx.AsyncClient(
    base_url="{spec_config.get('base_url', 'https://api.example.com')}",
{auth_setup}
)

# Load OpenAPI spec
openapi_spec = httpx.get("{spec_config.get('openapi_url', '')}").json()

# Create FastMCP server from OpenAPI
mcp = FastMCP.from_openapi(
    openapi_spec=openapi_spec,
    client=client,
    name="{spec_config.get('name', spec_id)} MCP Server",
{route_maps}
)

if __name__ == "__main__":
    import sys
    if "--http" in sys.argv:
        mcp.run(transport="http", port=8000)
    else:
        mcp.run(transport="stdio")
'''
    
    return code

@app.route('/search', methods=['GET'])
def search_specs():
    """Search OpenAPI specs by query"""
    query = request.args.get('q', '').lower()
    category = request.args.get('category')
    
    results = []
    for spec_id, spec_config in _openapi_registry.items():
        # Check if matches query
        matches_query = (
            query in spec_id.lower() or
            query in spec_config.get("name", "").lower() or
            query in spec_config.get("description", "").lower()
        )
        
        # Check category filter
        matches_category = (
            category is None or 
            spec_config.get("category", "other") == category
        )
        
        if matches_query and matches_category:
            results.append({
                "id": spec_id,
                "name": spec_config.get("name", spec_id),
                "description": spec_config.get("description", ""),
                "category": spec_config.get("category", "other"),
                "openapi_url": spec_config.get("openapi_url", "")
            })
    
    return jsonify({"results": results})

# Load registry on startup
load_openapi_registry()

if __name__ == "__main__":
    import sys
    
    print(f"🚀 Starting OpenAPI Catalog server with {len(_openapi_registry)} specs")
    
    if "--production" in sys.argv:
        # Production mode with Gunicorn would be configured here
        app.run(host="0.0.0.0", port=8000)
    else:
        # Development mode
        app.run(debug=True, port=8000)