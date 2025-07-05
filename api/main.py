#!/usr/bin/env python3
"""
MCP Catalog FastAPI Server

A modern REST API for MCP server discovery and configuration generation.
Provides auto-generated OpenAPI specs for gengine-mcp consumption.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .routers import servers, config
from .dependencies import load_server_registry

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    load_server_registry()
    yield
    # Shutdown (if needed)

# Create FastAPI app with metadata
app = FastAPI(
    title="MCP Catalog API",
    description="REST API for discovering and configuring Model Context Protocol servers",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(servers.router, prefix="/api/v1")
app.include_router(config.router, prefix="/api/v1")

@app.get("/", response_model=dict)
async def root():
    """Root endpoint with API information"""
    return {
        "name": "MCP Catalog API",
        "version": "1.0.0",
        "description": "REST API for MCP server discovery and configuration",
        "docs": "/docs",
        "openapi": "/openapi.json"
    }

@app.get("/health", response_model=dict)
async def health_check():
    """Health check endpoint"""
    from .dependencies import get_server_registry
    registry = get_server_registry()
    
    return {
        "status": "healthy",
        "server_count": len(registry),
        "catalog_version": "1.0.0",
        "api_version": "v1"
    }

if __name__ == "__main__":
    import uvicorn
    import sys
    
    print("🚀 Starting MCP Catalog FastAPI server")
    
    if "--production" in sys.argv:
        # Production mode
        uvicorn.run("main:app", host="0.0.0.0", port=8000)
    else:
        # Development mode with auto-reload
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)