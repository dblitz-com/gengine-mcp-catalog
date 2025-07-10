# 🚀 Generative OpenAPI → MCP Server Pipeline

This directory contains tools and documentation for automatically generating OpenAPI specifications from ANY running REST API, then converting them to MCP servers.

## 🎯 The Problem We Solve

Instead of being locked into specific languages or frameworks (FastAPI, Flask-RESTX, etc.), we can:
1. Build REST APIs in **ANY language** (Go, Rust, Node.js, Python, Java, etc.)
2. **Automatically generate** OpenAPI specs by analyzing HTTP traffic
3. Convert OpenAPI → MCP server using FastMCP

## 🔄 Complete Workflow

### 1️⃣ Build Your REST API (Any Language)

```python
# Python (Flask, FastAPI, Django, whatever!)
@app.route('/api/v1/servers')
def list_servers():
    return {"servers": load_servers()}
```

```javascript
// Node.js (Express, Koa, Hapi, whatever!)
app.get('/api/v1/servers', (req, res) => {
    res.json({servers: loadServers()})
})
```

```go
// Go (Gin, Echo, net/http, whatever!)
func listServers(w http.ResponseWriter, r *http.Request) {
    json.NewEncoder(w).Encode(map[string]interface{}{
        "servers": loadServers(),
    })
}
```

### 2️⃣ Capture Traffic & Generate OpenAPI

#### Option A: Optic CLI (Recommended)

```bash
# Install Optic
npm install -g @useoptic/optic

# Initialize in your project
optic capture init

# Start your API
python api_server.py  # or node server.js, or ./mygoapp

# Start Optic proxy
optic capture start --proxy http://localhost:8000

# Exercise your API (manually or with tests)
curl http://localhost:8001/api/v1/servers
curl http://localhost:8001/api/v1/servers/search?q=context
curl -X POST http://localhost:8001/api/v1/servers/generate-config \
  -d '{"servers": ["context7"]}'

# Stop and generate OpenAPI
optic capture stop

# Export OpenAPI spec
optic export openapi.json
```

#### Option B: OpenAPI DevTools (Browser)

1. Install browser extension
2. Open your web app
3. Use the app normally
4. Export captured OpenAPI spec

#### Option C: Run capture script (coming soon)

```bash
# Automated capture script
./capture-openapi.sh --api-url http://localhost:8000 --output openapi.json
```

### 3️⃣ Generate MCP Server from OpenAPI

```python
# generate_mcp_from_openapi.py
import json
import httpx
from fastmcp import FastMCP

# Load the AUTO-GENERATED OpenAPI spec
with open('openapi.json') as f:
    openapi_spec = json.load(f)

# Create MCP server pointing to your REST API
mcp = FastMCP.from_openapi(
    openapi_spec=openapi_spec,
    client=httpx.AsyncClient(base_url="http://localhost:8000"),
    name="MCP Catalog"
)

# Run as MCP server
if __name__ == "__main__":
    mcp.run()
```

## 🛠️ Tools Included

### Traffic Capture Tools
- **Optic CLI** - Proxy-based OpenAPI generation
- **OpenAPI AutoSpec** - Simple localhost proxy
- **OpenAPI DevTools** - Browser extension

### Conversion Tools
- `generate_mcp_from_openapi.py` - Convert OpenAPI → MCP server
- `capture-openapi.sh` - Automated capture script (coming soon)

## 🎨 Use Cases

1. **Legacy API Documentation** - Generate OpenAPI for undocumented APIs
2. **Multi-language Projects** - Use Go for API, Python for MCP server
3. **Rapid Prototyping** - Build API quickly, generate specs automatically
4. **API Testing** - Ensure OpenAPI matches actual implementation

## 📊 Comparison with Traditional Approaches

| Approach | Language Lock-in | Requires Annotations | Accuracy |
|----------|-----------------|---------------------|----------|
| FastAPI/Flask-RESTX | ✅ Python only | ✅ Yes | ⚠️ Can drift |
| Manual OpenAPI | ❌ None | ❌ No | ⚠️ Often outdated |
| **Traffic Capture** | ❌ None | ❌ No | ✅ Always accurate |

## 🚀 Quick Start

```bash
# 1. Install dependencies
npm install -g @useoptic/optic
pip install fastmcp httpx pyyaml

# 2. Start your REST API
cd ../
python -m mcp_catalog  # or your API in any language

# 3. Capture and generate
cd generative-openapi
./quick-capture.sh

# 4. Run MCP server
python mcp_server_generated.py
```

## 🔗 Resources

- [Optic Documentation](https://www.useoptic.com/docs)
- [OpenAPI Specification](https://www.openapis.org/)
- [FastMCP from_openapi](https://docs.fastmcp.com/servers/openapi)
- [MCP Protocol](https://modelcontextprotocol.io)