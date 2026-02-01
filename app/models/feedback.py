"""
Feedback models for user-submitted issue reports.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class FeedbackType(str, Enum):
    """Type of feedback being submitted"""
    TRANSCRIPT_ACCURACY = "transcript_accuracy"
    GRIOT_RESPONSE = "griot_response"
    CONTENT_ISSUE = "content_issue"
    OTHER = "other"


class FeedbackStatus(str, Enum):
    """Status of a feedback submission"""
    NEW = "new"
    REVIEWED = "reviewed"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class FeedbackCreateRequest(BaseModel):
    """Request to submit feedback"""
    description: str = Field(min_length=1, max_length=2000)
    feedback_type: FeedbackType
    artifact_id: str | None = Field(default=None, max_length=200)
    artifact_title: str | None = Field(default=None, max_length=500)
    chat_user_message: str | None = Field(default=None, max_length=2000)
    chat_assistant_message: str | None = Field(default=None, max_length=5000)
    submitter_name: str | None = Field(default=None, max_length=200)
    submitter_email: str | None = Field(default=None, max_length=200)


class Feedback(BaseModel):
    """Full feedback document model"""
    feedback_id: str = Field(description="Unique feedback identifier")
    description: str
    feedback_type: FeedbackType
    status: FeedbackStatus = Field(default=FeedbackStatus.NEW)

    # Optional context
    artifact_id: str | None = None
    artifact_title: str | None = None
    chat_user_message: str | None = None
    chat_assistant_message: str | None = None

    # Submitter info
    submitter_name: str | None = None
    submitter_email: str | None = None

    # Admin
    admin_notes: str | None = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None


class FeedbackStatusUpdateRequest(BaseModel):
    """Request to update feedback status"""
    status: FeedbackStatus
    admin_notes: str | None = Field(default=None, max_length=2000)
