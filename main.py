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
    """Initialize catalog with pre-discovery for proxy architecture"""
    logger.info("🔍 Initializing MCP Catalog Server with proxy architecture...")
    
    # Get configuration from environment
    enabled_servers = os.getenv("MCP_CATALOG_ENABLED_SERVERS", "").strip()
    disabled_tools = os.getenv("MCP_CATALOG_DISABLED_TOOLS", "").strip()
    
    # Parse enabled servers (comma-separated, or "*" for all)
    if enabled_servers:
        if enabled_servers == "*":
            enabled_servers_list = None  # None means all servers
            logger.info("📋 Server control: All servers enabled")
        else:
            enabled_servers_list = [s.strip() for s in enabled_servers.split(",") if s.strip()]
            logger.info(f"📋 Server control: Only enabling {enabled_servers_list}")
    else:
        enabled_servers_list = None  # Default: all servers enabled
        
    # Parse disabled tools (comma-separated)
    disabled_tools_list = [t.strip() for t in disabled_tools.split(",") if t.strip()] if disabled_tools else []
    if disabled_tools_list:
        logger.info(f"🚫 Tool control: Disabling tools {disabled_tools_list}")
    
    try:
        from .subprocess_manager import get_subprocess_manager
        manager = get_subprocess_manager()
        
        # 1. Start configured servers that are ready
        logger.info("🚀 Starting configured MCP servers...")
        started_servers = []
        
        for server_name, server_config in registry.config.get("servers", {}).items():
            # Check if server is enabled
            if enabled_servers_list is not None and server_name not in enabled_servers_list:
                logger.info(f"   ⏭️  Skipped {server_name}: not in enabled servers list")
                continue
            req = registry.check_server_requirements(server_name)
            if req["ready"]:
                try:
                    # Transform config format for subprocess manager
                    transformed_config = transform_config_for_subprocess(server_config)
                    
                    # Start the server process with transformed config
                    success = await manager.start_server(server_name, transformed_config)
                    if success:
                        started_servers.append(server_name)
                        logger.info(f"   ✅ Started: {server_name}")
                    else:
                        logger.warning(f"   ❌ Failed to start: {server_name}")
                except Exception as e:
                    logger.warning(f"   ❌ Error starting {server_name}: {e}")
            else:
                logger.warning(f"   ⏭️  Skipped {server_name}: missing {req['missing_env']}")
        
        # 2. Discover tools from started servers
        logger.info("🔍 Discovering tools from started servers...")
        all_discovered_tools = []
        
        for server_name in started_servers:
            try:
                # Use list_tools method from subprocess_manager
                tools_response = await manager.list_tools(server_name)
                if tools_response and "tools" in tools_response:
                    tools = tools_response["tools"]
                    logger.info(f"   📊 {server_name}: {len(tools)} tools discovered")
                    for tool in tools:
                        tool["server"] = server_name  # Add server context
                        all_discovered_tools.append(tool)
                else:
                    logger.warning(f"   ⚠️  {server_name}: No tools discovered")
            except Exception as e:
                logger.warning(f"   ❌ Error discovering tools from {server_name}: {e}")
        
        # 3. Register proxy tools with FastMCP
        logger.info("🔗 Registering proxy tools...")
        proxy_tools_registered = register_proxy_tools(all_discovered_tools, disabled_tools_list)
        
        logger.info("🎉 MCP Catalog Server initialization complete!")
        logger.info(f"   🚀 {len(started_servers)} servers running")
        logger.info(f"   🔧 {len(all_discovered_tools)} tools discovered")
        logger.info(f"   🔗 {proxy_tools_registered} proxy tools registered")
        
        # Keep servers running for proxying - DON'T cleanup!
        logger.info("💡 Servers kept running for tool proxying")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error during initialization: {e}")
        import traceback
        traceback.print_exc()
        return False

def transform_config_for_subprocess(server_config):
    """Transform local registry config format to subprocess manager format"""
    package = server_config.get("package", {})
    package_name = package.get("name", "")
    registry_type = package.get("registry", "npm")
    
    # Build execution config based on package type
    if registry_type == "npm":
        if package_name.startswith("@"):
            # Scoped npm package
            execution = {
                "command": "npx",
                "args": ["-y", package_name]
            }
        else:
            # Regular npm package
            execution = {
                "command": "npx", 
                "args": ["-y", package_name]
            }
    elif registry_type == "local":
        # Local Python server (like knowledge-graph)
        execution = {
            "command": "python",
            "args": ["-m", "mcp_server"]  # This will need adjustment per server
        }
    else:
        # Default to npm
        execution = {
            "command": "npx",
            "args": ["-y", package_name]
        }
    
    # Get environment variables from config
    env_vars = {}
    config_env = server_config.get("config", {}).get("env", {})
    
    # Build the subprocess manager format
    return {
        "execution": execution,
        "environment": env_vars
    }

def register_proxy_tools(discovered_tools, disabled_tools_list=None):
    """Register proxy tools with FastMCP that forward to subprocess servers"""
    from .subprocess_manager import get_subprocess_manager
    
    registered_count = 0
    skipped_count = 0
    manager = get_subprocess_manager()
    disabled_tools_list = disabled_tools_list or []
    
    for tool_info in discovered_tools:
        try:
            server_name = tool_info["server"]
            tool_name = tool_info["name"]
            tool_description = tool_info.get("description", f"Tool {tool_name} from {server_name}")
            
            # Create unique tool name to avoid conflicts
            proxy_tool_name = f"{server_name}_{tool_name}"
            
            # Check if tool is disabled
            if proxy_tool_name in disabled_tools_list or tool_name in disabled_tools_list:
                logger.debug(f"   ⏭️  Skipped disabled tool: {proxy_tool_name}")
                skipped_count += 1
                continue
            
            # Create proxy function with closure to capture variables
            def create_proxy_tool(srv_name, tl_name):
                async def proxy_tool(**kwargs):
                    """Proxy tool that forwards to subprocess MCP server"""
                    try:
                        # Handle Claude's nested argument structure  
                        if "kwargs" in kwargs and isinstance(kwargs["kwargs"], dict):
                            actual_args = kwargs["kwargs"]
                        else:
                            actual_args = kwargs
                        
                        # Forward request to target server via JSON-RPC
                        result = await manager.execute_tool(
                            server_name=srv_name,
                            tool_name=tl_name,
                            arguments=actual_args
                        )
                        return result
                    except Exception as e:
                        logger.error(f"❌ Proxy error for {srv_name}_{tl_name}: {e}")
                        return {"error": f"Proxy error: {str(e)}"}
                
                return proxy_tool
            
            # Register with FastMCP
            proxy_func = create_proxy_tool(server_name, tool_name)
            decorated_func = mcp.tool(
                name=proxy_tool_name,
                description=tool_description
            )(proxy_func)
            
            registered_count += 1
            logger.debug(f"   ✅ Registered proxy: {proxy_tool_name}")
            
        except Exception as e:
            logger.warning(f"   ❌ Failed to register proxy for {tool_info.get('name', 'unknown')}: {e}")
    
    if skipped_count > 0:
        logger.info(f"   ⏭️  Skipped {skipped_count} disabled tools")
    
    return registered_count

# Load environment variables
load_environment()

# Initialize registry FIRST
registry = initialize_catalog()

# Initialize managers
configs_dir = Path(__file__).parent / "configs"
registry_sync_manager = RegistrySyncManager(configs_dir)
config_exporter = ConfigurationExporter(configs_dir)

# Use FastMCP server lifecycle management pattern from the documentation
from contextlib import asynccontextmanager
from typing import AsyncIterator

@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[dict]:
    """Manage server startup and shutdown lifecycle with proxy initialization"""
    global discovery_success, _proxy_initialized
    
    logger.info("🔍 FastMCP server starting - initializing proxy architecture...")
    
    # Initialize proxy on startup
    try:
        discovery_success = await initialize_with_discovery()
        _proxy_initialized = True
        if discovery_success:
            logger.info("✅ Proxy initialization completed successfully")
        else:
            logger.error("❌ Proxy initialization failed")
    except Exception as e:
        logger.error(f"❌ Error during proxy initialization: {e}")
        discovery_success = False
    
    try:
        yield {"discovery_success": discovery_success, "proxy_initialized": _proxy_initialized}
    finally:
        # Cleanup on shutdown
        logger.info("🔄 Cleaning up proxy servers...")
        try:
            from .subprocess_manager import get_subprocess_manager
            manager = get_subprocess_manager()
            await manager.cleanup()
            logger.info("✅ Proxy cleanup completed")
        except Exception as e:
            logger.error(f"❌ Error during proxy cleanup: {e}")

# Apply lifespan to FastMCP server
mcp = FastMCP(name="mcp-catalog", version="1.0.0", lifespan=server_lifespan)

# Add meta-tools (these work immediately)
@mcp.tool()
def list_available_servers():
    """List all configured MCP servers"""
    servers = registry.config.get("servers", {})
    return {
        "servers": list(servers.keys()),
        "total": len(servers),
        "discovered_tools": len(registry.tool_map),
        "discovery_status": "on-demand"  # Tools are discovered when needed
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
    config = config_exporter.get_current_configuration()
    
    # Add current control settings
    config["control_settings"] = {
        "enabled_servers": os.getenv("MCP_CATALOG_ENABLED_SERVERS", "* (all)"),
        "disabled_tools": os.getenv("MCP_CATALOG_DISABLED_TOOLS", "(none)"),
        "configuration_info": {
            "MCP_CATALOG_ENABLED_SERVERS": "Comma-separated list of servers to enable, or '*' for all",
            "MCP_CATALOG_DISABLED_TOOLS": "Comma-separated list of tools to disable (e.g., 'perplexity-ask_perplexity_ask,taskmaster-ai_research')"
        }
    }
    
    return config

# Initialize state variables for proxy
logger.info("🚀 MCP Catalog ready - proxy initialization will happen during FastMCP startup")
discovery_success = None
_proxy_initialized = False

if __name__ == "__main__":
    import atexit
    import os
    from .subprocess_manager import get_subprocess_manager
    
    # Check if we should trigger discovery
    trigger_env = os.getenv("MCP_CATALOG_TRIGGER_DISCOVERY")
    logger.info(f"🔍 Discovery trigger env var: {trigger_env}")
    
    if trigger_env == "true":
        logger.info("🔍 Triggering pre-discovery initialization...")
        try:
            import asyncio
            discovery_success = asyncio.run(initialize_with_discovery())
            if discovery_success:
                logger.info("✅ Pre-discovery completed successfully")
            else:
                logger.error("❌ Pre-discovery failed")
        except Exception as e:
            logger.error(f"❌ Error during pre-discovery: {e}")
    else:
        logger.info("⏭️  Skipping pre-discovery (trigger not set)")
    
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