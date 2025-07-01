"""
Configuration management for MCP Catalog Server.

Handles configuration from multiple sources:
1. Command-line arguments
2. Environment variables
3. ~/.mcp/config.json
4. Project-local .mcp.json
5. Smart defaults
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class CatalogConfig:
    """Manages configuration for MCP Catalog Server."""
    
    # Configuration priority (highest to lowest)
    CONFIG_SOURCES = [
        "cli",         # Command-line arguments
        "env",         # Environment variables
        "user",        # ~/.mcp/config.json
        "project",     # .mcp.json in current directory
        "defaults",    # Built-in defaults
    ]
    
    # Default configuration
    DEFAULTS = {
        "server": {
            "host": "localhost",
            "port": 3000,
            "log_level": "INFO",
        },
        "paths": {
            "configs": "~/.mcp/configs",
            "logs": "~/.mcp/logs",
            "cache": "~/.mcp/cache",
        },
        "discovery": {
            "auto_discover": True,
            "scan_paths": [
                "~/.mcp/servers",
                "/usr/local/share/mcp-servers",
                "/opt/mcp-servers",
            ],
        },
        "subprocess": {
            "timeout": 30,
            "max_retries": 3,
            "health_check_interval": 60,
        },
    }
    
    def __init__(self):
        """Initialize configuration manager."""
        self._config = {}
        self._sources = {}  # Track which source each config came from
        
    def load(self, cli_args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Load configuration from all sources.
        
        Args:
            cli_args: Command-line arguments override
            
        Returns:
            Merged configuration dictionary
        """
        # Start with defaults
        self._config = self._deep_copy(self.DEFAULTS)
        self._track_source(self._config, "defaults")
        
        # Load project-local config
        project_config = self._load_project_config()
        if project_config:
            self._merge_config(project_config, "project")
        
        # Load user config
        user_config = self._load_user_config()
        if user_config:
            self._merge_config(user_config, "user")
        
        # Load environment variables
        env_config = self._load_env_config()
        if env_config:
            self._merge_config(env_config, "env")
        
        # Apply CLI arguments last (highest priority)
        if cli_args:
            self._merge_config(cli_args, "cli")
        
        # Expand paths
        self._expand_paths()
        
        # Auto-discover Python environment
        self._auto_discover_python()
        
        return self._config
    
    def _load_project_config(self) -> Optional[Dict[str, Any]]:
        """Load .mcp.json from current directory."""
        project_file = Path.cwd() / ".mcp.json"
        if project_file.exists():
            try:
                with open(project_file) as f:
                    config = json.load(f)
                logger.info(f"Loaded project config from {project_file}")
                return config
            except Exception as e:
                logger.warning(f"Failed to load project config: {e}")
        return None
    
    def _load_user_config(self) -> Optional[Dict[str, Any]]:
        """Load ~/.mcp/config.json."""
        user_file = Path.home() / ".mcp" / "config.json"
        if user_file.exists():
            try:
                with open(user_file) as f:
                    config = json.load(f)
                logger.info(f"Loaded user config from {user_file}")
                return config
            except Exception as e:
                logger.warning(f"Failed to load user config: {e}")
        return None
    
    def _load_env_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        config = {}
        
        # Map environment variables to config paths
        env_mapping = {
            "MCP_CATALOG_HOST": ["server", "host"],
            "MCP_CATALOG_PORT": ["server", "port"],
            "MCP_CATALOG_LOG_LEVEL": ["server", "log_level"],
            "MCP_CATALOG_CONFIG_PATH": ["paths", "configs"],
            "MCP_CATALOG_AUTO_DISCOVER": ["discovery", "auto_discover"],
            "MCP_CATALOG_PYTHON": ["python", "executable"],
        }
        
        for env_var, config_path in env_mapping.items():
            value = os.environ.get(env_var)
            if value is not None:
                # Convert types as needed
                if env_var == "MCP_CATALOG_PORT":
                    value = int(value)
                elif env_var == "MCP_CATALOG_AUTO_DISCOVER":
                    value = value.lower() in ("true", "1", "yes")
                
                # Set nested config value
                self._set_nested(config, config_path, value)
        
        return config
    
    def _merge_config(self, new_config: Dict[str, Any], source: str):
        """Merge new configuration with existing, tracking sources."""
        self._deep_merge(self._config, new_config, source)
    
    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any], source: str):
        """Deep merge update into base, tracking source."""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value, source)
            else:
                base[key] = value
                self._sources[self._get_path(base, key)] = source
    
    def _expand_paths(self):
        """Expand ~ and environment variables in paths."""
        paths = self._config.get("paths", {})
        for key, path in paths.items():
            if isinstance(path, str):
                paths[key] = os.path.expanduser(os.path.expandvars(path))
        
        # Also expand discovery scan paths
        discovery = self._config.get("discovery", {})
        scan_paths = discovery.get("scan_paths", [])
        discovery["scan_paths"] = [
            os.path.expanduser(os.path.expandvars(p))
            for p in scan_paths
        ]
    
    def _auto_discover_python(self):
        """Auto-discover Python executable if not specified."""
        if "python" not in self._config:
            self._config["python"] = {}
        
        if "executable" not in self._config["python"]:
            # Try to find Python in virtual environment first
            venv_python = self._find_venv_python()
            if venv_python:
                self._config["python"]["executable"] = str(venv_python)
                self._sources["python.executable"] = "auto-discovery"
            else:
                # Fall back to system Python
                self._config["python"]["executable"] = sys.executable
                self._sources["python.executable"] = "auto-discovery"
    
    def _find_venv_python(self) -> Optional[Path]:
        """Find Python executable in virtual environment."""
        # Check VIRTUAL_ENV environment variable
        venv = os.environ.get("VIRTUAL_ENV")
        if venv:
            venv_path = Path(venv)
            if sys.platform == "win32":
                python = venv_path / "Scripts" / "python.exe"
            else:
                python = venv_path / "bin" / "python"
            
            if python.exists():
                return python
        
        # Check common virtual environment locations
        cwd = Path.cwd()
        for venv_name in ["venv", ".venv", "env", ".env"]:
            venv_path = cwd / venv_name
            if venv_path.exists():
                if sys.platform == "win32":
                    python = venv_path / "Scripts" / "python.exe"
                else:
                    python = venv_path / "bin" / "python"
                
                if python.exists():
                    return python
        
        return None
    
    def _deep_copy(self, obj: Any) -> Any:
        """Deep copy a configuration object."""
        if isinstance(obj, dict):
            return {k: self._deep_copy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_copy(v) for v in obj]
        else:
            return obj
    
    def _set_nested(self, config: Dict[str, Any], path: List[str], value: Any):
        """Set a nested configuration value."""
        current = config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value
    
    def _get_path(self, obj: Dict[str, Any], key: str) -> str:
        """Get the full path to a configuration key."""
        # This is simplified - in production would track full paths
        return key
    
    def _track_source(self, config: Dict[str, Any], source: str, prefix: str = ""):
        """Track the source of all configuration values."""
        for key, value in config.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                self._track_source(value, source, path)
            else:
                self._sources[path] = source
    
    def get(self, path: str, default: Any = None) -> Any:
        """
        Get a configuration value by path.
        
        Args:
            path: Dot-separated path (e.g., "server.port")
            default: Default value if not found
            
        Returns:
            Configuration value
        """
        parts = path.split(".")
        current = self._config
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        
        return current
    
    def get_source(self, path: str) -> Optional[str]:
        """Get the source of a configuration value."""
        return self._sources.get(path)
    
    def to_dict(self) -> Dict[str, Any]:
        """Get the full configuration as a dictionary."""
        return self._deep_copy(self._config)