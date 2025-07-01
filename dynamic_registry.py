"""
Dynamic Tool Registry for MCP Catalog

This module implements dynamic tool registration using FastMCP's proper APIs.
It reads tool definitions from the generated configuration and creates
dynamic wrappers that can be registered with FastMCP at runtime.
"""

import asyncio
import json
from typing import Dict, Any, Callable, Optional, List
from pathlib import Path
import subprocess
import sys
from dataclasses import dataclass
import logging
import inspect
from functools import wraps

# Import subprocess manager
from .subprocess_manager import get_subprocess_manager

logger = logging.getLogger(__name__)

@dataclass
class DynamicTool:
    """Represents a dynamically discovered tool"""
    name: str
    server_name: str
    description: str
    input_schema: Optional[Dict[str, Any]] = None
    
class DynamicToolRegistry:
    """Registry for dynamically discovered MCP tools"""
    
    def __init__(self, config_path: Optional[Path] = None, mcp_json_path: Optional[Path] = None):
        """Initialize the dynamic tool registry"""
        if config_path is None:
            config_path = Path(__file__).parent / ".generated_mcp.json"
        if mcp_json_path is None:
            # Look for .mcp.json in project root
            mcp_json_path = Path(__file__).parent.parent.parent / ".mcp.json"
        self.config_path = config_path
        self.mcp_json_path = mcp_json_path
        self.config = {}
        self.tool_map = {}  # Maps tool_name -> server_name
        self.server_processes = {}  # Maps server_name -> process info
        self.mcp_env_vars = {}  # Environment vars from .mcp.json
        self.discovered_tools = {}  # Maps server_name -> tool definitions
        self.tool_schemas = {}  # Maps server_name -> {tool_name -> schema}
        
    def load_configuration(self):
        """Load the generated MCP configuration"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration not found: {self.config_path}")
            
        with open(self.config_path) as f:
            self.config = json.load(f)
                
        logger.info(f"Loaded configuration for {len(self.config['servers'])} servers")
    
    async def discover_all_tools(self):
        """Discover tools from all configured MCP servers"""
        logger.info("Starting dynamic tool discovery...")
        
        # Get subprocess manager
        manager = get_subprocess_manager()
        discovery_errors = []
        
        for server_name, server_config in self.config.get("servers", {}).items():
            try:
                logger.info(f"🔍 Processing server: {server_name}")
                
                # Check if server has required environment variables
                requirements = self.check_server_requirements(server_name)
                if not requirements["ready"]:
                    logger.warning(f"   ⚠️  Skipping {server_name} - missing env vars: {requirements['missing_env']}")
                    discovery_errors.append(f"{server_name}: Missing environment variables: {requirements['missing_env']}")
                    continue
                
                logger.info(f"   ✅ Environment check passed for {server_name}")
                
                # Start server if needed
                if server_name not in manager.processes:
                    logger.info(f"   🚀 Starting {server_name} for tool discovery...")
                    started = await manager.start_server(server_name, server_config)
                    if not started:
                        logger.error(f"   ❌ Failed to start {server_name}")
                        discovery_errors.append(f"{server_name}: Failed to start server")
                        continue
                    
                    # Give server more time to initialize (especially TaskMaster)
                    if "taskmaster" in server_name.lower():
                        logger.info(f"   ⏱️  Giving TaskMaster extra time to initialize...")
                        await asyncio.sleep(5.0)
                    else:
                        await asyncio.sleep(3.0)
                    
                    logger.info(f"   ✅ Server {server_name} started successfully")
                
                # Discover tools with retry
                logger.info(f"   🔧 Discovering tools from {server_name}...")
                tools_response = None
                
                # Try discovery with retry
                for attempt in range(3):
                    try:
                        tools_response = await manager.list_tools(server_name)
                        if "error" not in tools_response:
                            break
                        logger.warning(f"   ⚠️  Attempt {attempt + 1} failed for {server_name}: {tools_response.get('error')}")
                        if attempt < 2:  # Don't sleep on last attempt
                            await asyncio.sleep(2.0)
                    except Exception as e:
                        logger.warning(f"   ⚠️  Attempt {attempt + 1} exception for {server_name}: {e}")
                        if attempt < 2:
                            await asyncio.sleep(2.0)
                
                if not tools_response or "error" in tools_response:
                    error_msg = tools_response.get("error", "Unknown error") if tools_response else "No response"
                    logger.error(f"   ❌ Error discovering tools from {server_name}: {error_msg}")
                    discovery_errors.append(f"{server_name}: Tool discovery failed - {error_msg}")
                    continue
                
                # Parse tools
                tools = tools_response.get("tools", [])
                self.discovered_tools[server_name] = tools
                
                logger.info(f"   📦 Found {len(tools)} tools from {server_name}")
                
                # Build tool map and schemas
                tools_added = 0
                for tool in tools:
                    tool_name = tool.get("name")
                    if tool_name:
                        self.tool_map[tool_name] = server_name
                        if server_name not in self.tool_schemas:
                            self.tool_schemas[server_name] = {}
                        self.tool_schemas[server_name][tool_name] = tool.get("inputSchema", {})
                        tools_added += 1
                
                logger.info(f"   ✅ Successfully registered {tools_added} tools from {server_name}")
                
            except Exception as e:
                logger.error(f"   ❌ Error discovering tools from {server_name}: {e}")
                discovery_errors.append(f"{server_name}: Exception during discovery - {str(e)}")
                import traceback
                traceback.print_exc()
        
        total_tools = len(self.tool_map)
        successful_servers = len(self.discovered_tools)
        total_servers = len(self.config.get("servers", {}))
        
        logger.info(f"📊 Tool discovery complete:")
        logger.info(f"   🔧 {total_tools} total tools discovered")
        logger.info(f"   📦 {successful_servers}/{total_servers} servers successful")
        
        if discovery_errors:
            logger.warning("⚠️  Discovery errors encountered:")
            for error in discovery_errors:
                logger.warning(f"   - {error}")
        
        # Stop all servers after discovery to clean up
        logger.info("🧹 Stopping discovery servers...")
        await manager.cleanup()
        logger.info("✅ Discovery cleanup complete")
    
    # NOTE: Removed create_dynamic_tool_wrapper method - replaced with proper FastMCP registration
    
    async def _execute_npx_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]):
        """Execute a tool via NPX subprocess"""
        try:
            # Get subprocess manager
            manager = get_subprocess_manager()
            
            # Get server config
            server_config = self.config["servers"][server_name]
            
            # Ensure server is running
            if server_name not in manager.processes:
                logger.info(f"Starting server {server_name} for tool execution...")
                started = await manager.start_server(server_name, server_config)
                if not started:
                    return {
                        "error": f"Failed to start server {server_name}",
                        "details": "Check environment variables and server configuration"
                    }
                # Give server a moment to initialize
                await asyncio.sleep(1.0)
            
            # Execute the tool
            logger.info(f"Executing tool {tool_name} on server {server_name}")
            result = await manager.execute_tool(server_name, tool_name, arguments)
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name} on {server_name}: {e}")
            return {
                "error": str(e),
                "server": server_name,
                "tool": tool_name
            }
    
    async def _execute_python_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]):
        """Execute a native Python tool"""
        # For knowledge graph, we can import and call directly
        if server_name == "knowledge-graph":
            try:
                # Import the module dynamically
                from src.mcp_server.knowledge_graph_mcp import execute_tool
                return await execute_tool(tool_name, arguments)
            except ImportError:
                # Fallback for demo
                return {
                    "status": "would_execute_native_python",
                    "server": server_name,
                    "tool": tool_name,
                    "arguments": arguments
                }
        
        return {
            "error": f"Python module execution not implemented for {server_name}"
        }
    
    def get_all_tools(self) -> List[DynamicTool]:
        """Get all available tools with metadata"""
        tools = []
        
        for tool_name, server_name in self.tool_map.items():
            server_config = self.config["servers"][server_name]
            tools.append(DynamicTool(
                name=tool_name,
                server_name=server_name,
                description=f"Tool from {server_config['description']}"
            ))
        
        return tools
    
    def get_tools_for_server(self, server_name: str) -> List[str]:
        """Get all tools for a specific server"""
        server_config = self.config.get("servers", {}).get(server_name)
        if not server_config:
            return []
        return server_config.get("tools", [])
    
    def check_server_requirements(self, server_name: str) -> Dict[str, Any]:
        """Check if a server has all required environment variables"""
        server_config = self.config.get("servers", {}).get(server_name)
        if not server_config:
            return {"error": f"Server '{server_name}' not found"}
        
        requirements = {
            "server": server_name,
            "ready": True,
            "missing_env": [],
            "present_env": []
        }
        
        import os
        for env_var, env_details in server_config.get("environment", {}).items():
            if env_details.get("required", True):
                if os.getenv(env_var):
                    requirements["present_env"].append(env_var)
                else:
                    requirements["ready"] = False
                    requirements["missing_env"].append(env_var)
        
        return requirements
    
    def register_all_with_fastmcp(self, mcp_instance):
        """Register all dynamic tools with a FastMCP instance using proper FastMCP API"""
        registered = 0
        skipped = 0
        
        for tool_name in self.tool_map:
            # Check if server is ready
            server_name = self.tool_map[tool_name]
            requirements = self.check_server_requirements(server_name)
            
            if not requirements["ready"]:
                logger.warning(f"Skipping {tool_name} - server {server_name} missing env vars: {requirements['missing_env']}")
                skipped += 1
                continue
            
            try:
                # Get server config for description
                server_config = self.config["servers"][server_name]
                
                # Create display name (what LLM sees) - preserve hyphens
                display_name = f"{server_name}_{tool_name}"
                
                # Get discovered tool info for description
                tool_info = None
                for tool in self.discovered_tools.get(server_name, []):
                    if tool.get("name") == tool_name:
                        tool_info = tool
                        break
                
                # Create tool description from discovered info
                if tool_info:
                    tool_description = tool_info.get("description", f"Tool from {server_config['description']}")
                else:
                    tool_description = f"Tool from {server_config['description']}"
                
                # Create async wrapper function that forwards to subprocess execution
                def create_tool_wrapper(server_name=server_name, tool_name=tool_name, display_name=display_name):
                    async def tool_wrapper(**kwargs):
                        """Dynamic wrapper that forwards to subprocess execution"""
                        try:
                            # Extract actual arguments - Claude wraps them in "kwargs"
                            if "kwargs" in kwargs and isinstance(kwargs["kwargs"], dict):
                                # Claude is passing: {"kwargs": {"id": "50.2", "status": "done", ...}}
                                actual_args = kwargs["kwargs"]
                                logger.info(f"Extracted kwargs for {display_name}: {actual_args}")
                            else:
                                # Direct parameters: {"id": "50.2", "status": "done", ...}
                                actual_args = kwargs
                                logger.info(f"Using direct args for {display_name}: {actual_args}")
                            
                            # Execute via subprocess
                            result = await self._execute_npx_tool(server_name, tool_name, actual_args)
                            return result
                        except Exception as e:
                            logger.error(f"Error executing {display_name}: {e}")
                            return {
                                "error": str(e),
                                "tool": display_name,
                                "server": server_name
                            }
                    return tool_wrapper
                
                # Create the wrapper
                wrapper_func = create_tool_wrapper()
                
                # Register with FastMCP using proper API - display_name is what LLM sees
                logger.info(f"🔧 Attempting to register tool: {display_name}")
                
                decorated_func = mcp_instance.tool(
                    name=display_name,
                    description=tool_description
                )(wrapper_func)
                
                logger.info(f"✅ Successfully registered tool: {display_name}")
                registered += 1
                
            except Exception as e:
                logger.error(f"Failed to register {tool_name}: {e}")
                skipped += 1
        
        logger.info(f"Registered {registered} tools, skipped {skipped}")
        return {"registered": registered, "skipped": skipped}

# Example usage
if __name__ == "__main__":
    # Test the registry
    registry = DynamicToolRegistry()
    registry.load_configuration()
    
    print(f"\n🔍 Discovered {len(registry.tool_map)} tools:")
    for i, (tool, server) in enumerate(list(registry.tool_map.items())[:10]):
        print(f"   {i+1}. {tool} (from {server})")
    
    if len(registry.tool_map) > 10:
        print(f"   ... and {len(registry.tool_map) - 10} more")
    
    # Check requirements
    print("\n📋 Server readiness:")
    for server_name in registry.config["servers"]:
        req = registry.check_server_requirements(server_name)
        status = "✅ Ready" if req["ready"] else f"❌ Missing: {', '.join(req['missing_env'])}"
        print(f"   - {server_name}: {status}")