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
# Import tool schemas
from .tool_schemas import get_tool_schema

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
        
    def load_configuration(self):
        """Load the generated MCP configuration"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration not found: {self.config_path}")
            
        with open(self.config_path) as f:
            self.config = json.load(f)
            
        # Build tool map
        for server_name, server_config in self.config.get("servers", {}).items():
            for tool_name in server_config.get("tools", []):
                self.tool_map[tool_name] = server_name
                
        logger.info(f"Loaded {len(self.tool_map)} tools from {len(self.config['servers'])} servers")
    
    def create_dynamic_tool_wrapper(self, tool_name: str) -> Callable:
        """Create a dynamic wrapper function for a tool with proper parameter handling"""
        server_name = self.tool_map.get(tool_name)
        if not server_name:
            raise ValueError(f"Tool '{tool_name}' not found in registry")
        
        server_config = self.config["servers"][server_name]
        
        # Create a clean tool name with server prefix
        clean_tool_name = f"{server_name}_{tool_name}".replace("-", "_")
        
        # Get tool schema if available
        tool_schema = get_tool_schema(server_name, tool_name)
        
        # Create the base wrapper function
        async def base_wrapper(**kwargs):
            """Base wrapper that forwards to MCP server"""
            # Check if server requires subprocess
            if server_config["execution"]["type"] == "npx":
                return await self._execute_npx_tool(server_name, tool_name, kwargs)
            elif server_config["execution"]["type"] == "python":
                return await self._execute_python_tool(server_name, tool_name, kwargs)
            else:
                return {
                    "error": f"Unknown execution type: {server_config['execution']['type']}"
                }
        
        # If we have a schema, create a function with proper parameters
        if tool_schema and "properties" in tool_schema:
            # Build parameter list from schema
            params = []
            defaults = {}
            
            # Add required parameters first
            required = tool_schema.get("required", [])
            for param_name in required:
                params.append(param_name)
            
            # Add optional parameters with defaults
            for param_name, param_def in tool_schema["properties"].items():
                if param_name not in required:
                    params.append(param_name)
                    defaults[param_name] = param_def.get("default", None)
            
            # Create function signature dynamically
            sig_parts = []
            for param in params:
                if param in defaults:
                    sig_parts.append(f"{param}=None")
                else:
                    sig_parts.append(param)
            
            # Build the wrapper function with proper signature
            # We need to handle both required and optional parameters properly
            param_assignments = []
            for param in params:
                if param in required:
                    # Required parameters are always included
                    param_assignments.append(f"    kwargs['{param}'] = {param}")
                else:
                    # Optional parameters only included if not None
                    param_assignments.append(f"    if {param} is not None: kwargs['{param}'] = {param}")
            
            func_def = f"""
async def {clean_tool_name}({', '.join(sig_parts)}):
    '''Tool from {server_config['description']}'''
    # Build kwargs from actual parameters
    kwargs = {{}}
{chr(10).join(param_assignments)}
    return await base_wrapper(**kwargs)
"""
            
            # Execute the function definition
            local_vars = {"base_wrapper": base_wrapper}
            exec(func_def, local_vars)
            dynamic_tool_wrapper = local_vars[clean_tool_name]
            
        else:
            # No schema, use generic wrapper
            dynamic_tool_wrapper = base_wrapper
            dynamic_tool_wrapper.__name__ = clean_tool_name
            dynamic_tool_wrapper.__doc__ = f"Tool from {server_config['description']}"
        
        return dynamic_tool_wrapper
    
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
        """Register all dynamic tools with a FastMCP instance"""
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
                
                # Create dynamic wrapper
                wrapper = self.create_dynamic_tool_wrapper(tool_name)
                
                # Create a clean tool name with server prefix
                clean_tool_name = f"{server_name}_{tool_name}".replace("-", "_")
                
                # Get tool schema for better description
                tool_schema = get_tool_schema(server_name, tool_name)
                tool_description = f"Tool from {server_config['description']}"
                
                # Add schema info to description if available
                if tool_schema:
                    # Extract parameter info for description
                    params = []
                    for param_name, param_def in tool_schema.get("properties", {}).items():
                        param_desc = param_def.get("description", "")
                        if param_desc:
                            params.append(f"{param_name}: {param_desc}")
                    if params:
                        tool_description += f"\n\nParameters:\n" + "\n".join(f"- {p}" for p in params[:3])
                        if len(params) > 3:
                            tool_description += f"\n... and {len(params) - 3} more"
                
                # Register with FastMCP using the clean name
                # The wrapper already has the proper signature
                decorated_tool = mcp_instance.tool(
                    name=clean_tool_name,
                    description=tool_description
                )(wrapper)
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