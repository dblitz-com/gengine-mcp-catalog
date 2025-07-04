#!/usr/bin/env python3
"""
Simple Flask REST API for MCP Catalog - Language-agnostic approach

This demonstrates how to build a REST API that can be captured by traffic analysis tools
to generate OpenAPI specs, which can then be converted to MCP servers.

NO OPENAPI ANNOTATIONS NEEDED!
"""

import json
import os
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Load server registry
def load_servers():
    """Load known servers from JSON file"""
    # Look for known_servers.json
    current_dir = Path(__file__).parent
    for search_dir in [current_dir, current_dir.parent.parent / "mcp_catalog"]:
        servers_path = search_dir / "known_servers.json"
        if servers_path.exists():
            with open(servers_path, 'r') as f:
                return json.load(f)
    return {}

servers = load_servers()

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "server_count": len(servers),
        "catalog_version": "2.0.0",
        "api_version": "v1"
    })

@app.route('/api/v1/servers')
def list_servers():
    """List all available MCP servers"""
    result = []
    for server_id, config in servers.items():
        result.append({
            "id": server_id,
            "name": config.get("name", server_id),
            "description": config.get("description", ""),
            "category": config.get("category", "other"),
            "vendor": config.get("vendor", "community"),
            "homepage": config.get("homepage", "")
        })
    return jsonify(result)

@app.route('/api/v1/servers/<server_id>')
def get_server(server_id):
    """Get detailed information about a specific server"""
    if server_id not in servers:
        return jsonify({"error": f"Server '{server_id}' not found"}), 404
    
    config = servers[server_id]
    return jsonify({
        "id": server_id,
        "name": config.get("name", server_id),
        "description": config.get("description", ""),
        "category": config.get("category", "other"),
        "vendor": config.get("vendor", "community"),
        "homepage": config.get("homepage", ""),
        "license": config.get("license", "Unknown"),
        "installation": config.get("installation", {}),
        "config": config.get("config", {}),
        "features": config.get("features", []),
        "supported_platforms": config.get("supported_platforms", ["all"]),
        "capabilities": config.get("capabilities")
    })

@app.route('/api/v1/servers/search')
def search_servers():
    """Search servers by query or category"""
    query = request.args.get('q')
    category = request.args.get('category')
    
    if not query and not category:
        return jsonify({"error": "Query parameter 'q' or 'category' required"}), 400
    
    results = []
    for server_id, config in servers.items():
        # Check query match
        matches_query = True
        if query:
            query_lower = query.lower()
            matches_query = (
                query_lower in server_id.lower() or
                query_lower in config.get("name", "").lower() or
                query_lower in config.get("description", "").lower()
            )
        
        # Check category filter
        matches_category = (
            category is None or 
            config.get("category", "other") == category
        )
        
        if matches_query and matches_category:
            results.append({
                "id": server_id,
                "name": config.get("name", server_id),
                "description": config.get("description", ""),
                "category": config.get("category", "other"),
                "vendor": config.get("vendor", "community"),
                "homepage": config.get("homepage", "")
            })
    
    return jsonify({
        "results": results,
        "total": len(results),
        "query": query,
        "category": category
    })

@app.route('/api/v1/servers/generate-config', methods=['POST'])
def generate_config():
    """Generate MCP configuration for specified servers"""
    data = request.get_json()
    if not data or 'servers' not in data:
        return jsonify({"error": "Missing 'servers' in request body"}), 400
    
    requested_servers = data['servers']
    format_type = data.get('format', 'claude_desktop')
    include_env = data.get('include_env_vars', True)
    
    config = {"mcpServers": {}}
    
    for server_id in requested_servers:
        if server_id not in servers:
            continue
        
        server_config = servers[server_id]
        installation = server_config.get("installation", {})
        
        # Build MCP config
        if format_type == "docker" and "docker" in installation:
            mcp_config = {
                "command": "docker",
                "args": ["run", "-i", "--rm", f"mcp/{server_id}"]
            }
        elif "command" in installation:
            command_info = installation["command"]
            mcp_config = {
                "command": command_info["command"],
                "args": command_info.get("args", [])
            }
        else:
            mcp_config = {
                "command": "npx",
                "args": ["-y", f"@modelcontextprotocol/server-{server_id}"]
            }
        
        # Add environment variables
        if include_env and "env" in server_config.get("config", {}):
            env_config = {}
            for env_var, env_info in server_config["config"]["env"].items():
                if env_info.get("required"):
                    env_config[env_var] = f"${{{env_var}}}"
            if env_config:
                mcp_config["env"] = env_config
        
        config["mcpServers"][server_id] = mcp_config
    
    return jsonify({
        "format": format_type,
        "config": config,
        "servers_included": requested_servers,
        "installation_notes": f"Add this to your {format_type} configuration file"
    })

@app.route('/api/v1/servers/validate-config', methods=['POST'])
def validate_config():
    """Validate an MCP server configuration"""
    data = request.get_json()
    if not data or 'config' not in data:
        return jsonify({"error": "Missing 'config' in request body"}), 400
    
    config = data['config']
    errors = []
    warnings = []
    
    # Basic validation
    if "command" not in config:
        errors.append("Missing required field: 'command'")
    
    command = config.get("command", "")
    if command not in ["npx", "node", "python", "docker", "deno", "bun"]:
        warnings.append(f"Unusual command: '{command}'")
    
    if "args" in config and not isinstance(config["args"], list):
        errors.append("Field 'args' must be an array")
    
    if "env" in config:
        if not isinstance(config["env"], dict):
            errors.append("Field 'env' must be an object")
        else:
            for key, value in config["env"].items():
                if not isinstance(key, str):
                    errors.append(f"Environment variable key must be string: {key}")
                if not isinstance(value, str):
                    warnings.append(f"Environment variable '{key}' value should be string")
    
    return jsonify({
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "config": config
    })

@app.route('/api/v1/categories')
def list_categories():
    """List all available server categories"""
    categories = {}
    for config in servers.values():
        category = config.get("category", "other")
        categories[category] = categories.get(category, 0) + 1
    
    result = [
        {"name": cat, "count": count}
        for cat, count in sorted(categories.items())
    ]
    return jsonify(result)

if __name__ == '__main__':
    print(f"🚀 Starting Flask REST API with {len(servers)} servers")
    print("📡 No OpenAPI generation built-in - use traffic capture!")
    print("")
    print("Available endpoints:")
    print("  GET  /health")
    print("  GET  /api/v1/servers")
    print("  GET  /api/v1/servers/{id}")
    print("  GET  /api/v1/servers/search?q=...")
    print("  POST /api/v1/servers/generate-config")
    print("  POST /api/v1/servers/validate-config")
    print("  GET  /api/v1/categories")
    print("")
    print("Capture traffic with:")
    print("  cd ../../generative-openapi && ./quick-capture.sh")
    print("")
    
    app.run(host='0.0.0.0', port=8000, debug=True)