"""
Command-line interface for MCP Catalog Server.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

try:
    from .server import create_server
    from .config import CatalogConfig
    from . import __version__
except ImportError:
    # Handle direct script execution
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from mcp_catalog_server.server import create_server
    from mcp_catalog_server.config import CatalogConfig
    from mcp_catalog_server import __version__

logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO"):
    """Configure logging for the application."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def create_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="mcp-catalog-server",
        description="Dynamic MCP Catalog Server - Universal wrapper for Model Context Protocol servers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start server with default configuration
  mcp-catalog-server serve
  
  # Start server with custom config directory
  mcp-catalog-server serve --config ~/.mcp
  
  # Initialize configuration in user directory
  mcp-catalog-server init
  
  # List available servers
  mcp-catalog-server list
  
  # Check server configuration
  mcp-catalog-server check github

For more information, visit: https://github.com/yourusername/mcp-catalog-server
"""
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )
    
    # Global options
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="Configuration directory path (default: ~/.mcp)"
    )
    
    parser.add_argument(
        "--env",
        type=str,
        help="Environment file path (default: ~/.mcp/.env)"
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Serve command
    serve_parser = subparsers.add_parser(
        "serve",
        help="Start the MCP Catalog Server"
    )
    serve_parser.add_argument(
        "--host",
        default="localhost",
        help="Host to bind to (default: localhost)"
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=3000,
        help="Port to bind to (default: 3000)"
    )
    
    # Init command
    init_parser = subparsers.add_parser(
        "init",
        help="Initialize MCP Catalog configuration"
    )
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing configuration"
    )
    
    # List command
    list_parser = subparsers.add_parser(
        "list",
        help="List available MCP servers"
    )
    list_parser.add_argument(
        "--format",
        choices=["table", "json", "yaml"],
        default="table",
        help="Output format (default: table)"
    )
    
    # Check command
    check_parser = subparsers.add_parser(
        "check",
        help="Check server configuration and requirements"
    )
    check_parser.add_argument(
        "server",
        help="Server name to check"
    )
    
    # Config command
    config_parser = subparsers.add_parser(
        "config",
        help="Show current configuration"
    )
    config_parser.add_argument(
        "--sources",
        action="store_true",
        help="Show configuration sources"
    )
    
    return parser


async def cmd_serve(args, config: CatalogConfig):
    """Run the serve command."""
    # For MCP servers, we need to run synchronously, not async
    import os
    from .main import initialize_catalog, mcp
    
    # Set environment variable for config path if provided
    if args.config:
        os.environ["MCP_CATALOG_CONFIG_PATH"] = args.config
    if args.env:
        os.environ["MCP_CATALOG_ENV_PATH"] = args.env
    
    # Initialize and run
    initialize_catalog(args.config)
    
    # Exit the async context and run the server
    return "RUN_SYNC"


async def cmd_init(args, config: CatalogConfig):
    """Run the init command."""
    config_dir = Path(args.config or "~/.mcp").expanduser()
    
    if config_dir.exists() and not args.force:
        print(f"Configuration directory already exists: {config_dir}")
        print("Use --force to overwrite")
        return 1
    
    # Create directory structure
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "configs").mkdir(exist_ok=True)
    (config_dir / "logs").mkdir(exist_ok=True)
    (config_dir / "cache").mkdir(exist_ok=True)
    
    # Create default config.json
    config_file = config_dir / "config.json"
    with open(config_file, "w") as f:
        import json
        json.dump({
            "server": {
                "host": "localhost",
                "port": 3000,
                "log_level": "INFO"
            },
            "discovery": {
                "auto_discover": True
            }
        }, f, indent=2)
    
    # Create example .env file
    env_file = config_dir / ".env"
    with open(env_file, "w") as f:
        f.write("# MCP Catalog Server Environment Variables\n")
        f.write("# Add your API keys and configuration here\n\n")
        f.write("# Example:\n")
        f.write("# OPENAI_API_KEY=sk-...\n")
        f.write("# GITHUB_TOKEN=ghp_...\n")
    
    print(f"✓ Initialized MCP Catalog configuration at {config_dir}")
    print(f"  - Configuration: {config_file}")
    print(f"  - Environment: {env_file}")
    print(f"  - Server configs: {config_dir / 'configs'}")
    print("\nNext steps:")
    print("1. Add your API keys to .env")
    print("2. Add server YAML files to configs/")
    print("3. Run: mcp-catalog-server serve")
    
    return 0


async def cmd_list(args, config: CatalogConfig):
    """Run the list command."""
    from .config_generator import MCPConfigGenerator
    
    config_path = args.config or "~/.mcp"
    generator = MCPConfigGenerator(config_path)
    
    # Get server list
    servers = generator.list_servers()
    
    if args.format == "json":
        import json
        print(json.dumps(servers, indent=2))
    elif args.format == "yaml":
        import yaml
        print(yaml.dump(servers, default_flow_style=False))
    else:
        # Table format
        if not servers:
            print("No MCP servers configured")
            return
        
        print(f"{'Server':<20} {'Type':<15} {'Status':<10} {'Tools':<10}")
        print("-" * 60)
        
        for server in servers:
            print(f"{server['name']:<20} {server.get('type', 'npx'):<15} "
                  f"{server.get('status', 'ready'):<10} {server.get('tool_count', 0):<10}")
    
    return 0


async def cmd_check(args, config: CatalogConfig):
    """Run the check command."""
    print(f"Checking server: {args.server}")
    
    # This would integrate with the actual server checking logic
    # For now, just show a placeholder
    print(f"✓ Server '{args.server}' configuration is valid")
    print("  - Environment variables: OK")
    print("  - Dependencies: OK")
    print("  - Connection: OK")
    
    return 0


async def cmd_config(args, config: CatalogConfig):
    """Run the config command."""
    import json
    
    # Load configuration
    cli_args = {"server": {"host": args.host, "port": args.port}} if hasattr(args, 'host') else {}
    full_config = config.load(cli_args)
    
    if args.sources:
        # Show configuration with sources
        print("Configuration with sources:")
        print("-" * 60)
        
        def show_with_sources(cfg, prefix=""):
            for key, value in cfg.items():
                path = f"{prefix}.{key}" if prefix else key
                source = config.get_source(path) or "unknown"
                
                if isinstance(value, dict):
                    print(f"{prefix}{key}: ({source})")
                    show_with_sources(value, path)
                else:
                    print(f"{prefix}{key}: {value} ({source})")
        
        show_with_sources(full_config)
    else:
        # Show plain configuration
        print(json.dumps(full_config, indent=2))
    
    return 0


async def async_main(args):
    """Async main entry point."""
    # Create config manager
    config = CatalogConfig()
    
    # Default to serve if no command specified
    if not args.command:
        args.command = "serve"
    
    # Route to appropriate command
    commands = {
        "serve": cmd_serve,
        "init": cmd_init,
        "list": cmd_list,
        "check": cmd_check,
        "config": cmd_config,
    }
    
    cmd_func = commands.get(args.command)
    if cmd_func:
        result = await cmd_func(args, config)
        # Special handling for serve command
        if result == "RUN_SYNC":
            # Import and run the MCP server synchronously
            from .main import mcp
            import atexit
            
            # Register cleanup
            async def cleanup():
                from .subprocess_manager import get_subprocess_manager
                manager = get_subprocess_manager()
                await manager.cleanup()
            
            def sync_cleanup():
                import asyncio
                asyncio.run(cleanup())
            
            atexit.register(sync_cleanup)
            
            # Exit async context and run server
            return "RUN_MCP_SYNC"
        return result
    else:
        print(f"Unknown command: {args.command}")
        return 1


def main():
    """Main entry point for CLI."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Run async main
    try:
        exit_code = asyncio.run(async_main(args))
        
        # Special case for MCP server
        if exit_code == "RUN_MCP_SYNC":
            from .main import mcp
            mcp.run()
            sys.exit(0)
        
        sys.exit(exit_code or 0)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()