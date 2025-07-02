"""
Copy-Paste Configuration Parser for MCP Server Configurations

Handles various MCP server configuration formats from claude_desktop_config.json
with robust error handling and validation.
"""

import json
import re
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from pydantic import BaseModel, Field, field_validator, ValidationError, PrivateAttr
from enum import Enum


class CommandType(str, Enum):
    """Supported MCP server command types"""
    NPX = "npx"
    PYTHON = "python"
    NODE = "node"
    CUSTOM = "custom"


class EnvironmentVariable(BaseModel):
    """Environment variable configuration"""
    name: str
    value: Optional[str] = None
    required: bool = True
    description: Optional[str] = None
    is_reference: bool = False  # True if value is like ${VAR_NAME}
    
    @field_validator('value', mode='before')
    def validate_env_reference(cls, v):
        if v and isinstance(v, str) and v.startswith('${') and v.endswith('}'):
            return v
        return v


class MCPServerConfig(BaseModel):
    """Validated MCP server configuration"""
    name: str
    command: str
    args: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)  # Store raw env dict
    command_type: CommandType = CommandType.CUSTOM
    package_name: Optional[str] = None
    description: Optional[str] = None
    _processed_env: Optional[Dict[str, EnvironmentVariable]] = PrivateAttr(default=None)
    
    @field_validator('command_type', mode='before')
    def determine_command_type(cls, v, info):
        command = info.data.get('command', '').lower()
        if command == 'npx':
            return CommandType.NPX
        elif command in ['python', 'python3']:
            return CommandType.PYTHON
        elif command in ['node', 'nodejs']:
            return CommandType.NODE
        return CommandType.CUSTOM
    
    @field_validator('package_name', mode='before')
    def extract_package_name(cls, v, info):
        if v:
            return v
        
        command = info.data.get('command', '').lower()
        args = info.data.get('args', [])
        
        if command == 'npx' and args:
            # Skip flags like -y, --yes, etc.
            for arg in args:
                if not arg.startswith('-'):
                    return arg
        
        return None
    
    def get_processed_env(self) -> Dict[str, EnvironmentVariable]:
        """Get processed environment variables with metadata"""
        if self._processed_env is None:
            self._processed_env = {}
            env_var_pattern = re.compile(r'\$\{([^}]+)\}')
            
            for key, value in self.env.items():
                if isinstance(value, str):
                    is_ref = bool(env_var_pattern.match(value))
                    self._processed_env[key] = EnvironmentVariable(
                        name=key,
                        value=value,
                        is_reference=is_ref
                    )
                elif isinstance(value, dict):
                    self._processed_env[key] = EnvironmentVariable(**value)
                else:
                    self._processed_env[key] = EnvironmentVariable(
                        name=key, 
                        value=str(value)
                    )
        
        return self._processed_env


class ConfigParserError(Exception):
    """Base exception for configuration parsing errors"""
    pass


class MalformedJSONError(ConfigParserError):
    """Raised when JSON is malformed"""
    def __init__(self, message: str, line: int = None, column: int = None):
        self.line = line
        self.column = column
        super().__init__(message)


class ConfigurationParser:
    """
    Robust parser for MCP server configurations with comprehensive error handling
    """
    
    def __init__(self):
        self.env_var_pattern = re.compile(r'\$\{([^}]+)\}')
        self.common_json_fixes = {
            # Fix trailing commas
            r',\s*}': '}',
            r',\s*]': ']',
            # Fix single quotes (carefully, avoiding strings with apostrophes)
            r"(?<![a-zA-Z])'([^']*)'(?![a-zA-Z])": r'"\1"',
        }
    
    def parse_config_paste(self, config_text: str) -> Dict[str, MCPServerConfig]:
        """
        Parse pasted configuration text and return validated server configs
        
        Args:
            config_text: Raw configuration text (potentially malformed JSON)
            
        Returns:
            Dictionary of server name -> MCPServerConfig
            
        Raises:
            MalformedJSONError: If JSON cannot be parsed after fixes
            ConfigParserError: For validation errors
        """
        # Attempt to fix common JSON issues
        fixed_text = self._fix_common_json_issues(config_text)
        
        # Try to parse JSON
        try:
            config_data = json.loads(fixed_text)
        except json.JSONDecodeError as e:
            # Provide helpful error message with location
            raise MalformedJSONError(
                f"Invalid JSON at line {e.lineno}, column {e.colno}: {e.msg}",
                line=e.lineno,
                column=e.colno
            )
        
        # Handle different configuration formats
        servers = self._extract_servers(config_data)
        
        # Validate and create server configs
        validated_servers = {}
        for name, server_data in servers.items():
            try:
                validated_servers[name] = self._validate_server_config(name, server_data)
            except ValidationError as e:
                raise ConfigParserError(
                    f"Invalid configuration for server '{name}': {self._format_validation_errors(e)}"
                )
        
        return validated_servers
    
    def _fix_common_json_issues(self, text: str) -> str:
        """Apply common JSON fixes to make parsing more forgiving"""
        fixed = text
        
        # Apply regex fixes
        for pattern, replacement in self.common_json_fixes.items():
            fixed = re.sub(pattern, replacement, fixed)
        
        # Handle missing quotes around keys (more complex)
        # This is a simplified approach - a full parser would be more robust
        lines = fixed.split('\n')
        fixed_lines = []
        in_string = False
        
        for line in lines:
            # Skip comment lines
            if line.strip().startswith('//'):
                fixed_lines.append(line)
                continue
                
            # Look for unquoted keys (word followed by colon)
            # Only fix if we're sure it's a key
            match = re.match(r'^(\s*)([a-zA-Z_]\w*)\s*:\s*(.*)$', line)
            if match:
                indent = match.group(1)
                key = match.group(2)
                rest = match.group(3)
                # Check if key is already quoted
                if not (f'"{key}"' in line or f"'{key}'" in line):
                    line = f'{indent}"{key}": {rest}'
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def _extract_servers(self, config_data: Any) -> Dict[str, Dict]:
        """Extract server configurations from various formats"""
        servers = {}
        
        # Case 1: Full claude_desktop_config.json format
        if isinstance(config_data, dict) and 'mcpServers' in config_data:
            servers = config_data['mcpServers']
        
        # Case 2: Direct server dictionary
        elif isinstance(config_data, dict):
            # Check if this looks like a single server config
            if 'command' in config_data:
                # Single server without name
                servers['unnamed_server'] = config_data
            else:
                # Multiple servers
                servers = config_data
        
        # Case 3: Array of server configs (non-standard but handle it)
        elif isinstance(config_data, list):
            for i, server in enumerate(config_data):
                name = server.get('name', f'server_{i}')
                servers[name] = server
        
        else:
            raise ConfigParserError(
                "Unrecognized configuration format. Expected object with 'mcpServers' or direct server configuration."
            )
        
        return servers
    
    def _validate_server_config(self, name: str, server_data: Dict) -> MCPServerConfig:
        """Validate and enhance server configuration"""
        # Create validated config
        config = MCPServerConfig(
            name=name,
            command=server_data.get('command', ''),
            args=server_data.get('args', []),
            env=server_data.get('env', {})
        )
        
        # Add description based on known packages
        config.description = self._generate_description(config)
        
        return config
    
    def _generate_description(self, config: MCPServerConfig) -> str:
        """Generate description based on package name or command"""
        known_packages = {
            '@modelcontextprotocol/server-github': 'GitHub repository management and operations',
            '@modelcontextprotocol/server-postgres': 'PostgreSQL database integration',
            '@modelcontextprotocol/server-filesystem': 'Local filesystem operations',
            'task-master-ai': 'AI-powered task and project management',
            'server-perplexity-ask': 'Perplexity AI web search and research',
            '@modelcontextprotocol/server-sequential-thinking': 'Sequential thinking for complex problem solving',
            '@upstash/context7-mcp': 'Context7 library documentation retrieval',
        }
        
        if config.package_name and config.package_name in known_packages:
            return known_packages[config.package_name]
        
        # Generate generic description
        if config.command_type == CommandType.NPX:
            return f"NPX-based MCP server: {config.package_name or 'unknown package'}"
        elif config.command_type == CommandType.PYTHON:
            return f"Python MCP server: {config.args[0] if config.args else 'unknown script'}"
        
        return "Custom MCP server"
    
    def _format_validation_errors(self, error: ValidationError) -> str:
        """Format Pydantic validation errors into readable messages"""
        messages = []
        for err in error.errors():
            field = ' -> '.join(str(x) for x in err['loc'])
            messages.append(f"{field}: {err['msg']}")
        return '; '.join(messages)
    
    def extract_required_env_vars(self, config: MCPServerConfig) -> List[str]:
        """Extract list of required environment variables"""
        required = []
        processed_env = config.get_processed_env()
        
        for var in processed_env.values():
            if var.required and var.is_reference:
                # Extract variable name from ${VAR_NAME}
                match = self.env_var_pattern.match(var.value)
                if match:
                    required.append(match.group(1))
        return required
    
    def generate_yaml_config(self, config: MCPServerConfig) -> Dict[str, Any]:
        """Generate YAML-compatible configuration dictionary"""
        yaml_config = {
            'name': config.name,
            'description': config.description,
            'category': 'community',  # Default to community
        }
        
        # Package configuration
        if config.command_type == CommandType.NPX:
            yaml_config['package'] = {
                'type': 'npx',
                'name': config.package_name or config.args[0] if config.args else 'unknown',
                'args': config.args[1:] if len(config.args) > 1 else []
            }
        elif config.command_type == CommandType.PYTHON:
            yaml_config['package'] = {
                'type': 'python',
                'script': config.args[0] if config.args else 'unknown.py',
                'args': config.args[1:] if len(config.args) > 1 else []
            }
        else:
            yaml_config['package'] = {
                'type': 'custom',
                'command': config.command,
                'args': config.args
            }
        
        # Environment variables
        if config.env:
            yaml_config['environment'] = {}
            processed_env = config.get_processed_env()
            
            for key, var in processed_env.items():
                yaml_config['environment'][key] = {
                    'required': var.required,
                    'description': var.description or f"Environment variable: {key}"
                }
                if not var.is_reference and var.value:
                    yaml_config['environment'][key]['default'] = var.value
        
        return yaml_config


# Convenience functions for common operations
def parse_mcp_config(config_text: str) -> Dict[str, MCPServerConfig]:
    """Parse MCP configuration text"""
    parser = ConfigurationParser()
    return parser.parse_config_paste(config_text)


def validate_single_server(server_data: Dict, name: str = "server") -> MCPServerConfig:
    """Validate a single server configuration"""
    parser = ConfigurationParser()
    return parser._validate_server_config(name, server_data)