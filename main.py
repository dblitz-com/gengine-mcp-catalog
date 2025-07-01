#!/usr/bin/env python3
"""
Main entry point for MCP Catalog Server when run as a standalone script.
This mimics the behavior of mcp_catalog_dynamic.py but uses the packaged modules.
"""

import sys
import os
from pathlib import Path
import atexit
import asyncio
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add package to path if needed
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server.fastmcp import FastMCP
from mcp_catalog_server.config_generator import MCPConfigGenerator
from mcp_catalog_server.dynamic_registry import DynamicToolRegistry
from mcp_catalog_server.subprocess_manager import get_subprocess_manager

# Initialize FastMCP server
mcp = FastMCP(
    name="mcp-catalog",
    instructions="""
Dynamic MCP Catalog Server - Universal wrapper for all MCP servers.

This server dynamically discovers and exposes tools from multiple MCP servers
configured via YAML files. It provides:

• Automatic tool discovery from configured servers
• Dynamic tool registration without hardcoding
• Meta-tools for server discovery and configuration
• Single entry point replacing all MCP server entries

Use meta-tools to explore:
• list_available_servers() - See all configured servers
• check_server_requirements() - Check env requirements
• list_all_tools() - Browse all available tools
• search_tools(query) - Search for specific tools
• get_tool_details(tool_name) - Get tool documentation
"""
)

def initialize_catalog(config_path=None):
    """Initialize the dynamic MCP catalog with all discovered tools"""
    # Determine config path
    if config_path is None:
        # Try environment variable first
        config_path = os.environ.get("MCP_CATALOG_CONFIG_PATH")
        if not config_path:
            # Default to src/mcp_catalog/configs
            config_path = Path(__file__).parent / "configs"
    
    config_path = Path(config_path)
    
    # Load environment from .env if it exists
    env_path = os.environ.get("MCP_CATALOG_ENV_PATH")
    if not env_path:
        # Try project root .env
        project_root = Path(__file__).parent.parent.parent
        env_file = project_root / ".env"
        if env_file.exists():
            env_path = env_file
    
    if env_path and Path(env_path).exists():
        from dotenv import load_dotenv
        load_dotenv(env_path)
        print(f"✅ Loaded environment from {env_path}")
    
    # Initialize config generator and registry
    print(f"🔧 Using config path: {config_path}")
    generator = MCPConfigGenerator(str(config_path))
    config = generator.generate_config()
    
    # Save generated config
    generated_path = config_path.parent / ".generated_mcp.json"
    generator.save_generated_config(str(generated_path))
    
    # Initialize registry
    registry = DynamicToolRegistry(config_path=generated_path)
    
    print("🚀 Starting Dynamic MCP Catalog Server...")
    
    # Load configuration
    registry.load_configuration()
    
    # Register all dynamic tools
    print("\n📝 Registering dynamic tools...")
    result = registry.register_all_with_fastmcp(mcp)
    
    print(f"\n✅ Dynamic MCP Catalog Server initialized!")
    print(f"   📊 {len(registry.config.get('servers', {}))} servers configured")
    print(f"   🛠️  {result['registered']} tools registered")
    print(f"   ⚠️  {result['skipped']} tools skipped (missing env vars)")
    print(f"\n🔍 Use meta-tools to explore:")
    print(f"   • list_available_servers() - See all servers")
    print(f"   • list_all_tools() - Browse available tools")
    print(f"   • search_tools(query) - Find specific tools")
    print(f"   • check_server_requirements(server) - Check env vars")

if __name__ == "__main__":
    # Register cleanup handler
    async def cleanup():
        manager = get_subprocess_manager()
        await manager.cleanup()
    
    def sync_cleanup():
        asyncio.run(cleanup())
    
    atexit.register(sync_cleanup)
    
    # Get config path from command line if provided
    config_path = None
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    initialize_catalog(config_path)
    mcp.run()