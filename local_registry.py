"""
Local MCP Server Registry

Since the official registry requires running a separate service,
this module provides a local registry of known MCP servers that
can be expanded over time.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Known MCP servers with their configurations
KNOWN_SERVERS = {
    "context7": {
        "id": "io.upstash/context7-mcp",
        "name": "context7",
        "description": "Context7 for library documentation, code context, and package resolution",
        "package": {
            "name": "@upstash/context7-mcp",
            "registry": "npm",
            "version": "latest"
        },
        "config": {
            "env": {},
            "args": []
        },
        "categories": ["documentation", "knowledge-management", "official"],
        "repository": {
            "url": "https://context7.com/",
            "source": "website"
        }
    },
    "perplexity-ask": {
        "id": "io.modelcontextprotocol.servers/perplexity-ask",
        "name": "perplexity-ask",
        "description": "Perplexity AI integration for web search, research, and real-time information",
        "package": {
            "name": "server-perplexity-ask",
            "registry": "npm",
            "version": "latest"
        },
        "config": {
            "env": {
                "PERPLEXITY_API_KEY": {
                    "required": True,
                    "description": "Perplexity API key for AI-powered search"
                }
            },
            "args": []
        },
        "categories": ["search", "ai", "research", "official"],
        "repository": {
            "url": "https://docs.perplexity.ai/",
            "source": "documentation"
        }
    },
    "sequential-thinking": {
        "id": "io.modelcontextprotocol.servers/sequential-thinking",
        "name": "sequential-thinking",
        "description": "Sequential thinking tool for complex problem solving and multi-step analysis",
        "package": {
            "name": "@modelcontextprotocol/server-sequential-thinking",
            "registry": "npm",
            "version": "latest"
        },
        "config": {
            "env": {},
            "args": []
        },
        "categories": ["problem-solving", "analysis", "official"],
        "repository": {
            "url": "https://github.com/modelcontextprotocol/servers/tree/main/src/sequential-thinking",
            "source": "github"
        }
    },
    "taskmaster-ai": {
        "id": "io.taskmaster/taskmaster-ai",
        "name": "taskmaster-ai",
        "description": "TaskMaster AI for project management, task automation, and AI-powered research",
        "package": {
            "name": "task-master-ai",
            "registry": "npm",
            "version": "latest"
        },
        "config": {
            "env": {
                "OPENAI_API_KEY": {
                    "required": True,
                    "description": "OpenAI API key for AI-powered features"
                },
                "PERPLEXITY_API_KEY": {
                    "required": False,
                    "description": "Perplexity API key for research features"
                }
            },
            "args": []
        },
        "categories": ["project-management", "automation", "ai", "official"],
        "repository": {
            "url": "https://github.com/taskmaster-ai/taskmaster",
            "source": "github"
        }
    },
    "knowledge-graph": {
        "id": "io.local/knowledge-graph-engine",
        "name": "knowledge-graph",
        "description": "Knowledge Graph Engine for universal code repository analysis and retrieval",
        "package": {
            "name": "knowledge-graph-engine",
            "registry": "local",
            "version": "latest"
        },
        "config": {
            "env": {
                "NEO4J_URI": {
                    "required": True,
                    "description": "Neo4j database URI"
                },
                "NEO4J_USERNAME": {
                    "required": True,
                    "description": "Neo4j username"
                },
                "NEO4J_PASSWORD": {
                    "required": True,
                    "description": "Neo4j password"
                },
                "OPENAI_API_KEY": {
                    "required": True,
                    "description": "OpenAI API key for embeddings"
                }
            },
            "args": []
        },
        "categories": ["knowledge-management", "code-analysis", "local"],
        "repository": {
            "url": "https://github.com/devin/dblitz/engine",
            "source": "github"
        }
    }
    
    # COMMENTED OUT - Not currently configured in .mcp.json
    # "filesystem": {
    #     "id": "io.modelcontextprotocol.servers/filesystem",
    #     "name": "filesystem",
    #     "description": "MCP server for filesystem operations - read, write, and manage files and directories",
    #     "package": {
    #         "name": "@modelcontextprotocol/server-filesystem",
    #         "registry": "npm",
    #         "version": "latest"
    #     },
    #     "config": {
    #         "env": {},
    #         "args": ["path/to/allowed/directory"]  # Placeholder - user must configure
    #     },
    #     "categories": ["file-management", "official"],
    #     "repository": {
    #         "url": "https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem",
    #         "source": "github"
    #     }
    # },
    # "github": {
    #     "id": "io.modelcontextprotocol.servers/github",
    #     "name": "github",
    #     "description": "MCP server for GitHub API integration - manage repos, issues, PRs, and more",
    #     "package": {
    #         "name": "@modelcontextprotocol/server-github",
    #         "registry": "npm",
    #         "version": "latest"
    #     },
    #     "config": {
    #         "env": {
    #             "GITHUB_PERSONAL_ACCESS_TOKEN": {
    #                 "required": True,
    #                 "description": "GitHub personal access token for API authentication"
    #             }
    #         },
    #         "args": []
    #     },
    #     "categories": ["version-control", "development", "official"],
    #     "repository": {
    #         "url": "https://github.com/modelcontextprotocol/servers/tree/main/src/github",
    #         "source": "github"
    #     }
    # },
    # "postgres": {
    #     "id": "io.modelcontextprotocol.servers/postgres",
    #     "name": "postgres",
    #     "description": "MCP server for PostgreSQL database operations",
    #     "package": {
    #         "name": "@modelcontextprotocol/server-postgres",
    #         "registry": "npm",
    #         "version": "latest"
    #     },
    #     "config": {
    #         "env": {
    #             "POSTGRES_CONNECTION_STRING": {
    #                 "required": True,
    #                 "description": "PostgreSQL connection string (e.g., postgresql://user:pass@host:5432/db)"
    #             }
    #         },
    #         "args": []
    #     },
    #     "categories": ["database", "official"],
    #     "repository": {
    #         "url": "https://github.com/modelcontextprotocol/servers/tree/main/src/postgres",
    #         "source": "github"
    #     }
    # },
    # "brave-search": {
    #     "id": "io.modelcontextprotocol.servers/brave-search",
    #     "name": "brave-search",
    #     "description": "MCP server for Brave Search API integration",
    #     "package": {
    #         "name": "@modelcontextprotocol/server-brave-search",
    #         "registry": "npm",
    #         "version": "latest"
    #     },
    #     "config": {
    #         "env": {
    #             "BRAVE_API_KEY": {
    #                 "required": True,
    #                 "description": "Brave Search API key"
    #             }
    #         },
    #         "args": []
    #     },
    #     "categories": ["search", "web", "official"],
    #     "repository": {
    #         "url": "https://github.com/modelcontextprotocol/servers/tree/main/src/brave-search",
    #         "source": "github"
    #     }
    # },
    # "memory": {
    #     "id": "io.modelcontextprotocol.servers/memory",
    #     "name": "memory",
    #     "description": "MCP server for persistent memory/knowledge graph with semantic search",
    #     "package": {
    #         "name": "@modelcontextprotocol/server-memory",
    #         "registry": "npm",
    #         "version": "latest"
    #     },
    #     "config": {
    #         "env": {},
    #         "args": []
    #     },
    #     "categories": ["knowledge-management", "official"],
    #     "repository": {
    #         "url": "https://github.com/modelcontextprotocol/servers/tree/main/src/memory",
    #         "source": "github"
    #     }
    # },
    # "puppeteer": {
    #     "id": "io.modelcontextprotocol.servers/puppeteer",
    #     "name": "puppeteer",
    #     "description": "MCP server for browser automation using Puppeteer",
    #     "package": {
    #         "name": "@modelcontextprotocol/server-puppeteer",
    #         "registry": "npm",
    #         "version": "latest"
    #     },
    #     "config": {
    #         "env": {},
    #         "args": []
    #     },
    #     "categories": ["browser-automation", "testing", "official"],
    #     "repository": {
    #         "url": "https://github.com/modelcontextprotocol/servers/tree/main/src/puppeteer",
    #         "source": "github"
    #     }
    # },
    # "slack": {
    #     "id": "io.modelcontextprotocol.servers/slack",
    #     "name": "slack",
    #     "description": "MCP server for Slack workspace integration",
    #     "package": {
    #         "name": "@modelcontextprotocol/server-slack",
    #         "registry": "npm",
    #         "version": "latest"
    #     },
    #     "config": {
    #         "env": {
    #             "SLACK_BOT_TOKEN": {
    #                 "required": True,
    #                 "description": "Slack bot token (xoxb-...)"
    #             },
    #             "SLACK_TEAM_ID": {
    #                 "required": True,
    #                 "description": "Slack team/workspace ID"
    #             }
    #         },
    #         "args": []
    #     },
    #     "categories": ["communication", "official"],
    #     "repository": {
    #         "url": "https://github.com/modelcontextprotocol/servers/tree/main/src/slack",
    #         "source": "github"
    #     }
    # },
    # "gitlab": {
    #     "id": "io.modelcontextprotocol.servers/gitlab",
    #     "name": "gitlab",
    #     "description": "MCP server for GitLab API integration",
    #     "package": {
    #         "name": "@modelcontextprotocol/server-gitlab",
    #         "registry": "npm",
    #         "version": "latest"
    #     },
    #     "config": {
    #         "env": {
    #             "GITLAB_PERSONAL_ACCESS_TOKEN": {
    #                 "required": True,
    #                 "description": "GitLab personal access token"
    #             },
    #             "GITLAB_URL": {
    #                 "required": False,
    #                 "description": "GitLab instance URL (defaults to gitlab.com)",
    #                 "default": "https://gitlab.com"
    #             }
    #         },
    #         "args": []
    #     },
    #     "categories": ["version-control", "development", "official"],
    #     "repository": {
    #         "url": "https://github.com/modelcontextprotocol/servers/tree/main/src/gitlab",
    #         "source": "github"
    #     }
    # },
    # "google-maps": {
    #     "id": "io.modelcontextprotocol.servers/google-maps",
    #     "name": "google-maps",
    #     "description": "MCP server for Google Maps API integration",
    #     "package": {
    #         "name": "@modelcontextprotocol/server-google-maps",
    #         "registry": "npm",
    #         "version": "latest"
    #     },
    #     "config": {
    #         "env": {
    #             "GOOGLE_MAPS_API_KEY": {
    #                 "required": True,
    #                 "description": "Google Maps API key"
    #             }
    #         },
    #         "args": []
    #     },
    #     "categories": ["location", "maps", "official"],
    #     "repository": {
    #         "url": "https://github.com/modelcontextprotocol/servers/tree/main/src/google-maps",
    #         "source": "github"
    #     }
    # },
    # "aws-kb-retrieval": {
    #     "id": "io.modelcontextprotocol.servers/aws-kb-retrieval",
    #     "name": "aws-kb-retrieval",
    #     "description": "MCP server for AWS Knowledge Base retrieval",
    #     "package": {
    #         "name": "@modelcontextprotocol/server-aws-kb-retrieval",
    #         "registry": "npm",
    #         "version": "latest"
    #     },
    #     "config": {
    #         "env": {
    #             "AWS_ACCESS_KEY_ID": {
    #                 "required": True,
    #                 "description": "AWS access key ID"
    #             },
    #             "AWS_SECRET_ACCESS_KEY": {
    #                 "required": True,
    #                 "description": "AWS secret access key"
    #             },
    #             "AWS_REGION": {
    #                 "required": True,
    #                 "description": "AWS region (e.g., us-east-1)"
    #             },
    #             "AWS_KB_KNOWLEDGEBASE_ID": {
    #                 "required": True,
    #                 "description": "AWS Knowledge Base ID"
    #             }
    #         },
    #         "args": []
    #     },
    #     "categories": ["knowledge-management", "aws", "official"],
    #     "repository": {
    #         "url": "https://github.com/modelcontextprotocol/servers/tree/main/src/aws-kb-retrieval",
    #         "source": "github"
    #     }
    # },
    # "google-drive": {
    #     "id": "io.modelcontextprotocol.servers/google-drive",
    #     "name": "google-drive",
    #     "description": "MCP server for Google Drive integration - access and manage files",
    #     "package": {
    #         "name": "@modelcontextprotocol/server-google-drive",
    #         "registry": "npm",
    #         "version": "latest"
    #     },
    #     "config": {
    #         "env": {
    #             "GOOGLE_DRIVE_API_KEY": {
    #                 "required": True,
    #                 "description": "Google Drive API key"
    #             }
    #         },
    #         "args": []
    #     },
    #     "categories": ["file-management", "google", "official"],
    #     "repository": {
    #         "url": "https://github.com/modelcontextprotocol/servers/tree/main/src/google-drive",
    #         "source": "github"
    #     }
    # },
    # "sentry": {
    #     "id": "io.modelcontextprotocol.servers/sentry",
    #     "name": "sentry",
    #     "description": "MCP server for Sentry error tracking integration",
    #     "package": {
    #         "name": "@modelcontextprotocol/server-sentry",
    #         "registry": "npm",
    #         "version": "latest"
    #     },
    #     "config": {
    #         "env": {
    #             "SENTRY_AUTH_TOKEN": {
    #                 "required": True,
    #                 "description": "Sentry authentication token"
    #             },
    #             "SENTRY_ORG": {
    #                 "required": True,
    #                 "description": "Sentry organization slug"
    #             }
    #         },
    #         "args": []
    #     },
    #     "categories": ["monitoring", "error-tracking", "official"],
    #     "repository": {
    #         "url": "https://github.com/modelcontextprotocol/servers/tree/main/src/sentry",
    #         "source": "github"
    #     }
    # },
    # "linear": {
    #     "id": "io.modelcontextprotocol.servers/linear",
    #     "name": "linear",
    #     "description": "MCP server for Linear issue tracking integration",
    #     "package": {
    #         "name": "@modelcontextprotocol/server-linear",
    #         "registry": "npm",
    #         "version": "latest"
    #     },
    #     "config": {
    #         "env": {
    #             "LINEAR_API_KEY": {
    #                 "required": True,
    #                 "description": "Linear API key"
    #             }
    #         },
    #         "args": []
    #     },
    #     "categories": ["project-management", "issue-tracking", "official"],
    #     "repository": {
    #         "url": "https://github.com/modelcontextprotocol/servers/tree/main/src/linear",
    #         "source": "github"
    #     }
    # },
    # "notion": {
    #     "id": "io.modelcontextprotocol.servers/notion",
    #     "name": "notion",
    #     "description": "MCP server for Notion workspace integration",
    #     "package": {
    #         "name": "@modelcontextprotocol/server-notion",
    #         "registry": "npm",
    #         "version": "latest"
    #     },
    #     "config": {
    #         "env": {
    #             "NOTION_API_KEY": {
    #                 "required": True,
    #                 "description": "Notion integration token"
    #             }
    #         },
    #         "args": []
    #     },
    #     "categories": ["productivity", "documentation", "official"],
    #     "repository": {
    #         "url": "https://github.com/modelcontextprotocol/servers/tree/main/src/notion",
    #         "source": "github"
    #     }
    # },
    # "obsidian": {
    #     "id": "io.modelcontextprotocol.servers/obsidian",
    #     "name": "obsidian",
    #     "description": "MCP server for Obsidian vault integration",
    #     "package": {
    #         "name": "@modelcontextprotocol/server-obsidian",
    #         "registry": "npm",
    #         "version": "latest"
    #     },
    #     "config": {
    #         "env": {},
    #         "args": ["path/to/vault"]  # Placeholder - user must configure
    #     },
    #     "categories": ["note-taking", "knowledge-management", "official"],
    #     "repository": {
    #         "url": "https://github.com/modelcontextprotocol/servers/tree/main/src/obsidian",
    #         "source": "github"
    #     }
    # }
}


class LocalRegistry:
    """Local registry of known MCP servers"""
    
    def __init__(self, custom_registry_path: Optional[Path] = None):
        """Initialize with optional custom registry file"""
        self.custom_registry_path = custom_registry_path
        self._servers = KNOWN_SERVERS.copy()
        
        # Load custom servers if available
        if custom_registry_path and custom_registry_path.exists():
            self._load_custom_registry()
    
    def _load_custom_registry(self):
        """Load custom server definitions from file"""
        if not self.custom_registry_path:
            return
            
        try:
            with open(self.custom_registry_path, 'r') as f:
                custom_servers = json.load(f)
                print(f"📦 Loading {len(custom_servers)} custom servers from {self.custom_registry_path}")
                self._servers.update(custom_servers)
        except Exception as e:
            # Log but don't fail
            print(f"⚠️  Warning: Failed to load custom registry: {e}")
    
    def list_servers(self, 
                    categories: Optional[List[str]] = None,
                    search: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all servers with optional filtering
        
        Args:
            categories: Filter by categories
            search: Search in name and description
            
        Returns:
            List of server configurations
        """
        servers = list(self._servers.values())
        
        # Filter by categories
        if categories:
            servers = [
                s for s in servers
                if any(cat in s.get("categories", []) for cat in categories)
            ]
        
        # Search filter
        if search:
            search_lower = search.lower()
            servers = [
                s for s in servers
                if search_lower in s.get("name", "").lower() or
                   search_lower in s.get("description", "").lower()
            ]
        
        return servers
    
    def get_server(self, server_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific server by ID or name"""
        # Try by ID first
        for server in self._servers.values():
            if server.get("id") == server_id:
                return server
        
        # Try by name
        return self._servers.get(server_id)
    
    def get_categories(self) -> List[str]:
        """Get all unique categories"""
        categories = set()
        for server in self._servers.values():
            categories.update(server.get("categories", []))
        return sorted(list(categories))
    
    def add_custom_server(self, server_config: Dict[str, Any]) -> bool:
        """Add a custom server configuration"""
        server_id = server_config.get("id") or server_config.get("name")
        if not server_id:
            return False
            
        self._servers[server_id] = server_config
        
        # Save to custom registry if path is set
        if self.custom_registry_path:
            try:
                # Load existing custom servers
                custom_servers = {}
                if self.custom_registry_path.exists():
                    with open(self.custom_registry_path, 'r') as f:
                        custom_servers = json.load(f)
                
                # Add new server
                custom_servers[server_id] = server_config
                
                # Save back
                self.custom_registry_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.custom_registry_path, 'w') as f:
                    json.dump(custom_servers, f, indent=2)
                    
                return True
            except Exception:
                return False
                
        return True


def main():
    """Example usage"""
    registry = LocalRegistry()
    
    print("Available MCP Servers:")
    print("-" * 50)
    
    for server in registry.list_servers():
        print(f"\n{server['name']}:")
        print(f"  Description: {server['description']}")
        print(f"  Package: {server['package']['name']}")
        print(f"  Categories: {', '.join(server['categories'])}")
        
        env_vars = server['config'].get('env', {})
        if env_vars:
            print("  Required env vars:")
            for var, details in env_vars.items():
                if isinstance(details, dict) and details.get('required'):
                    print(f"    - {var}")
    
    print(f"\n\nTotal servers: {len(registry.list_servers())}")
    print(f"Categories: {', '.join(registry.get_categories())}")
    print("\nNote: This is a local registry. The official MCP Registry API is not yet publicly available.")


if __name__ == "__main__":
    main()