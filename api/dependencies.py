#!/usr/bin/env python3
"""
FastAPI dependencies for MCP Catalog API
"""

import json
from pathlib import Path
from typing import Dict, Any

# Global server registry
_server_registry: Dict[str, Any] = {}

def load_server_registry() -> None:
    """Load the known servers registry"""
    global _server_registry
    
    # Look for known_servers.json in registry directory
    current_dir = Path(__file__).parent.parent
    registry_paths = [
        current_dir / "registry" / "known_servers.json",
        current_dir.parent / "registry" / "known_servers.json",  # For development
    ]
    
    for registry_path in registry_paths:
        if registry_path.exists():
            with open(registry_path, 'r') as f:
                _server_registry = json.load(f)
            print(f"📚 Loaded {len(_server_registry)} servers from {registry_path}")
            return
    
    print("⚠️  No known_servers.json found")
    _server_registry = {}

def get_server_registry() -> Dict[str, Any]:
    """Get the loaded server registry"""
    return _server_registry

def get_server_by_id(server_id: str) -> Dict[str, Any] | None:
    """Get a specific server by ID"""
    return _server_registry.get(server_id)