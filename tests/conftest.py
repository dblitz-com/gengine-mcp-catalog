#!/usr/bin/env python3
"""
Pytest configuration and fixtures for gengine-mcp-catalog tests
"""

import pytest
from httpx import AsyncClient, ASGITransport
from api.main import app


@pytest.fixture
async def client():
    """Create async test client"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac