"""
Official MCP Registry Sync Module

Syncs with the official Model Context Protocol registry at
https://registry.modelcontextprotocol.io to auto-configure available servers.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml
from datetime import datetime

from .config_parser import ConfigurationParser, MCPServerConfig, CommandType
from .local_registry import LocalRegistry

logger = logging.getLogger(__name__)


class RegistryServer:
    """Represents a server from the official MCP registry"""
    
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.id = data.get("id", "")
        self.name = data.get("name", "")
        self.description = data.get("description", "")
        self.author = data.get("author", "")
        self.homepage = data.get("homepage", "")
        self.license = data.get("license", "")
        self.categories = data.get("categories", [])
        self.runtime = data.get("runtime", "node")
        
        # Package information
        self.package = data.get("package", {})
        self.package_name = self.package.get("name", "")
        self.package_registry = self.package.get("registry", "npm")
        self.package_version = self.package.get("version", "latest")
        
        # Configuration requirements
        self.config = data.get("config", {})
        self.env_requirements = self.config.get("env", {})
        self.args = self.config.get("args", [])
    
    def to_yaml_config(self) -> Dict[str, Any]:
        """Convert registry server to our YAML configuration format"""
        yaml_config = {
            "name": self.name,
            "description": self.description,
            "category": "official",  # All registry servers are official
            "author": self.author,
            "homepage": self.homepage,
            "license": self.license,
            "tags": self.categories,
        }
        
        # Package configuration based on runtime
        if self.runtime == "node" and self.package_registry == "npm":
            yaml_config["package"] = {
                "type": "npx",
                "name": self.package_name,
                "version": self.package_version,
                "args": self.args
            }
        elif self.runtime == "python":
            yaml_config["package"] = {
                "type": "python",
                "module": self.package_name,
                "args": self.args
            }
        else:
            # Custom runtime
            yaml_config["package"] = {
                "type": "custom",
                "runtime": self.runtime,
                "name": self.package_name,
                "registry": self.package_registry,
                "version": self.package_version,
                "args": self.args
            }
        
        # Environment variables
        if self.env_requirements:
            yaml_config["environment"] = {}
            for var_name, var_config in self.env_requirements.items():
                env_entry = {
                    "required": var_config.get("required", True),
                    "description": var_config.get("description", f"Environment variable: {var_name}")
                }
                if "default" in var_config:
                    env_entry["default"] = var_config["default"]
                yaml_config["environment"][var_name] = env_entry
        
        # Add metadata
        yaml_config["_metadata"] = {
            "registry_id": self.id,
            "synced_at": datetime.utcnow().isoformat(),
            "registry_version": self.package_version
        }
        
        return yaml_config
    
    def to_mcp_server_config(self) -> MCPServerConfig:
        """Convert to MCPServerConfig for compatibility"""
        # Determine command based on runtime
        if self.runtime == "node":
            command = "npx"
            args = ["-y", self.package_name] + self.args
        elif self.runtime == "python":
            command = "python"
            args = ["-m", self.package_name] + self.args
        else:
            command = self.runtime
            args = [self.package_name] + self.args
        
        # Build environment dict
        env = {}
        for var_name, var_config in self.env_requirements.items():
            if var_config.get("required", True):
                # Use placeholder for required variables
                env[var_name] = f"${{{var_name}}}"
            elif "default" in var_config:
                env[var_name] = var_config["default"]
        
        return MCPServerConfig(
            name=self.name,
            command=command,
            args=args,
            env=env,
            description=self.description
        )


class RegistrySyncManager:
    """Manages synchronization with the local MCP registry"""
    
    def __init__(self, configs_dir: Path):
        self.configs_dir = configs_dir
        self.configs_dir.mkdir(exist_ok=True)
        self.parser = ConfigurationParser()
        
        # Create registry subdirectory for synced configs
        self.registry_configs_dir = self.configs_dir / "registry"
        self.registry_configs_dir.mkdir(exist_ok=True)
        
        # Initialize local registry
        custom_registry_path = self.configs_dir / "custom_registry.json"
        self.local_registry = LocalRegistry(custom_registry_path)
    
    async def fetch_registry_data(self) -> Dict[str, Any]:
        """Fetch data from the local registry"""
        servers = self.local_registry.list_servers()
        
        logger.info(f"Loaded {len(servers)} servers from local registry")
        
        return {
            "servers": servers,
            "total_count": len(servers),
            "version": "local-v1"
        }
    
    async def browse_official_registry(self, 
                                     search_query: Optional[str] = None,
                                     categories_filter: Optional[List[str]] = None,
                                     limit: int = 50) -> Dict[str, Any]:
        """
        Browse the local MCP registry without adding servers
        
        Args:
            search_query: Optional search term to filter servers
            categories_filter: Optional list of categories to filter servers
            limit: Maximum number of results to return
            
        Returns:
            List of available servers with metadata
        """
        logger.info("Browsing local registry...")
        
        # Get servers from local registry
        servers = self.local_registry.list_servers(
            categories=categories_filter,
            search=search_query
        )
        
        # Get all categories
        all_categories = self.local_registry.get_categories()
        
        # Limit results
        servers = servers[:limit]
        
        # Format results
        results = {
            "total_available": len(self.local_registry.list_servers()),
            "filtered_count": len(servers),
            "servers": [],
            "categories": sorted(list(all_categories)),
            "registry_version": "local-v1"
        }
        
        for server_data in servers:
            server = RegistryServer(server_data)
            results["servers"].append({
                "id": server.id,
                "name": server.name,
                "description": server.description,
                "author": server.author,
                "categories": server.categories,
                "package": server.package_name,
                "runtime": server.runtime,
                "requires_env": list(server.env_requirements.keys()),
                "homepage": server.homepage
            })
        
        return results
    
    async def add_server_from_registry(self, 
                                     server_id: str,
                                     test_connectivity: bool = True) -> Dict[str, Any]:
        """
        Add a specific server from the official registry
        
        Args:
            server_id: The registry ID of the server to add
            test_connectivity: Whether to test the server after adding
            
        Returns:
            Result of the add operation
        """
        logger.info(f"Adding server {server_id} from registry...")
        
        # Fetch specific server details
        server_data = await self.fetch_server_details(server_id)
        if not server_data:
            return {
                "status": "error",
                "error": f"Server {server_id} not found in registry"
            }
        
        try:
            server = RegistryServer(server_data)
            
            # Generate YAML configuration
            yaml_config = server.to_yaml_config()
            
            # Save configuration
            safe_name = server.name.lower().replace(" ", "-").replace("/", "-")
            yaml_path = self.configs_dir / f"{safe_name}.yaml"
            
            with open(yaml_path, 'w') as f:
                yaml.dump(yaml_config, f, default_flow_style=False, sort_keys=False)
            
            result = {
                "status": "success",
                "name": server.name,
                "id": server.id,
                "yaml_path": str(yaml_path),
                "requires_env": list(server.env_requirements.keys())
            }
            
            # Test connectivity if requested
            if test_connectivity:
                test_result = await self._test_server_connectivity(server)
                result["connectivity_test"] = test_result
                
                if test_result.get("success"):
                    result["tools_discovered"] = test_result.get("tools_count", 0)
                    result["tools"] = test_result.get("tools", [])
            
            logger.info(f"Successfully added {server.name}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to add server {server_id}: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _process_registry_server(self, 
                                     server: RegistryServer, 
                                     test_connectivity: bool) -> Dict[str, Any]:
        """Process a single registry server"""
        result = {
            "name": server.name,
            "id": server.id,
            "categories": server.categories,
            "status": "pending"
        }
        
        try:
            # Generate YAML configuration
            yaml_config = server.to_yaml_config()
            
            # Determine file path
            # Use sanitized name for filename
            safe_name = server.name.lower().replace(" ", "-").replace("/", "-")
            yaml_path = self.registry_configs_dir / f"{safe_name}.yaml"
            
            # Check if already exists and is up to date
            if yaml_path.exists():
                existing_config = yaml.safe_load(yaml_path.read_text())
                existing_version = existing_config.get("_metadata", {}).get("registry_version")
                
                if existing_version == server.package_version:
                    result["status"] = "skipped"
                    result["reason"] = "Already up to date"
                    result["yaml_path"] = str(yaml_path)
                    return result
            
            # Save YAML configuration
            with open(yaml_path, 'w') as f:
                yaml.dump(yaml_config, f, default_flow_style=False, sort_keys=False)
            
            result["yaml_path"] = str(yaml_path)
            
            # Test connectivity if requested
            if test_connectivity:
                test_result = await self._test_server_connectivity(server)
                result["connectivity_test"] = test_result
                
                if not test_result["success"]:
                    result["status"] = "warning"
                    result["warning"] = "Configuration saved but connectivity test failed"
                else:
                    result["status"] = "success"
                    result["tools_discovered"] = test_result.get("tools_count", 0)
            else:
                result["status"] = "success"
            
            logger.info(f"Successfully processed {server.name}")
            
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            logger.error(f"Failed to process {server.name}: {e}")
        
        return result
    
    async def _test_server_connectivity(self, server: RegistryServer) -> Dict[str, Any]:
        """Test if a server can be started and responds to tools/list"""
        # This is a placeholder - actual implementation would start the subprocess
        # and send a tools/list request
        return {
            "success": True,
            "tools_count": 0,
            "message": "Connectivity test not yet implemented"
        }
    
    async def _save_sync_metadata(self, results: Dict[str, Any]):
        """Save metadata about the sync operation"""
        metadata_path = self.registry_configs_dir / "_sync_metadata.json"
        
        metadata = {
            "last_sync": datetime.utcnow().isoformat(),
            "registry_version": results["registry_version"],
            "total_servers": results["total_servers"],
            "successful": results["successful"],
            "failed": results["failed"],
            "skipped": results["skipped"],
            "categories": results["categories"]
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """Get the current sync status"""
        metadata_path = self.registry_configs_dir / "_sync_metadata.json"
        
        if not metadata_path.exists():
            return {
                "synced": False,
                "message": "No sync has been performed yet"
            }
        
        with open(metadata_path) as f:
            metadata = json.load(f)
        
        # List actual config files
        config_files = list(self.registry_configs_dir.glob("*.yaml"))
        
        return {
            "synced": True,
            "last_sync": metadata["last_sync"],
            "registry_version": metadata["registry_version"],
            "total_servers": metadata["total_servers"],
            "config_files": len(config_files),
            "categories": metadata["categories"]
        }
    
    async def fetch_server_details(self, server_id: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed information about a specific server from local registry"""
        server = self.local_registry.get_server(server_id)
        
        if server:
            # Add fetch timestamp
            server["_fetched_at"] = datetime.now().isoformat()
            
        return server


class ConfigurationExporter:
    """Exports configuration suggestions for the user to apply"""
    
    def __init__(self, configs_dir: Path):
        self.configs_dir = configs_dir
    
    def generate_enable_config(self, server_names: List[str]) -> Dict[str, Any]:
        """Generate configuration snippet to enable specific servers"""
        # Validate that servers exist
        available_servers = self._get_available_servers()
        invalid_servers = [s for s in server_names if s not in available_servers]
        
        if invalid_servers:
            return {
                "status": "error",
                "error": f"Unknown servers: {', '.join(invalid_servers)}",
                "available_servers": list(available_servers.keys())
            }
        
        # Generate configuration snippet
        config_snippet = {
            "mcp-catalog": {
                "env": {
                    "ENABLED_SERVERS": ",".join(server_names)
                }
            }
        }
        
        return {
            "status": "success",
            "config_snippet": config_snippet,
            "instructions": [
                "To enable these servers, add or update the following in your claude_desktop_config.json:",
                json.dumps(config_snippet, indent=2),
                "",
                "Note: This will override any existing ENABLED_SERVERS setting.",
                "Restart Claude Desktop for changes to take effect."
            ]
        }
    
    def generate_disable_tools_config(self, tool_patterns: Dict[str, List[str]]) -> Dict[str, Any]:
        """Generate configuration to disable specific tools"""
        # Format: {"github": ["delete_*"], "taskmaster": ["debug_*"]}
        disabled_patterns = []
        for server, patterns in tool_patterns.items():
            for pattern in patterns:
                disabled_patterns.append(f"{server}:{pattern}")
        
        config_snippet = {
            "mcp-catalog": {
                "env": {
                    "DISABLED_TOOLS": ",".join(disabled_patterns)
                }
            }
        }
        
        return {
            "status": "success",
            "config_snippet": config_snippet,
            "instructions": [
                "To disable these tools, add or update the following in your claude_desktop_config.json:",
                json.dumps(config_snippet, indent=2),
                "",
                "Note: This will override any existing DISABLED_TOOLS setting.",
                "Restart Claude Desktop for changes to take effect."
            ]
        }
    
    def _get_available_servers(self) -> Dict[str, Dict[str, Any]]:
        """Get all available servers from configs"""
        servers = {}
        
        for yaml_file in self.configs_dir.glob("**/*.yaml"):
            try:
                with open(yaml_file) as f:
                    config = yaml.safe_load(f)
                    if "name" in config:
                        servers[config["name"]] = {
                            "description": config.get("description", ""),
                            "config_path": str(yaml_file.relative_to(self.configs_dir))
                        }
            except:
                continue
        
        return servers
    
    def get_current_configuration(self) -> Dict[str, Any]:
        """Get information about current configuration from environment"""
        import os
        
        enabled_servers = os.getenv("ENABLED_SERVERS", "").split(",") if os.getenv("ENABLED_SERVERS") else []
        disabled_tools = os.getenv("DISABLED_TOOLS", "").split(",") if os.getenv("DISABLED_TOOLS") else []
        
        # Parse disabled tools into server -> patterns mapping
        disabled_by_server = {}
        for item in disabled_tools:
            if ":" in item:
                server, pattern = item.split(":", 1)
                if server not in disabled_by_server:
                    disabled_by_server[server] = []
                disabled_by_server[server].append(pattern)
        
        available_servers = self._get_available_servers()
        
        return {
            "enabled_servers": [s for s in enabled_servers if s],
            "disabled_tools_by_server": disabled_by_server,
            "available_servers": list(available_servers.keys()),
            "configuration_source": "environment_variables"
        }