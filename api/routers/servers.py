#!/usr/bin/env python3
"""
FastAPI router for server management endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from ..models.servers import (
    ServerListResponse, ServerDetails, SearchResponse, 
    CategoriesResponse, CategoryInfo, ServerSummary
)
from ..dependencies import get_server_registry, get_server_by_id

router = APIRouter()

@router.get("/servers", response_model=ServerListResponse)
async def list_available_servers():
    """List all available MCP servers"""
    registry = get_server_registry()
    
    servers = []
    for server_id, server_config in registry.items():
        servers.append(ServerSummary(
            id=server_id,
            name=server_config.get("name", server_id),
            description=server_config.get("description", ""),
            category=server_config.get("category", "other"),
            homepage=server_config.get("homepage", ""),
            vendor=server_config.get("vendor", "community")
        ))
    
    return ServerListResponse(
        servers=servers,
        total=len(servers)
    )

@router.get("/servers/search", response_model=SearchResponse)
async def search_servers(
    q: Optional[str] = Query(None, description="Search query"),
    category: Optional[str] = Query(None, description="Category filter")
):
    """Search MCP servers by query and/or category"""
    if not q and not category:
        raise HTTPException(status_code=400, detail="Query parameter 'q' or 'category' required")
    
    registry = get_server_registry()
    results = []
    
    for server_id, server_config in registry.items():
        # Check if matches query
        matches_query = True
        if q:
            q_lower = q.lower()
            matches_query = (
                q_lower in server_id.lower() or
                q_lower in server_config.get("name", "").lower() or
                q_lower in server_config.get("description", "").lower()
            )
        
        # Check category filter
        matches_category = (
            category is None or 
            server_config.get("category", "other") == category
        )
        
        if matches_query and matches_category:
            results.append(ServerSummary(
                id=server_id,
                name=server_config.get("name", server_id),
                description=server_config.get("description", ""),
                category=server_config.get("category", "other"),
                vendor=server_config.get("vendor", "community")
            ))
    
    return SearchResponse(
        results=results,
        total=len(results),
        query=q,
        category=category
    )

@router.get("/servers/{server_id}", response_model=ServerDetails)
async def get_server_info(server_id: str):
    """Get detailed information about a specific MCP server"""
    server_config = get_server_by_id(server_id)
    
    if not server_config:
        raise HTTPException(status_code=404, detail=f"Server '{server_id}' not found")
    
    # Build detailed response
    server_details = ServerDetails(
        id=server_id,
        name=server_config.get("name", server_id),
        description=server_config.get("description", ""),
        category=server_config.get("category", "other"),
        vendor=server_config.get("vendor", "community"),
        homepage=server_config.get("homepage", ""),
        license=server_config.get("license", "Unknown"),
        installation=server_config.get("installation", {}),
        config=server_config.get("config", {}),
        features=server_config.get("features", []),
        supported_platforms=server_config.get("supported_platforms", ["all"])
    )
    
    # Add capabilities if available
    if "capabilities" in server_config:
        server_details.capabilities = server_config["capabilities"]
    
    return server_details

@router.get("/categories", response_model=CategoriesResponse)
async def list_categories():
    """List all available server categories"""
    registry = get_server_registry()
    categories = {}
    
    for server_config in registry.values():
        category = server_config.get("category", "other")
        if category not in categories:
            categories[category] = 0
        categories[category] += 1
    
    category_list = [
        CategoryInfo(name=cat, count=count)
        for cat, count in sorted(categories.items())
    ]
    
    return CategoriesResponse(categories=category_list)