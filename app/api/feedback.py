"""
API endpoints for user feedback.
"""

from fastapi import APIRouter, HTTPException, Query
from app.models.feedback import (
    FeedbackCreateRequest,
    FeedbackStatus,
    FeedbackStatusUpdateRequest,
    FeedbackType,
    Feedback,
)
from app.factory import factory
from app.services.feedback_service import FeedbackServiceError
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("/", response_model=Feedback)
async def create_feedback(request: FeedbackCreateRequest):
    """
    Submit user feedback about content or AI responses.

    Public endpoint — no authentication required.
    """
    try:
        feedback = await factory.feedback_service.create_feedback(request)
        return feedback
    except Exception as e:
        logger.error(f"Failed to create feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_feedback(
    status: FeedbackStatus | None = Query(default=None, description="Filter by status"),
    feedback_type: FeedbackType | None = Query(default=None, description="Filter by feedback type"),
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of results"),
    skip: int = Query(default=0, ge=0, description="Number of results to skip"),
):
    """
    List feedback submissions with optional filtering.
    """
    try:
        feedback_list, total = await factory.feedback_service.list_feedback(
            status, feedback_type, limit, skip
        )
        return {
            "feedback": feedback_list,
            "count": len(feedback_list),
            "total": total,
        }
    except Exception as e:
        logger.error(f"Failed to list feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{feedback_id}", response_model=Feedback)
async def get_feedback(feedback_id: str):
    """
    Get feedback details by ID.
    """
    feedback = await factory.feedback_service.get_feedback(feedback_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return feedback


@router.patch("/{feedback_id}/status", response_model=Feedback)
async def update_feedback_status(
    feedback_id: str, request: FeedbackStatusUpdateRequest
):
    """
    Update feedback status and optional admin notes.
    """
    try:
        feedback = await factory.feedback_service.update_status(feedback_id, request)
        return feedback
    except FeedbackServiceError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update feedback {feedback_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
