"""
Shared test fixtures for backend API tests.

Supports two modes:

1. **Integration mode** (default): Tests hit a running backend via HTTP.
   Set BACKEND_URL env var (defaults to http://localhost:8000).
   Used with Docker Compose: `make test-services-up && make test-backend`

2. **In-process mode**: Set USE_ASGI=true to use ASGITransport.
   Requires MongoDB and MinIO to be directly reachable from the test process.
"""

import os
import pytest
from httpx import AsyncClient

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


@pytest.fixture
async def client():
    """Async HTTP client targeting the backend API."""
    if os.environ.get("USE_ASGI") == "true":
        from httpx import ASGITransport
        from app.server import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            yield ac
    else:
        async with AsyncClient(base_url=BACKEND_URL) as ac:
            yield ac
