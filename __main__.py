"""
Entry point for running MCP Catalog Server as a module.

Usage:
    python -m mcp_catalog_server [options]    # CLI mode
    python -m mcp_catalog_server              # MCP server mode (for Claude Desktop)
"""

import sys

if __name__ == "__main__":
    # If no arguments provided, run as MCP server
    if len(sys.argv) == 1:
        from .main import mcp
        mcp.run()
    else:
        # Otherwise use CLI interface
        from .cli import main
        main()