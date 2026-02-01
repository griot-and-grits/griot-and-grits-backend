"""
Shared test fixtures for backend API tests.

These tests use httpx.AsyncClient with ASGITransport to test the FastAPI app
directly without needing a running server. The factory's services (Database,
ObjectStorage) connect to real MongoDB/MinIO when running inside the Docker
Compose test environment.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.server import app


@pytest.fixture
async def client():
    """Async HTTP client wired to the FastAPI application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
