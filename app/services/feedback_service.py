"""
Service for managing user feedback submissions.
"""

import uuid
from app.models.feedback import (
    Feedback,
    FeedbackCreateRequest,
    FeedbackStatus,
    FeedbackStatusUpdateRequest,
    FeedbackType,
)
from app.services.db import Database
import logging

logger = logging.getLogger(__name__)


class FeedbackService:
    """Service for feedback lifecycle"""

    def __init__(self, db: Database):
        self.db = db

    async def create_feedback(self, request: FeedbackCreateRequest) -> Feedback:
        """
        Create a new feedback submission.

        Args:
            request: FeedbackCreateRequest with feedback details

        Returns:
            Feedback with NEW status
        """
        feedback = Feedback(
            feedback_id=self._generate_feedback_id(),
            description=request.description,
            feedback_type=request.feedback_type,
            artifact_id=request.artifact_id,
            artifact_title=request.artifact_title,
            chat_user_message=request.chat_user_message,
            chat_assistant_message=request.chat_assistant_message,
            submitter_name=request.submitter_name,
            submitter_email=request.submitter_email,
        )

        await self.db.insert_feedback(feedback)
        logger.info(f"Created feedback: {feedback.feedback_id} type={feedback.feedback_type.value}")
        return feedback

    async def update_status(
        self, feedback_id: str, request: FeedbackStatusUpdateRequest
    ) -> Feedback:
        """
        Update feedback status and optional admin notes.

        Args:
            feedback_id: Feedback identifier
            request: Status update request

        Returns:
            Updated Feedback

        Raises:
            FeedbackServiceError: If feedback not found
        """
        existing = await self.db.get_feedback(feedback_id)
        if not existing:
            raise FeedbackServiceError(f"Feedback not found: {feedback_id}")

        updates = {"status": request.status.value}
        if request.admin_notes is not None:
            updates["admin_notes"] = request.admin_notes

        await self.db.update_feedback(feedback_id, updates)

        updated = await self.db.get_feedback(feedback_id)
        logger.info(f"Updated feedback {feedback_id} status={request.status.value}")
        return Feedback(**updated)

    async def get_feedback(self, feedback_id: str) -> Feedback | None:
        """
        Get feedback by ID.

        Args:
            feedback_id: Feedback identifier

        Returns:
            Feedback or None
        """
        feedback_dict = await self.db.get_feedback(feedback_id)
        if not feedback_dict:
            return None
        return Feedback(**feedback_dict)

    async def list_feedback(
        self,
        status: FeedbackStatus | None = None,
        feedback_type: FeedbackType | None = None,
        limit: int = 50,
        skip: int = 0,
    ) -> tuple[list[Feedback], int]:
        """
        List feedback with optional filtering.

        Args:
            status: Optional status filter
            feedback_type: Optional type filter
            limit: Maximum number of results
            skip: Number to skip for pagination

        Returns:
            Tuple of (feedback list, total count)
        """
        feedback_dicts = await self.db.list_feedback(status, feedback_type, limit, skip)
        feedback_list = [Feedback(**f) for f in feedback_dicts]
        total = await self.db.count_feedback(status, feedback_type)
        return feedback_list, total

    def _generate_feedback_id(self) -> str:
        """Generate unique feedback ID"""
        return f"fb_{uuid.uuid4().hex[:12]}"


class FeedbackServiceError(Exception):
    """Feedback service exceptions"""
    pass
