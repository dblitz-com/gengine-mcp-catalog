# MCP Catalog Server

A dynamic catalog server for Model Context Protocol (MCP) that acts as a universal wrapper, automatically discovering and exposing tools from multiple configured MCP servers through a single entry point.

## Features

- 🔍 **Dynamic Tool Discovery**: Automatically discovers tools from configured MCP servers
- 🚀 **Single Entry Point**: Replace all individual MCP server entries with one catalog
- 🔧 **Meta Tools**: Built-in tools for server discovery and management
- 📦 **Multiple Installation Methods**: pip, uvx, Docker, or source
- ⚙️ **Smart Configuration**: Hierarchical config with environment variables and auto-discovery
- 🐳 **Production Ready**: Docker support for enterprise deployments

## Quick Start

### Install via pip

```bash
pip install mcp-catalog-server
```

### Install via uvx (zero-install)

```bash
uvx mcp-catalog-server serve
```

### Initialize Configuration

```bash
mcp-catalog-server init
```

This creates a `~/.mcp/` directory with:
- `config.json` - Main configuration
- `.env` - Environment variables for API keys
- `configs/` - YAML files for MCP servers

### Add MCP Servers

Create YAML files in `~/.mcp/configs/` for each MCP server. Example:

```yaml
# ~/.mcp/configs/github.yaml
name: github
description: "GitHub API integration for MCP"
type: npx
command: "@modelcontextprotocol/server-github"
env:
  GITHUB_TOKEN: "${GITHUB_TOKEN}"
metadata:
  author: "Anthropic"
  version: "latest"
```

### Start the Server

```bash
mcp-catalog-server serve
```

## Configuration

### Configuration Hierarchy

Configuration is loaded from multiple sources (highest to lowest priority):

1. Command-line arguments
2. Environment variables (`MCP_CATALOG_*`)
3. User config (`~/.mcp/config.json`)
4. Project config (`.mcp.json` in current directory)
5. Built-in defaults

### Environment Variables

```bash
# Server configuration
export MCP_CATALOG_HOST=localhost
export MCP_CATALOG_PORT=3000
export MCP_CATALOG_LOG_LEVEL=INFO

# Python configuration
export MCP_CATALOG_PYTHON=/path/to/python

# Auto-discovery
export MCP_CATALOG_AUTO_DISCOVER=true
```

### Example Configuration

```json
{
  "server": {
    "host": "localhost",
    "port": 3000,
    "log_level": "INFO"
  },
  "paths": {
    "configs": "~/.mcp/configs",
    "logs": "~/.mcp/logs",
    "cache": "~/.mcp/cache"
  },
  "discovery": {
    "auto_discover": true,
    "scan_paths": [
      "~/.mcp/servers",
      "/usr/local/share/mcp-servers"
    ]
  }
}
```

## Docker Deployment

### Using Docker

```bash
docker run -p 3000:3000 \
  -v ~/.mcp:/root/.mcp \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  mcp-catalog-server
```

### Using Docker Compose

```yaml
version: '3.8'
services:
  mcp-catalog:
    image: mcp-catalog-server
    ports:
      - "3000:3000"
    volumes:
      - ~/.mcp:/root/.mcp
    env_file:
      - .env
```

## CLI Commands

### List Available Servers

```bash
mcp-catalog-server list
mcp-catalog-server list --format json
```

### Check Server Configuration

```bash
mcp-catalog-server check github
```

### Show Current Configuration

```bash
mcp-catalog-server config
mcp-catalog-server config --sources  # Show where each value comes from
```

## Meta Tools

The catalog server provides built-in tools for management:

- `list_available_servers()` - List all configured MCP servers
- `check_server_requirements(server_name)` - Check environment requirements
- `list_all_tools()` - Browse all available tools
- `search_tools(query)` - Search for tools by keyword
- `get_tool_details(tool_name)` - Get detailed tool documentation
- `refresh_configuration()` - Reload configuration from YAML files

## Development

### Install from Source

```bash
git clone https://github.com/yourusername/mcp-catalog-server
cd mcp-catalog-server
pip install -e .
```

### Run Tests

```bash
pytest tests/
```

## Migration from Local Setup

If you're currently using local paths in your `.mcp.json`:

1. Install the package: `pip install mcp-catalog-server`
2. Initialize config: `mcp-catalog-server init`
3. Copy your server YAML files to `~/.mcp/configs/`
4. Update your Claude Desktop config to use the catalog server
5. Remove individual server entries

## License

MIT License - see LICENSE file for details.