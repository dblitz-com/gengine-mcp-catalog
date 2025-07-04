#!/usr/bin/env python3
"""
MCP Catalog REST API Server

A pure REST API that provides MCP server discovery and configuration generation.
No MCP protocol implementation - just REST endpoints.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Server registry - loaded from known_servers.json
_server_registry: Dict[str, Any] = {}

def load_server_registry():
    """Load the known servers registry"""
    global _server_registry
    
    # Look for known_servers.json in current directory and parent directories
    current_dir = Path(__file__).parent
    for search_dir in [current_dir, current_dir.parent, current_dir.parent / "src" / "mcp_catalog_server"]:
        known_servers_path = search_dir / "known_servers.json"
        if known_servers_path.exists():
            with open(known_servers_path, 'r') as f:
                _server_registry = json.load(f)
            print(f"📚 Loaded {len(_server_registry)} servers from {known_servers_path}")
            return
    
    print("⚠️  No known_servers.json found")
    _server_registry = {}

# Load registry on startup
load_server_registry()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "server_count": len(_server_registry),
        "catalog_version": "1.0.0",
        "api_version": "v1"
    })

@app.route('/api/v1/servers', methods=['GET'])
def list_available_servers():
    """List all available MCP servers"""
    servers = []
    for server_id, server_config in _server_registry.items():
        servers.append({
            "id": server_id,
            "name": server_config.get("name", server_id),
            "description": server_config.get("description", ""),
            "category": server_config.get("category", "other"),
            "homepage": server_config.get("homepage", ""),
            "vendor": server_config.get("vendor", "community")
        })
    
    return jsonify({
        "servers": servers,
        "total": len(servers)
    })

@app.route('/api/v1/servers/<server_id>', methods=['GET'])
def get_server_info(server_id: str):
    """Get detailed information about a specific MCP server"""
    if server_id not in _server_registry:
        return jsonify({"error": f"Server '{server_id}' not found"}), 404
    
    server_config = _server_registry[server_id]
    
    # Build detailed response
    info = {
        "id": server_id,
        "name": server_config.get("name", server_id),
        "description": server_config.get("description", ""),
        "category": server_config.get("category", "other"),
        "vendor": server_config.get("vendor", "community"),
        "homepage": server_config.get("homepage", ""),
        "license": server_config.get("license", "Unknown"),
        "installation": server_config.get("installation", {}),
        "config": server_config.get("config", {}),
        "features": server_config.get("features", []),
        "supported_platforms": server_config.get("supported_platforms", ["all"])
    }
    
    # Add capabilities if available
    if "capabilities" in server_config:
        info["capabilities"] = server_config["capabilities"]
    
    return jsonify(info)

@app.route('/api/v1/servers/generate-config', methods=['POST'])
def generate_mcp_config():
    """Generate MCP configuration for specified servers"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400
    
    servers = data.get("servers", [])
    format = data.get("format", "claude_desktop")
    include_env_vars = data.get("include_env_vars", True)
    
    if not servers:
        return jsonify({"error": "No servers specified"}), 400
    
    # Generate configuration
    config = {"mcpServers": {}}
    
    for server_id in servers:
        if server_id not in _server_registry:
            continue
        
        server_config = _server_registry[server_id]
        
        # Get installation command based on format
        installation = server_config.get("installation", {})
        if format == "docker" and "docker" in installation:
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
            # Default NPX installation
            mcp_config = {
                "command": "npx",
                "args": ["-y", f"@modelcontextprotocol/server-{server_id}"]
            }
        
        # Add environment variables if requested
        if include_env_vars and "env" in server_config.get("config", {}):
            env_config = {}
            for env_var, env_config_item in server_config["config"]["env"].items():
                if env_config_item.get("required"):
                    env_config[env_var] = f"${{{env_var}}}"
            if env_config:
                mcp_config["env"] = env_config
        
        config["mcpServers"][server_id] = mcp_config
    
    return jsonify({
        "format": format,
        "config": config,
        "servers_included": servers,
        "installation_notes": f"Add this to your {format} configuration file"
    })

@app.route('/api/v1/servers/search', methods=['GET'])
def search_servers():
    """Search MCP servers by query"""
    query = request.args.get('q', '').lower()
    category = request.args.get('category')
    
    if not query and not category:
        return jsonify({"error": "Query parameter 'q' or 'category' required"}), 400
    
    results = []
    
    for server_id, server_config in _server_registry.items():
        # Check if matches query
        matches_query = True
        if query:
            matches_query = (
                query in server_id.lower() or
                query in server_config.get("name", "").lower() or
                query in server_config.get("description", "").lower()
            )
        
        # Check category filter
        matches_category = (
            category is None or 
            server_config.get("category", "other") == category
        )
        
        if matches_query and matches_category:
            results.append({
                "id": server_id,
                "name": server_config.get("name", server_id),
                "description": server_config.get("description", ""),
                "category": server_config.get("category", "other"),
                "vendor": server_config.get("vendor", "community")
            })
    
    return jsonify({
        "results": results,
        "total": len(results),
        "query": query,
        "category": category
    })

@app.route('/api/v1/servers/validate-config', methods=['POST'])
def validate_server_config():
    """Validate an MCP server configuration"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400
    
    config = data.get("config", {})
    
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
    
    return jsonify({
        "valid": is_valid,
        "errors": errors,
        "warnings": warnings,
        "config": config
    })

@app.route('/api/v1/categories', methods=['GET'])
def list_categories():
    """List all available server categories"""
    categories = {}
    
    for server_config in _server_registry.values():
        category = server_config.get("category", "other")
        if category not in categories:
            categories[category] = 0
        categories[category] += 1
    
    return jsonify({
        "categories": [
            {"name": cat, "count": count}
            for cat, count in sorted(categories.items())
        ]
    })

@app.route('/openapi.json', methods=['GET'])
def get_openapi_spec():
    """Return OpenAPI specification for this API"""
    return jsonify({
        "openapi": "3.0.0",
        "info": {
            "title": "MCP Catalog API",
            "description": "REST API for discovering and configuring Model Context Protocol servers",
            "version": "1.0.0"
        },
        "servers": [
            {"url": "http://localhost:8000", "description": "Local development server"}
        ],
        "paths": {
            "/health": {
                "get": {
                    "summary": "Health check",
                    "operationId": "health_check",
                    "responses": {
                        "200": {
                            "description": "Server is healthy",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {"type": "string"},
                                            "server_count": {"type": "integer"},
                                            "catalog_version": {"type": "string"},
                                            "api_version": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/v1/servers": {
                "get": {
                    "summary": "List all available MCP servers",
                    "operationId": "list_available_servers",
                    "responses": {
                        "200": {
                            "description": "List of servers",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "servers": {
                                                "type": "array",
                                                "items": {"$ref": "#/components/schemas/ServerSummary"}
                                            },
                                            "total": {"type": "integer"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/v1/servers/{server_id}": {
                "get": {
                    "summary": "Get detailed server information",
                    "operationId": "get_server_info",
                    "parameters": [
                        {
                            "name": "server_id",
                            "in": "path",
                            "required": true,
                            "schema": {"type": "string"}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Server details",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ServerDetails"}
                                }
                            }
                        },
                        "404": {
                            "description": "Server not found"
                        }
                    }
                }
            },
            "/api/v1/servers/generate-config": {
                "post": {
                    "summary": "Generate MCP configuration",
                    "operationId": "generate_mcp_config",
                    "requestBody": {
                        "required": true,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "servers": {
                                            "type": "array",
                                            "items": {"type": "string"}
                                        },
                                        "format": {"type": "string", "default": "claude_desktop"},
                                        "include_env_vars": {"type": "boolean", "default": true}
                                    },
                                    "required": ["servers"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Generated configuration"
                        }
                    }
                }
            },
            "/api/v1/servers/search": {
                "get": {
                    "summary": "Search MCP servers",
                    "operationId": "search_servers",
                    "parameters": [
                        {
                            "name": "q",
                            "in": "query",
                            "schema": {"type": "string"}
                        },
                        {
                            "name": "category",
                            "in": "query",
                            "schema": {"type": "string"}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Search results"
                        }
                    }
                }
            },
            "/api/v1/servers/validate-config": {
                "post": {
                    "summary": "Validate server configuration",
                    "operationId": "validate_server_config",
                    "requestBody": {
                        "required": true,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "config": {"type": "object"}
                                    },
                                    "required": ["config"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Validation result"
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "ServerSummary": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "category": {"type": "string"},
                        "vendor": {"type": "string"}
                    }
                },
                "ServerDetails": {
                    "allOf": [
                        {"$ref": "#/components/schemas/ServerSummary"},
                        {
                            "type": "object",
                            "properties": {
                                "homepage": {"type": "string"},
                                "license": {"type": "string"},
                                "installation": {"type": "object"},
                                "config": {"type": "object"},
                                "features": {"type": "array", "items": {"type": "string"}},
                                "supported_platforms": {"type": "array", "items": {"type": "string"}}
                            }
                        }
                    ]
                }
            }
        }
    })

if __name__ == "__main__":
    import sys
    
    print(f"🚀 Starting MCP Catalog REST API with {len(_server_registry)} servers")
    print("📄 OpenAPI spec available at: http://localhost:8000/openapi.json")
    
    if "--production" in sys.argv:
        app.run(host="0.0.0.0", port=8000)
    else:
        app.run(debug=True, port=8000)