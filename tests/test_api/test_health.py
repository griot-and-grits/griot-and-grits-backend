"""Tests for the /health endpoint."""

import pytest


@pytest.mark.asyncio
async def test_health_returns_200(client):
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"


@pytest.mark.asyncio
async def test_root_returns_200(client):
    response = await client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert "version" in body
    assert "endpoints" in body
