#!/usr/bin/env python3
"""
MCP Catalog Server main entry point.

This file provides the direct MCP server interface that can be called
by Claude Desktop via stdio without any CLI arguments.
"""

import sys
import asyncio
import os
import logging
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server.fastmcp import FastMCP

# Import our modules
from .config_generator import MCPConfigGenerator
from .dynamic_registry import DynamicToolRegistry
from .registry_sync import RegistrySyncManager, ConfigurationExporter

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_environment():
    """Load environment variables from .env file"""
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        logger.info(f"Loading environment from {env_file}")
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
        logger.info("Environment variables loaded")
    else:
        logger.warning("No .env file found")

def initialize_catalog():
    """Initialize the MCP catalog server"""
    logger.info("🚀 Starting Dynamic MCP Catalog Server...")
    
    # Generate/update configuration
    config_path = Path(__file__).parent / ".generated_mcp.json"
    logger.info("🔧 Generating configuration...")
    generator = MCPConfigGenerator()
    generator.save_generated_config(config_path)
    
    # Initialize tool registry
    registry = DynamicToolRegistry(config_path)
    registry.load_configuration()
    
    logger.info(f"📊 Catalog Summary:")
    logger.info(f"   🔧 {len(registry.config.get('servers', {}))} servers configured")
    logger.info(f"   🔑 {len(registry.config.get('environment_requirements', {}))} environment variables")
    
    return registry

async def initialize_with_discovery():
    """Initialize catalog with pre-discovery of tools BEFORE FastMCP starts"""
    logger.info("🔍 Pre-discovering tools before FastMCP initialization...")
    
    try:
        # Discover tools from all servers FIRST
        await registry.discover_all_tools()
        
        # Log discovery results
        total_tools = len(registry.tool_map)
        total_servers = len(registry.discovered_tools)
        logger.info(f"📊 Discovery Results: {total_tools} tools from {total_servers} servers")
        
        # Now that tools are discovered, we can register them with FastMCP
        if total_tools > 0:
            logger.info("🔧 Registering tools with FastMCP...")
            registration_result = registry.register_all_with_fastmcp(mcp)
            logger.info(f"✅ Registration complete: {registration_result['registered']} registered, {registration_result['skipped']} skipped")
        else:
            logger.warning("⚠️  No tools discovered to register")
        
        logger.info("🎉 MCP Catalog Server initialization complete!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error during pre-discovery initialization: {e}")
        import traceback
        traceback.print_exc()
        return False

# Load environment variables
load_environment()

# Initialize registry FIRST
registry = initialize_catalog()

# Initialize managers
configs_dir = Path(__file__).parent / "configs"
registry_sync_manager = RegistrySyncManager(configs_dir)
config_exporter = ConfigurationExporter(configs_dir)

# Initialize FastMCP server
mcp = FastMCP(name="mcp-catalog", version="1.0.0")

# Add meta-tools (these work immediately)
@mcp.tool()
def list_available_servers():
    """List all configured MCP servers"""
    servers = registry.config.get("servers", {})
    return {
        "servers": list(servers.keys()),
        "total": len(servers),
        "discovered_tools": len(registry.tool_map),
        "discovery_status": "complete" if registry.discovered_tools else "pending"
    }

@mcp.tool()
def debug_catalog_status():
    """Debug tool to check catalog server internal state"""
    return {
        "catalog_status": "alive",
        "tools_discovered": len(registry.tool_map),
        "servers_discovered": len(registry.discovered_tools),
        "tool_names": list(registry.tool_map.keys())[:10],  # First 10 tools
        "discovery_success": discovery_success if 'discovery_success' in globals() else None
    }

@mcp.tool()
async def refresh_tools():
    """Refresh tool discovery from all servers"""
    logger.info("🔄 Refreshing tool discovery...")
    
    try:
        # Clear existing tools
        registry.tool_map.clear()
        registry.discovered_tools.clear()
        
        # Re-discover and register
        await registry.discover_all_tools()
        
        total_tools = len(registry.tool_map)
        logger.info(f"🔄 Refresh complete: {total_tools} tools discovered")
        
        return {
            "status": "success", 
            "tools_discovered": total_tools,
            "servers": len(registry.discovered_tools)
        }
        
    except Exception as e:
        logger.error(f"❌ Error refreshing tools: {e}")
        return {"status": "error", "message": str(e)}

# Registry browsing and management tools
@mcp.tool()
async def browse_official_registry(
    search_query: str = None,
    categories: list = None,
    limit: int = 20
):
    """
    Browse available MCP servers from the official registry
    
    Args:
        search_query: Optional search term to filter servers
        categories: Optional list of categories to filter by
        limit: Maximum number of results to return (default: 20)
    
    Returns:
        List of available servers with metadata
    """
    return await registry_sync_manager.browse_official_registry(
        search_query=search_query,
        categories_filter=categories,
        limit=limit
    )

@mcp.tool()
async def add_server_from_registry(
    server_id: str
):
    """
    Add a specific server from the official MCP registry
    
    Args:
        server_id: The registry ID of the server (e.g., "io.github.modelcontextprotocol/server-github")
    
    Returns:
        Result of the add operation including discovered tools
    """
    result = await registry_sync_manager.add_server_from_registry(
        server_id=server_id,
        test_connectivity=True
    )
    
    # If successful, refresh our tool registry
    if result.get("status") == "success":
        await refresh_tools()
    
    return result

@mcp.tool()
def suggest_enable_servers(server_names: list):
    """
    Generate configuration to enable specific MCP servers
    
    Args:
        server_names: List of server names to enable
    
    Returns:
        Configuration snippet and instructions for the user
    """
    return config_exporter.generate_enable_config(server_names)

@mcp.tool()
def suggest_disable_tools(
    tool_patterns: dict
):
    """
    Generate configuration to disable specific tools
    
    Args:
        tool_patterns: Dictionary mapping server names to lists of tool patterns
                      Example: {"github": ["delete_*"], "taskmaster": ["debug_*"]}
    
    Returns:
        Configuration snippet and instructions for the user
    """
    return config_exporter.generate_disable_tools_config(tool_patterns)

@mcp.tool()
def get_server_configuration():
    """
    Get current server configuration from environment variables
    
    Returns:
        Current enabled servers, disabled tools, and available servers
    """
    return config_exporter.get_current_configuration()

# Run pre-discovery initialization synchronously during startup
logger.info("🚀 Starting pre-discovery initialization...")
discovery_success = asyncio.run(initialize_with_discovery())

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
            logger.error(f"Cleanup error: {e}")
    
    atexit.register(cleanup_sync)
    
    # Run the MCP server
    logger.info("🚀 Starting FastMCP server...")
    mcp.run()