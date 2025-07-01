"""
MCP Catalog Server - Dynamic Model Context Protocol server wrapper.

This package provides a universal catalog server for MCP (Model Context Protocol)
that dynamically discovers and exposes tools from multiple configured servers.
"""

__version__ = "0.1.0"
__author__ = "Knowledge Graph Engine Team"

from .server import MCPCatalogServer
from .config import CatalogConfig
from .dynamic_registry import DynamicToolRegistry

__all__ = [
    "MCPCatalogServer",
    "CatalogConfig", 
    "DynamicToolRegistry",
    "__version__",
]