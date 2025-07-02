# MCP Catalog Registry Status

## Current Implementation

As of December 2024, the MCP Catalog Server uses a **local registry** approach for discovering and managing MCP servers. This is a temporary solution until the official MCP Registry API becomes publicly available.

## Official Registry Status

The official MCP Registry (https://registry.modelcontextprotocol.io) is:
- ✅ **In active development** at https://github.com/modelcontextprotocol/registry
- ❌ **NOT publicly accessible** - API endpoints return timeouts/errors
- 🔄 **Coming soon** - Expected to launch after initial development sprint

## Our Local Registry Approach

### What We Have

We maintain a curated list of known MCP servers in `local_registry.py`:

```python
KNOWN_SERVERS = {
    "filesystem": {...},      # Official - File system operations
    "github": {...},          # Official - GitHub API integration  
    "postgres": {...},        # Official - PostgreSQL operations
    "brave-search": {...},    # Official - Brave Search API
    "memory": {...},          # Official - Persistent memory/knowledge graph
    "puppeteer": {...},       # Official - Browser automation
    "slack": {...},           # Official - Slack workspace integration
    "gitlab": {...},          # Official - GitLab API integration
    "google-maps": {...},     # Official - Google Maps API
    "aws-kb-retrieval": {...} # Official - AWS Knowledge Base
}
```

### Limitations

1. **Limited Server Selection**
   - Only 10 pre-configured servers (vs thousands in the ecosystem)
   - Manual curation required for new servers
   - No automatic discovery of community servers

2. **No Version Updates**
   - Can't check for new versions automatically
   - Must manually update package versions
   - No notification of security updates

3. **No Community Submissions**
   - Can't publish new servers to a central registry
   - No standardized discovery mechanism
   - Each MCP client maintains their own list

### Adding Custom Servers

Users can extend the local registry by creating `custom_registry.json`:

```json
{
  "my-custom-server": {
    "id": "com.mycompany/my-custom-server",
    "name": "my-custom-server",
    "description": "My custom MCP server",
    "package": {
      "name": "@mycompany/mcp-server",
      "registry": "npm",
      "version": "1.0.0"
    },
    "config": {
      "env": {
        "API_KEY": {
          "required": true,
          "description": "API key for authentication"
        }
      }
    },
    "categories": ["custom", "internal"]
  }
}
```

## Stateless Configuration

Following MCP best practices and the official registry design, our catalog is completely stateless:

### Environment Variables

Configure in `claude_desktop_config.json`:

```json
{
  "mcp-catalog": {
    "command": "python",
    "args": ["-m", "mcp_catalog_server"],
    "env": {
      // Filter which servers are available
      "ENABLED_SERVERS": "github,taskmaster-ai,perplexity-ask",
      
      // Disable specific tools by pattern
      "DISABLED_TOOLS": "github:delete_*,taskmaster:debug_*",
      
      // Required credentials
      "GITHUB_TOKEN": "${GITHUB_TOKEN}",
      "OPENAI_API_KEY": "${OPENAI_API_KEY}",
      // ... other API keys
    }
  }
}
```

### Available Tools

Our catalog provides these discovery and configuration tools:

1. **browse_official_registry()** - Browse servers in local registry
2. **add_server_from_registry()** - Add server configuration from local registry
3. **suggest_enable_servers()** - Generate config to enable specific servers
4. **suggest_disable_tools()** - Generate config to disable specific tools
5. **get_server_configuration()** - View current configuration

## Future Integration

When the official registry launches, we'll update our implementation to:

1. **Fetch from API**: Replace local data with API calls to registry.modelcontextprotocol.io
2. **Cache responses**: Implement 15-minute caching as specified
3. **Daily polling**: Set up daily synchronization for new servers
4. **Version tracking**: Check for updates to installed servers

The transition will be seamless because:
- Our API mirrors the expected registry structure
- Configuration remains in environment variables
- Tool interfaces won't change

## Comparison with Official Design

| Feature | Official Registry (Future) | Our Local Registry (Now) |
|---------|---------------------------|-------------------------|
| Server Count | Thousands | 10 + custom |
| Discovery | REST API | Local file |
| Updates | Daily polling | Manual |
| Publishing | GitHub OAuth + CLI | Edit custom_registry.json |
| Namespacing | DNS-based (io.github.user/server) | Following same convention |
| Caching | 15-minute cache | N/A (local file) |
| Authentication | Not required for read | N/A |

## Recommendations for Users

1. **Start with official servers** - The 10 pre-configured servers cover most common use cases
2. **Add custom servers carefully** - Test thoroughly before adding to production
3. **Monitor for registry launch** - Check https://github.com/modelcontextprotocol/registry for updates
4. **Use environment variables** - Configure filtering via ENABLED_SERVERS and DISABLED_TOOLS
5. **Contribute upstream** - Consider submitting your servers to the official registry when it launches

## Summary

Our local registry is a pragmatic solution that:
- ✅ Provides immediate value with curated servers
- ✅ Follows official registry design principles  
- ✅ Allows custom server additions
- ✅ Ready for seamless transition when official API launches
- ❌ Limited to manual curation
- ❌ No automatic updates or version management
- ❌ No community discovery features

This approach balances functionality with simplicity while we await the official registry launch.