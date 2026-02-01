"""Tests for the /artifacts endpoints."""

import json
import pytest


SAMPLE_METADATA = {
    "title": "Test Artifact",
    "description": "A test artifact for E2E testing",
    "creator": "Test Suite",
    "creation_date": "2024-01-15",
}


@pytest.mark.asyncio
async def test_ingest_artifact(client):
    """POST /artifacts/ingest with valid file and metadata should return 200."""
    response = await client.post(
        "/artifacts/ingest",
        data={"metadata": json.dumps(SAMPLE_METADATA)},
        files={"file": ("test.txt", b"hello world", "text/plain")},
    )
    assert response.status_code == 200
    body = response.json()
    assert "artifact_id" in body
    assert "status" in body


@pytest.mark.asyncio
async def test_get_artifact_status(client):
    """Ingest then GET /artifacts/{id}/status should return status."""
    # Ingest first
    ingest_resp = await client.post(
        "/artifacts/ingest",
        data={"metadata": json.dumps(SAMPLE_METADATA)},
        files={"file": ("status-test.txt", b"status check content", "text/plain")},
    )
    assert ingest_resp.status_code == 200
    artifact_id = ingest_resp.json()["artifact_id"]

    # Check status
    status_resp = await client.get(f"/artifacts/{artifact_id}/status")
    assert status_resp.status_code == 200
    body = status_resp.json()
    assert body["artifact_id"] == artifact_id
    assert "status" in body


@pytest.mark.asyncio
async def test_get_artifact_by_id(client):
    """Ingest then GET /artifacts/{id} should return full artifact."""
    ingest_resp = await client.post(
        "/artifacts/ingest",
        data={"metadata": json.dumps(SAMPLE_METADATA)},
        files={"file": ("get-test.txt", b"get by id content", "text/plain")},
    )
    assert ingest_resp.status_code == 200
    artifact_id = ingest_resp.json()["artifact_id"]

    get_resp = await client.get(f"/artifacts/{artifact_id}")
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["artifact_id"] == artifact_id
    assert body["title"] == SAMPLE_METADATA["title"]


@pytest.mark.asyncio
async def test_list_artifacts(client):
    """GET /artifacts/ should return a list with total count."""
    # Ingest an artifact to ensure list is non-empty
    await client.post(
        "/artifacts/ingest",
        data={"metadata": json.dumps(SAMPLE_METADATA)},
        files={"file": ("list-test.txt", b"list test content", "text/plain")},
    )

    response = await client.get("/artifacts/")
    assert response.status_code == 200
    body = response.json()
    assert "artifacts" in body
    assert "total" in body
    assert body["total"] >= 1


@pytest.mark.asyncio
async def test_ingest_missing_file(client):
    """POST /artifacts/ingest without a file should fail with 422."""
    response = await client.post(
        "/artifacts/ingest",
        data={"metadata": json.dumps(SAMPLE_METADATA)},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_ingest_invalid_metadata(client):
    """POST /artifacts/ingest with invalid JSON metadata should fail with 400."""
    response = await client.post(
        "/artifacts/ingest",
        data={"metadata": "not-json"},
        files={"file": ("bad-meta.txt", b"content", "text/plain")},
    )
    assert response.status_code == 400
