# Adding Custom MCP Servers

Since the official MCP Registry is not yet available, you can add custom MCP servers to your local catalog.

## Method 1: Custom Registry File (Recommended)

Create a `custom_registry.json` file in the MCP catalog configs directory:

```bash
# Location: src/mcp_catalog_server/configs/custom_registry.json
```

### Example Custom Server

```json
{
  "my-api-server": {
    "id": "com.mycompany/my-api-server",
    "name": "my-api-server",
    "description": "Custom API integration server for internal services",
    "package": {
      "name": "@mycompany/mcp-api-server",
      "registry": "npm",
      "version": "1.2.0"
    },
    "config": {
      "env": {
        "API_BASE_URL": {
          "required": true,
          "description": "Base URL for the API (e.g., https://api.mycompany.com)"
        },
        "API_KEY": {
          "required": true,
          "description": "API key for authentication"
        },
        "API_TIMEOUT": {
          "required": false,
          "description": "Request timeout in milliseconds",
          "default": "30000"
        }
      },
      "args": []
    },
    "categories": ["api", "internal", "custom"],
    "repository": {
      "url": "https://github.com/mycompany/mcp-api-server",
      "source": "github"
    }
  }
}
```

### Server Configuration Schema

Each server entry should include:

- **id**: Unique identifier following DNS naming (e.g., `com.company/server-name`)
- **name**: Short name for the server
- **description**: Clear description of what the server does
- **package**: Package information
  - **name**: Package name in the registry
  - **registry**: One of `npm`, `pypi`, `docker`, etc.
  - **version**: Version to install
- **config**: Configuration requirements
  - **env**: Environment variables needed
    - Each variable can have:
      - **required**: Boolean indicating if mandatory
      - **description**: What the variable is for
      - **default**: Optional default value
  - **args**: Command line arguments (if any)
- **categories**: Array of category tags
- **repository**: Source code information
  - **url**: Repository URL
  - **source**: Usually `github`, `gitlab`, etc.

## Method 2: Python Package Servers

For Python-based MCP servers:

```json
{
  "my-python-server": {
    "id": "com.mycompany/my-python-server",
    "name": "my-python-server",
    "description": "Python-based MCP server",
    "package": {
      "name": "my-mcp-server",
      "registry": "pypi",
      "version": "0.1.0"
    },
    "config": {
      "env": {
        "PYTHON_SERVER_CONFIG": {
          "required": true,
          "description": "Path to configuration file"
        }
      },
      "args": []
    },
    "categories": ["python", "custom"],
    "runtime": "python"
  }
}
```

## Using Your Custom Servers

1. **Add to Registry**: Place your configuration in the appropriate location
2. **Enable in Config**: Add to your `claude_desktop_config.json`:
   ```json
   {
     "mcp-catalog": {
       "env": {
         "ENABLED_SERVERS": "github,my-custom-server,my-api-server"
       }
     }
   }
   ```
3. **Restart Claude**: Restart Claude Desktop to reload the configuration
4. **Use Tools**: Your custom server's tools will appear with the prefix `my-custom-server_toolname`

## Best Practices

1. **Namespace Properly**: Use reverse DNS notation for IDs (e.g., `com.company/server`)
2. **Document Environment**: Clearly describe all required environment variables
3. **Version Lock**: Specify exact versions for production use
4. **Test First**: Test your server independently before adding to the catalog
5. **Categories**: Use meaningful categories to help with discovery

## Common Issues

### Server Not Appearing
- Check that the server name is in `ENABLED_SERVERS`
- Verify JSON syntax is valid
- Ensure all required environment variables are set

### Tools Not Working
- Check server logs for connection issues
- Verify package name and version are correct
- Test the server runs independently with `npx` or `python -m`

### Environment Variables
- Set them in `claude_desktop_config.json` under the catalog's env section
- Use `${VARIABLE_NAME}` syntax to reference system environment variables

## Future Migration

When the official MCP Registry launches:
1. Your custom servers will continue to work locally
2. Consider publishing popular servers to the official registry
3. The catalog will automatically discover officially published versions
4. Local custom servers will take precedence over registry versions