"""
MCP Configuration Generator

Generates a unified .generated_mcp.json configuration from the local registry
of MCP servers and custom registry JSON files. No longer supports YAML configurations.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any
from .local_registry import LocalRegistry

class MCPConfigGenerator:
    """Generates unified MCP configuration from local registry and custom registry JSON"""
    
    def __init__(self, config_dir: str = None):
        """Initialize with configuration directory"""
        if config_dir is None:
            config_dir = Path(__file__).parent / "configs"
        self.config_dir = Path(config_dir)
        
        # Initialize local registry
        custom_registry_path = self.config_dir.parent / "custom_registry.json"
        self.local_registry = LocalRegistry(custom_registry_path)
        
        self.generated_config = {
            "version": "1.0.0",
            "generated_at": None,
            "servers": {},
            "environment_requirements": {},
            "categories": {}
        }
    
    def _load_custom_registry_servers(self) -> List[Dict[str, Any]]:
        """Load servers from custom registry JSON file"""
        custom_registry_path = self.config_dir.parent / "custom_registry.json"
        
        if not custom_registry_path.exists():
            return []
            
        try:
            with open(custom_registry_path, 'r') as f:
                custom_servers = json.load(f)
                # Convert dict of servers to list format
                servers_list = []
                for server_id, server_data in custom_servers.items():
                    # Ensure server has an id if not present
                    if 'id' not in server_data:
                        server_data['id'] = server_id
                    if 'name' not in server_data:
                        server_data['name'] = server_id
                    servers_list.append(server_data)
                
                print(f"✅ Loaded {len(servers_list)} servers from custom registry")
                return servers_list
        except Exception as e:
            print(f"❌ Failed to load custom registry: {e}")
            return []
    
    def _process_registry_server(self, server_data: Dict[str, Any]):
        """Process a server from the local registry"""
        server_name = server_data.get("name")
        
        # Extract package info
        package_info = server_data.get("package", {})
        
        # Build execution config based on package type
        execution = {}
        if package_info.get("registry") == "npm":
            execution = {
                "type": "npx",
                "package": package_info.get("name"),
                "args": server_data.get("config", {}).get("args", [])
            }
        
        # Build server entry
        server_entry = {
            "name": server_name,
            "description": server_data.get("description", ""),
            "category": "official",  # All registry servers are official
            "version": package_info.get("version", "latest"),
            "package": {
                "type": "npx",
                "name": package_info.get("name"),
                "version": package_info.get("version", "latest"),
                "args": server_data.get("config", {}).get("args", [])
            },
            "execution": execution,
            "environment": {},
            "tools": [],  # Will be discovered dynamically
            "metadata": {
                "id": server_data.get("id", ""),
                "repository": server_data.get("repository", {}),
                "categories": server_data.get("categories", [])
            }
        }
        
        # Process environment variables
        env_config = server_data.get("config", {}).get("env", {})
        for env_var, env_details in env_config.items():
            if isinstance(env_details, dict):
                server_entry["environment"][env_var] = {
                    "required": env_details.get("required", True),
                    "description": env_details.get("description", "")
                }
                
                # Track global environment requirements
                if env_var not in self.generated_config["environment_requirements"]:
                    self.generated_config["environment_requirements"][env_var] = {
                        "required_by": [],
                        "description": env_details.get("description", ""),
                        "example": env_details.get("default", "")
                    }
                self.generated_config["environment_requirements"][env_var]["required_by"].append(server_name)
        
        # Add to servers
        self.generated_config["servers"][server_name] = server_entry
        
        # Track categories
        for category in server_data.get("categories", ["official"]):
            if category not in self.generated_config["categories"]:
                self.generated_config["categories"][category] = []
            self.generated_config["categories"][category].append(server_name)
    
    def generate_config(self) -> Dict[str, Any]:
        """Generate unified configuration from local registry and custom registry JSON"""
        from datetime import datetime
        
        self.generated_config["generated_at"] = datetime.now().isoformat()
        
        # Load all servers from local registry (primary source)
        registry_servers = self.local_registry.list_servers()
        print(f"📦 Loading {len(registry_servers)} servers from local registry")
        for server_data in registry_servers:
            self._process_registry_server(server_data)
        
        # Load servers from custom registry JSON (secondary source)
        custom_servers = self._load_custom_registry_servers()
        print(f"📦 Loading {len(custom_servers)} servers from custom registry")
        for server_data in custom_servers:
            self._process_registry_server(server_data)
        
        # Add summary statistics
        self.generated_config["summary"] = {
            "total_servers": len(self.generated_config["servers"]),
            "total_tools": "Will be discovered dynamically",
            "total_env_vars": len(self.generated_config["environment_requirements"]),
            "categories": list(self.generated_config["categories"].keys())
        }
        
        return self.generated_config
    
    def save_generated_config(self, output_path: str = None):
        """Save generated configuration to JSON file"""
        if output_path is None:
            output_path = Path(__file__).parent / ".generated_mcp.json"
        
        config = self.generate_config()
        
        with open(output_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"\n✅ Generated configuration saved to: {output_path}")
        print(f"   📊 {config['summary']['total_servers']} servers from local + custom registry")
        print(f"   🛠️  {config['summary']['total_tools']} total tools")
        print(f"   🔑 {config['summary']['total_env_vars']} environment variables")
        
        return output_path
    
    def validate_environment(self) -> Dict[str, Any]:
        """Check which required environment variables are set"""
        config = self.generate_config()
        validation = {
            "missing": [],
            "present": [],
            "servers_ready": {},
            "servers_missing_env": {}
        }
        
        # Check each environment variable
        for env_var in config["environment_requirements"]:
            if os.getenv(env_var):
                validation["present"].append(env_var)
            else:
                validation["missing"].append(env_var)
        
        # Check each server's readiness
        for server_name, server_config in config["servers"].items():
            missing_env = []
            for env_var, env_details in server_config["environment"].items():
                if env_details.get("required", True) and not os.getenv(env_var):
                    missing_env.append(env_var)
            
            if missing_env:
                validation["servers_missing_env"][server_name] = missing_env
            else:
                validation["servers_ready"][server_name] = True
        
        return validation

if __name__ == "__main__":
    # Generate configuration when run directly
    generator = MCPConfigGenerator()
    generator.save_generated_config()
    
    # Validate environment
    print("\n🔍 Environment validation:")
    validation = generator.validate_environment()
    
    if validation["missing"]:
        print(f"   ⚠️  Missing environment variables: {', '.join(validation['missing'])}")
    else:
        print("   ✅ All environment variables are set!")
    
    if validation["servers_missing_env"]:
        print("\n   ❌ Servers missing environment variables:")
        for server, missing in validation["servers_missing_env"].items():
            print(f"      - {server}: {', '.join(missing)}")
    else:
        print("   ✅ All servers have required environment variables!")