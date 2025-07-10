# 🔥 Example: Go REST API → OpenAPI → MCP Server

This example shows how to create an MCP server from a Go REST API without writing any OpenAPI specs!

## 1. Create a Simple Go REST API

```go
// main.go
package main

import (
    "encoding/json"
    "fmt"
    "net/http"
)

type Server struct {
    ID          string   `json:"id"`
    Name        string   `json:"name"`
    Description string   `json:"description"`
    Category    string   `json:"category"`
    Features    []string `json:"features"`
}

var servers = []Server{
    {
        ID:          "context7",
        Name:        "Context7",
        Description: "Library documentation provider",
        Category:    "documentation",
        Features:    []string{"npm", "pypi", "crates"},
    },
    {
        ID:          "perplexity",
        Name:        "Perplexity",
        Description: "Web search and research",
        Category:    "search",
        Features:    []string{"search", "research"},
    },
}

func listServers(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(servers)
}

func searchServers(w http.ResponseWriter, r *http.Request) {
    query := r.URL.Query().Get("q")
    var results []Server
    
    for _, server := range servers {
        if query == "" || 
           contains(server.Name, query) || 
           contains(server.Description, query) {
            results = append(results, server)
        }
    }
    
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(map[string]interface{}{
        "results": results,
        "query": query,
    })
}

func contains(s, substr string) bool {
    return len(substr) == 0 || 
           len(s) >= len(substr) && 
           s[:len(substr)] == substr
}

func main() {
    http.HandleFunc("/api/v1/servers", listServers)
    http.HandleFunc("/api/v1/servers/search", searchServers)
    
    fmt.Println("Go REST API running on :8000")
    http.ListenAndServe(":8000", nil)
}
```

## 2. Run the Go API

```bash
go run main.go
# API running on http://localhost:8000
```

## 3. Capture Traffic & Generate OpenAPI

```bash
cd generative-openapi
./quick-capture.sh

# When prompted, make these API calls:
curl http://localhost:8001/api/v1/servers
curl http://localhost:8001/api/v1/servers/search?q=context

# Press ENTER to finish capture
```

## 4. What Gets Generated

### captured-openapi.json (AUTO-GENERATED!)
```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Captured API",
    "version": "1.0.0"
  },
  "paths": {
    "/api/v1/servers": {
      "get": {
        "responses": {
          "200": {
            "description": "Successful response",
            "content": {
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "type": "object",
                    "properties": {
                      "id": {"type": "string"},
                      "name": {"type": "string"},
                      "description": {"type": "string"},
                      "category": {"type": "string"},
                      "features": {
                        "type": "array",
                        "items": {"type": "string"}
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/servers/search": {
      "get": {
        "parameters": [{
          "name": "q",
          "in": "query",
          "schema": {"type": "string"}
        }],
        "responses": {
          "200": {
            "description": "Search results",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "results": {
                      "type": "array",
                      "items": {"$ref": "#/components/schemas/Server"}
                    },
                    "query": {"type": "string"}
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

### mcp_server_generated.py (AUTO-GENERATED!)
```python
#!/usr/bin/env python3
# Auto-generated MCP server from captured OpenAPI spec

import json
import httpx
from fastmcp import FastMCP

# Load OpenAPI spec
with open('captured-openapi.json') as f:
    openapi_spec = json.load(f)

# Create MCP server
mcp = FastMCP.from_openapi(
    openapi_spec=openapi_spec,
    client=httpx.AsyncClient(base_url="http://localhost:8000"),
    name="MCP Catalog (Generated)"
)

if __name__ == "__main__":
    import sys
    if "--http" in sys.argv:
        mcp.run(transport="http", port=8002)
    else:
        mcp.run(transport="stdio")
```

## 5. Run the MCP Server

```bash
# Test with stdio
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","clientInfo":{"name":"test","version":"1.0"},"capabilities":{}}}' | python mcp_server_generated.py

# Or run with HTTP
python mcp_server_generated.py --http

# Add to Claude Code
claude mcp add go-catalog --transport http http://localhost:8002/mcp/
```

## 🎯 What Just Happened?

1. We built a REST API in **Go** (could be ANY language!)
2. Used **Optic** to capture traffic and generate OpenAPI
3. Used **FastMCP** to create an MCP server from OpenAPI
4. Now Claude can access our Go API through MCP!

## 🚀 The Power

- **Zero annotations** in Go code
- **Zero OpenAPI writing**
- **Automatic schema inference**
- **Language agnostic**
- **Always accurate** (based on real traffic)

This same approach works with:
- Rust (Actix, Rocket, Warp)
- Java (Spring Boot, Jersey)
- Node.js (Express, Fastify, Koa)
- Python (Django, Flask, Bottle)
- Ruby (Rails, Sinatra)
- **ANY HTTP REST API!**