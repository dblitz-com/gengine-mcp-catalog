"""
Entry point for running MCP Catalog Server as a module.

Usage:
    python -m mcp_catalog_server [options]
"""

from .cli import main

if __name__ == "__main__":
    main()