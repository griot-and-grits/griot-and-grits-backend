"""
Artifact validation utilities for approval workflow.
"""

from app.models.metadata import Artifact


def validate_artifact_for_approval(artifact: Artifact | dict) -> tuple[bool, str | None]:
    """
    Validate that an artifact has minimum required metadata before approval.

    Args:
        artifact: Artifact object or dict

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Handle both Artifact objects and dicts
    if isinstance(artifact, dict):
        title = artifact.get("title", "").strip()
        artifact_type = artifact.get("type")
        artifact_format = artifact.get("format")
    else:
        title = getattr(artifact, "title", "").strip()
        artifact_type = getattr(artifact, "type", None)
        artifact_format = getattr(artifact, "format", None)

    # Required fields for approval
    if not title:
        return False, "Title is required"

    # Type is recommended but not strictly required
    # (it can be inferred from format during approval)

    # Format should at least be present (file extension)
    if not artifact_format:
        return False, "Format/file extension is required"

    return True, None
