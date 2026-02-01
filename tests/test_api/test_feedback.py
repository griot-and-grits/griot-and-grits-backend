"""Tests for the /feedback endpoints."""

import pytest


SAMPLE_FEEDBACK = {
    "description": "The transcript has several inaccuracies in the second paragraph.",
    "feedback_type": "transcript_accuracy",
    "artifact_id": "test-artifact-123",
    "artifact_title": "Interview with John Doe",
    "submitter_name": "Test User",
}


@pytest.mark.asyncio
async def test_create_feedback(client):
    """POST /feedback/ with valid data should return 200 with feedback_id."""
    response = await client.post("/feedback/", json=SAMPLE_FEEDBACK)
    assert response.status_code == 200
    body = response.json()
    assert "feedback_id" in body
    assert body["status"] == "new"
    assert body["feedback_type"] == "transcript_accuracy"


@pytest.mark.asyncio
async def test_list_feedback(client):
    """Create feedback then GET /feedback/ should include it."""
    # Create
    create_resp = await client.post("/feedback/", json=SAMPLE_FEEDBACK)
    assert create_resp.status_code == 200

    # List
    list_resp = await client.get("/feedback/")
    assert list_resp.status_code == 200
    body = list_resp.json()
    assert "feedback" in body
    assert "total" in body
    assert body["total"] >= 1


@pytest.mark.asyncio
async def test_get_feedback_by_id(client):
    """Create then GET /feedback/{id} should return the same feedback."""
    create_resp = await client.post("/feedback/", json=SAMPLE_FEEDBACK)
    assert create_resp.status_code == 200
    feedback_id = create_resp.json()["feedback_id"]

    get_resp = await client.get(f"/feedback/{feedback_id}")
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["feedback_id"] == feedback_id
    assert body["description"] == SAMPLE_FEEDBACK["description"]


@pytest.mark.asyncio
async def test_update_feedback_status(client):
    """Create then PATCH /feedback/{id}/status should update status."""
    create_resp = await client.post("/feedback/", json=SAMPLE_FEEDBACK)
    assert create_resp.status_code == 200
    feedback_id = create_resp.json()["feedback_id"]

    update_resp = await client.patch(
        f"/feedback/{feedback_id}/status",
        json={"status": "reviewed", "admin_notes": "Reviewed by test suite"},
    )
    assert update_resp.status_code == 200
    body = update_resp.json()
    assert body["status"] == "reviewed"
    assert body["admin_notes"] == "Reviewed by test suite"


@pytest.mark.asyncio
async def test_create_feedback_missing_required_fields(client):
    """POST /feedback/ without required fields should fail with 422."""
    response = await client.post("/feedback/", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_feedback_not_found(client):
    """GET /feedback/{id} with non-existent ID should return 404."""
    response = await client.get("/feedback/fb_nonexistent123")
    assert response.status_code == 404
