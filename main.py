#!/usr/bin/env python3
"""
MCP Catalog Server main entry point.

This file provides the direct MCP server interface that can be called
by Claude Desktop via stdio without any CLI arguments.
"""

import sys
import asyncio
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server.fastmcp import FastMCP

# Import our modules
from .config_generator import MCPConfigGenerator
from .dynamic_registry import DynamicToolRegistry

def initialize_catalog():
    """Initialize the MCP catalog server"""
    print("🚀 Starting Dynamic MCP Catalog Server...")
    
    # Generate/update configuration
    config_path = Path(__file__).parent / ".generated_mcp.json"
    print("🔧 Generating configuration...")
    generator = MCPConfigGenerator()
    generator.save_generated_config(config_path)
    
    # Initialize tool registry
    registry = DynamicToolRegistry(config_path)
    
    print(f"📊 Catalog Summary:")
    print(f"   🔧 {len(registry.config.get('servers', {}))} servers configured")
    print(f"   🛠️  {registry.config.get('summary', {}).get('total_tools', 0)} total tools available")
    print(f"   🔑 {len(registry.config.get('environment_requirements', {}))} environment variables")
    
    return registry

# Initialize FastMCP server
mcp = FastMCP(
    name="mcp-catalog",
    version="1.0.0"
)

# Initialize registry and register tools
registry = initialize_catalog()
registry.load_configuration()
registry.register_all_with_fastmcp(mcp)

if __name__ == "__main__":
    import atexit
    from .subprocess_manager import get_subprocess_manager
    
    # Register cleanup handler
    async def cleanup():
        """Cleanup subprocess manager on exit"""
        manager = get_subprocess_manager()
        await manager.cleanup()
    
    def cleanup_sync():
        """Synchronous cleanup wrapper"""
        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(cleanup())
        except Exception as e:
            print(f"Cleanup error: {e}")
    
    atexit.register(cleanup_sync)
    
    # Run the MCP server
    mcp.run()