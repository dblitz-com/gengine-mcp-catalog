"""
Main MCP Catalog Server implementation.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

from mcp.server.fastmcp import FastMCP

from .config_generator import MCPConfigGenerator
from .dynamic_registry import DynamicToolRegistry
from .subprocess_manager import SubprocessManager

logger = logging.getLogger(__name__)


class MCPCatalogServer:
    """Main MCP Catalog Server class."""
    
    def __init__(self, config_path: Optional[Path] = None, env_path: Optional[Path] = None):
        """
        Initialize the MCP Catalog Server.
        
        Args:
            config_path: Path to MCP configuration directory (default: ~/.mcp/)
            env_path: Path to .env file (default: ~/.mcp/.env)
        """
        self.config_path = config_path or Path.home() / ".mcp"
        self.env_path = env_path or self.config_path / ".env"
        
        # Initialize FastMCP server
        self.mcp = FastMCP(
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
        
        # Initialize components
        self.config_generator = None
        self.registry = None
        self.subprocess_manager = None
        self.initialized = False
        
    async def initialize(self):
        """Initialize the server components."""
        if self.initialized:
            return
            
        logger.info(f"Initializing MCP Catalog Server from {self.config_path}")
        
        try:
            # Load environment variables
            if self.env_path.exists():
                from dotenv import load_dotenv
                load_dotenv(self.env_path)
                logger.info(f"Loaded environment from {self.env_path}")
            
            # Initialize configuration generator
            self.config_generator = MCPConfigGenerator(str(self.config_path))
            
            # Generate configuration from YAML files
            config = self.config_generator.generate_config()
            
            # Initialize subprocess manager
            self.subprocess_manager = SubprocessManager()
            
            # Initialize tool registry
            # First generate the config file
            config_file = self.config_path / ".generated_mcp.json"
            with open(config_file, 'w') as f:
                import json
                json.dump(config, f, indent=2)
            
            # Initialize registry with config file path
            self.registry = DynamicToolRegistry(config_path=config_file)
            
            # Load configuration
            self.registry.load_configuration()
            
            # Register all tools
            self.registry.register_all_with_fastmcp(self.mcp)
            
            self.initialized = True
            logger.info("MCP Catalog Server initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP Catalog Server: {e}")
            raise
    
    async def run(self):
        """Run the MCP Catalog Server."""
        try:
            # Initialize if not already done
            await self.initialize()
            
            # Run the FastMCP server
            logger.info("Starting MCP Catalog Server...")
            await self.mcp.run()
            
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise
        finally:
            # Cleanup
            if self.subprocess_manager:
                await self.subprocess_manager.cleanup()
            logger.info("MCP Catalog Server stopped")
    
    def get_mcp_instance(self) -> FastMCP:
        """Get the FastMCP instance for direct access."""
        return self.mcp


def create_server(config_path: Optional[str] = None, env_path: Optional[str] = None) -> MCPCatalogServer:
    """
    Create an MCP Catalog Server instance.
    
    Args:
        config_path: Path to MCP configuration directory
        env_path: Path to .env file
        
    Returns:
        MCPCatalogServer instance
    """
    config_p = Path(config_path) if config_path else None
    env_p = Path(env_path) if env_path else None
    
    return MCPCatalogServer(config_path=config_p, env_path=env_p)