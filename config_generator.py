"""
MCP Configuration Generator

Reads YAML configuration files for MCP servers and generates
a unified .generated_mcp.json configuration file with all details.
"""

import yaml
import json
import os
from pathlib import Path
from typing import Dict, List, Any

class MCPConfigGenerator:
    """Generates unified MCP configuration from YAML files"""
    
    def __init__(self, config_dir: str = None):
        """Initialize with configuration directory"""
        if config_dir is None:
            config_dir = Path(__file__).parent / "configs"
        self.config_dir = Path(config_dir)
        self.generated_config = {
            "version": "1.0.0",
            "generated_at": None,
            "servers": {},
            "environment_requirements": {},
            "categories": {}
        }
    
    def load_yaml_configs(self) -> Dict[str, Dict[str, Any]]:
        """Load all YAML configuration files"""
        configs = {}
        
        for yaml_file in self.config_dir.glob("*.yaml"):
            try:
                with open(yaml_file, 'r') as f:
                    config = yaml.safe_load(f)
                    server_name = config.get('name', yaml_file.stem)
                    configs[server_name] = config
                    print(f"✅ Loaded config: {server_name} from {yaml_file.name}")
            except Exception as e:
                print(f"❌ Failed to load {yaml_file}: {e}")
        
        return configs
    
    def generate_config(self) -> Dict[str, Any]:
        """Generate unified configuration from YAML files"""
        from datetime import datetime
        
        configs = self.load_yaml_configs()
        self.generated_config["generated_at"] = datetime.now().isoformat()
        
        for server_name, config in configs.items():
            # Build server entry
            server_entry = {
                "name": server_name,
                "description": config.get("description", ""),
                "category": config.get("category", "official"),
                "version": config.get("version", "latest"),
                "package": config.get("package"),
                "execution": config.get("execution", {}),
                "environment": {},
                "tools": config.get("tools", []),
                "metadata": config.get("metadata", {})
            }
            
            # Process environment variables
            env_config = config.get("environment", {})
            for env_var, env_details in env_config.items():
                server_entry["environment"][env_var] = env_details
                
                # Track global environment requirements
                if env_var not in self.generated_config["environment_requirements"]:
                    self.generated_config["environment_requirements"][env_var] = {
                        "required_by": [],
                        "description": env_details.get("description", ""),
                        "example": env_details.get("example", "")
                    }
                self.generated_config["environment_requirements"][env_var]["required_by"].append(server_name)
            
            # Add to servers
            self.generated_config["servers"][server_name] = server_entry
            
            # Track categories
            category = config.get("category", "official")
            if category not in self.generated_config["categories"]:
                self.generated_config["categories"][category] = []
            self.generated_config["categories"][category].append(server_name)
        
        # Add summary statistics
        self.generated_config["summary"] = {
            "total_servers": len(self.generated_config["servers"]),
            "total_tools": sum(len(s["tools"]) for s in self.generated_config["servers"].values()),
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
        print(f"   📊 {config['summary']['total_servers']} servers")
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