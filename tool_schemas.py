"""
Tool Schema Definitions for MCP Catalog

This module provides parameter schemas for known MCP tools to enable
proper parameter passing instead of generic kwargs.
"""

from typing import Dict, Any, Optional

# TaskMaster tool schemas
TASKMASTER_SCHEMAS = {
    "initialize_project": {
        "properties": {
            "projectRoot": {
                "type": "string",
                "description": "The root directory for the project"
            },
            "addAliases": {
                "type": "boolean",
                "default": True,
                "description": "Add shell aliases"
            },
            "initGit": {
                "type": "boolean", 
                "default": True,
                "description": "Initialize Git repository"
            },
            "rules": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of rule profiles to include"
            },
            "skipInstall": {
                "type": "boolean",
                "default": False,
                "description": "Skip installing dependencies"
            },
            "storeTasksInGit": {
                "type": "boolean",
                "default": True,
                "description": "Store tasks in Git"
            },
            "yes": {
                "type": "boolean",
                "default": True,
                "description": "Skip prompts"
            }
        },
        "required": ["projectRoot"]
    },
    "models": {
        "properties": {
            "projectRoot": {
                "type": "string",
                "description": "The directory of the project"
            },
            "listAvailableModels": {
                "type": "boolean",
                "description": "List all available models"
            },
            "setMain": {
                "type": "string",
                "description": "Set the primary model"
            },
            "setFallback": {
                "type": "string",
                "description": "Set the fallback model"
            },
            "setResearch": {
                "type": "string",
                "description": "Set the research model"
            }
        },
        "required": ["projectRoot"]
    },
    "get_tasks": {
        "properties": {
            "projectRoot": {
                "type": "string",
                "description": "The directory of the project"
            },
            "file": {
                "type": "string",
                "description": "Path to the tasks file"
            },
            "status": {
                "type": "string",
                "description": "Filter tasks by status"
            },
            "withSubtasks": {
                "type": "boolean",
                "description": "Include subtasks"
            }
        },
        "required": ["projectRoot"]
    },
    "get_task": {
        "properties": {
            "projectRoot": {
                "type": "string",
                "description": "Project root directory"
            },
            "id": {
                "type": "string",
                "description": "Task ID to get"
            },
            "file": {
                "type": "string",
                "description": "Path to tasks file"
            }
        },
        "required": ["projectRoot", "id"]
    },
    "next_task": {
        "properties": {
            "projectRoot": {
                "type": "string",
                "description": "The directory of the project"
            },
            "file": {
                "type": "string",
                "description": "Path to tasks file"
            }
        },
        "required": ["projectRoot"]
    },
    "set_task_status": {
        "properties": {
            "projectRoot": {
                "type": "string",
                "description": "Project root directory"
            },
            "id": {
                "type": "string",
                "description": "Task ID"
            },
            "status": {
                "type": "string",
                "enum": ["pending", "done", "in-progress", "review", "deferred", "cancelled"],
                "description": "New status"
            }
        },
        "required": ["projectRoot", "id", "status"]
    },
    "add_task": {
        "properties": {
            "projectRoot": {
                "type": "string",
                "description": "Project root directory"
            },
            "prompt": {
                "type": "string",
                "description": "Task description"
            },
            "priority": {
                "type": "string",
                "enum": ["high", "medium", "low"],
                "description": "Task priority"
            }
        },
        "required": ["projectRoot"]
    },
    "update_task": {
        "properties": {
            "projectRoot": {
                "type": "string",
                "description": "Project root directory"
            },
            "id": {
                "type": "string",
                "description": "Task ID to update"
            },
            "prompt": {
                "type": "string",
                "description": "Update information"
            }
        },
        "required": ["projectRoot", "id", "prompt"]
    },
    "research": {
        "properties": {
            "projectRoot": {
                "type": "string",
                "description": "Project root directory"
            },
            "query": {
                "type": "string",
                "description": "Research query"
            },
            "detailLevel": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "description": "Detail level"
            }
        },
        "required": ["projectRoot", "query"]
    }
}

# Perplexity tool schemas
PERPLEXITY_SCHEMAS = {
    "perplexity_ask": {
        "properties": {
            "messages": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "role": {"type": "string"},
                        "content": {"type": "string"}
                    },
                    "required": ["role", "content"]
                },
                "description": "Array of conversation messages"
            }
        },
        "required": ["messages"]
    }
}

# Sequential thinking tool schemas
SEQUENTIAL_THINKING_SCHEMAS = {
    "sequentialthinking": {
        "properties": {
            "thought": {
                "type": "string",
                "description": "Your current thinking step"
            },
            "nextThoughtNeeded": {
                "type": "boolean",
                "description": "Whether another thought step is needed"
            },
            "thoughtNumber": {
                "type": "integer",
                "minimum": 1,
                "description": "Current thought number"
            },
            "totalThoughts": {
                "type": "integer",
                "minimum": 1,
                "description": "Estimated total thoughts needed"
            },
            "isRevision": {
                "type": "boolean",
                "description": "Whether this revises previous thinking"
            },
            "revisesThought": {
                "type": "integer",
                "minimum": 1,
                "description": "Which thought is being reconsidered"
            },
            "branchFromThought": {
                "type": "integer",
                "minimum": 1,
                "description": "Branching point thought number"
            },
            "branchId": {
                "type": "string",
                "description": "Branch identifier"
            },
            "needsMoreThoughts": {
                "type": "boolean",
                "description": "If more thoughts are needed"
            }
        },
        "required": ["thought", "nextThoughtNeeded", "thoughtNumber", "totalThoughts"]
    }
}

# Context7 tool schemas
CONTEXT7_SCHEMAS = {
    "resolve_library_id": {
        "properties": {
            "libraryName": {
                "type": "string",
                "description": "Library name to search for"
            }
        },
        "required": ["libraryName"]
    },
    "get_library_docs": {
        "properties": {
            "context7CompatibleLibraryID": {
                "type": "string",
                "description": "Context7-compatible library ID"
            },
            "tokens": {
                "type": "number",
                "default": 10000,
                "description": "Maximum tokens to retrieve"
            },
            "topic": {
                "type": "string",
                "description": "Topic to focus on"
            }
        },
        "required": ["context7CompatibleLibraryID"]
    }
}

# Combine all schemas
ALL_TOOL_SCHEMAS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "taskmaster-ai": TASKMASTER_SCHEMAS,
    "perplexity-ask": PERPLEXITY_SCHEMAS,
    "sequential-thinking": SEQUENTIAL_THINKING_SCHEMAS,
    "Context7": CONTEXT7_SCHEMAS
}


def get_tool_schema(server_name: str, tool_name: str) -> Optional[Dict[str, Any]]:
    """Get the parameter schema for a specific tool"""
    server_schemas = ALL_TOOL_SCHEMAS.get(server_name, {})
    return server_schemas.get(tool_name)


def get_all_schemas_for_server(server_name: str) -> Dict[str, Dict[str, Any]]:
    """Get all tool schemas for a specific server"""
    return ALL_TOOL_SCHEMAS.get(server_name, {})