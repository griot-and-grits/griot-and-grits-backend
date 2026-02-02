from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from typing import Optional
from pydantic import BaseModel, Field
import json
from app.models.metadata import Artifact, ArtifactStatus
from app.models.ingestion import IngestionMetadata, IngestionResponse, ArtifactStatusResponse
from app.services.artifact_validator import validate_artifact_for_approval
from app.factory import factory


# New request/response models for artifact-collection linking
class ApproveArtifactRequest(BaseModel):
    approved_by: str = Field(description="User who is approving the artifact")


class BulkMetadataUpdateRequest(BaseModel):
    artifact_ids: list[str] = Field(description="List of artifact IDs to update")
    metadata_updates: dict = Field(description="Metadata fields to update")


class BulkMetadataUpdateResponse(BaseModel):
    updated_count: int
    artifact_ids: list[str]

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.post("/ingest", response_model=IngestionResponse)
async def ingest_artifact(
    file: UploadFile = File(..., description="Artifact file to upload"),
    metadata: str = Form(..., description="JSON-encoded ingestion metadata"),
    collection_id: Optional[str] = Form(None, description="Optional collection ID to link artifact to"),
):
    """
    Ingest a new artifact with file upload and metadata.

    This endpoint handles:
    - File upload to hot storage (MinIO)
    - Checksum calculation for integrity verification
    - Metadata extraction and preservation event logging
    - Storage location tracking
    - Optional linking to collection (NEW)

    Args:
        file: The artifact file (video, audio, document, etc.)
        metadata: JSON string containing IngestionMetadata fields
        collection_id: Optional collection ID to link this artifact to

    Returns:
        IngestionResponse with artifact ID and status
    """
    try:
        # Parse metadata JSON
        metadata_dict = json.loads(metadata)
        ingestion_metadata = IngestionMetadata(**metadata_dict)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in metadata field")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid metadata: {str(e)}")

    try:
        response = await factory.ingestion_service.ingest_artifact(
            file=file,
            metadata=ingestion_metadata,
            agent="api",
        )

        # If collection_id provided, link artifact to collection
        if collection_id:
            artifact_id = response.artifact_id
            await factory.db.link_artifact_to_collection(artifact_id, collection_id)
            await factory.db.update_collection_artifact_counts(collection_id)

            # Update artifact to set ingestion_source and collection_id
            await factory.db.update_artifact(artifact_id, {
                "collection_id": collection_id,
                "ingestion_source": "api",
            })

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.get("/{artifact_id}/status", response_model=ArtifactStatusResponse)
async def get_artifact_status(artifact_id: str):
    """
    Get the processing status of an artifact.

    Args:
        artifact_id: Artifact identifier

    Returns:
        Current status and processing progress
    """
    try:
        status_info = await factory.ingestion_service.get_artifact_status(artifact_id)

        return ArtifactStatusResponse(
            artifact_id=artifact_id,
            status=ArtifactStatus(status_info["status"]),
            processing_progress=status_info.get("processing_metadata", {}),
            last_updated=status_info.get("updated_at"),
            errors=[],
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {str(e)}")


@router.get("/drafts")
async def list_draft_artifacts(
    collection_id: Optional[str] = Query(None, description="Filter by collection"),
    limit: Optional[int] = Query(50, ge=1, le=100, description="Maximum number of results"),
    skip: Optional[int] = Query(0, ge=0, description="Number of results to skip"),
):
    """
    List draft artifacts (status=DRAFT) with optional collection filter.

    Draft artifacts are created when files are uploaded via Globus bulk upload
    and require admin approval before they become ready.

    Args:
        collection_id: Optional filter by collection
        limit: Maximum number of artifacts to return
        skip: Number of artifacts to skip for pagination

    Returns:
        List of draft artifacts with total count and pending count
    """
    artifacts, total = await factory.db.get_draft_artifacts(collection_id, skip, limit)

    # Convert MongoDB ObjectId to string and rename _id to artifact_id
    for artifact in artifacts:
        if "_id" in artifact:
            artifact["artifact_id"] = str(artifact["_id"])
            del artifact["_id"]

    return {
        "artifacts": artifacts,
        "total": total,
        "pending_count": total,  # For draft endpoint, total == pending
    }


@router.get("/{artifact_id}")
async def get_artifact(artifact_id: str):
    """
    Get full artifact metadata by ID.

    Args:
        artifact_id: Artifact identifier

    Returns:
        Complete artifact document
    """
    artifact = await factory.db.get_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    # Convert MongoDB ObjectId to string and rename _id to artifact_id
    if "_id" in artifact:
        artifact["artifact_id"] = str(artifact["_id"])
        del artifact["_id"]

    return artifact


@router.get("/")
async def list_artifacts(
    limit: Optional[int] = Query(50, ge=1, le=100, description="Maximum number of results"),
    skip: Optional[int] = Query(0, ge=0, description="Number of results to skip"),
    status: Optional[ArtifactStatus] = Query(None, description="Filter by status"),
):
    """
    List artifacts with pagination and filtering.

    Args:
        limit: Maximum number of artifacts to return (default 50, max 100)
        skip: Number of artifacts to skip for pagination
        status: Filter by artifact status

    Returns:
        List of artifacts
    """
    if status:
        artifacts = await factory.db.get_artifacts_by_status(status)
        # Apply pagination manually
        artifacts = artifacts[skip : skip + limit]
    else:
        artifacts = await factory.db.get_artifacts(limit=limit, skip=skip)

    # Convert MongoDB ObjectId to string and rename _id to artifact_id
    for artifact in artifacts:
        if "_id" in artifact:
            artifact["artifact_id"] = str(artifact["_id"])
            del artifact["_id"]

    return {
        "total": len(artifacts),
        "limit": limit,
        "skip": skip,
        "artifacts": artifacts,
    }


@router.post("/{artifact_id}/approve")
async def approve_draft_artifact(
    artifact_id: str,
    request: ApproveArtifactRequest,
):
    """
    Approve a draft artifact, changing status from DRAFT to READY.

    Validates that the artifact has minimum required metadata before approval.

    Args:
        artifact_id: Artifact identifier
        request: Approval request with approved_by field

    Returns:
        Updated artifact
    """
    # Get artifact first to validate
    artifact = await factory.db.get_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    # Check if it's a draft
    if artifact.get("status") != ArtifactStatus.DRAFT.value:
        raise HTTPException(
            status_code=400,
            detail=f"Artifact is not in DRAFT status (current: {artifact.get('status')})"
        )

    # Validate metadata
    is_valid, error_msg = validate_artifact_for_approval(artifact)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Cannot approve: {error_msg}")

    # Approve the artifact
    updated_artifact = await factory.db.approve_artifact(artifact_id, request.approved_by)
    if not updated_artifact:
        raise HTTPException(status_code=404, detail="Failed to approve artifact")

    # Update collection counts if artifact belongs to a collection
    if updated_artifact.get("collection_id"):
        await factory.db.update_collection_artifact_counts(updated_artifact["collection_id"])

    # Convert MongoDB ObjectId to string
    if "_id" in updated_artifact:
        updated_artifact["artifact_id"] = str(updated_artifact["_id"])
        del updated_artifact["_id"]

    return updated_artifact


@router.post("/bulk-metadata", response_model=BulkMetadataUpdateResponse)
async def bulk_update_metadata(request: BulkMetadataUpdateRequest):
    """
    Update metadata for multiple artifacts at once (safe bulk operation).

    Only updates shared metadata fields. Does NOT update unique fields like title.

    Allowed fields:
    - creator, rights, subject, creation_date, language, type

    Args:
        request: Bulk update request with artifact IDs and metadata updates

    Returns:
        Count of artifacts updated and list of IDs
    """
    # Validate that only safe fields are being updated
    safe_fields = {"creator", "rights", "subject", "creation_date", "language", "type"}
    requested_fields = set(request.metadata_updates.keys())

    unsafe_fields = requested_fields - safe_fields
    if unsafe_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot bulk update these fields: {unsafe_fields}. Only {safe_fields} are allowed."
        )

    if not request.artifact_ids:
        raise HTTPException(status_code=400, detail="No artifact IDs provided")

    # Perform bulk update
    updated_count = await factory.db.bulk_update_artifact_metadata(
        request.artifact_ids,
        request.metadata_updates
    )

    return BulkMetadataUpdateResponse(
        updated_count=updated_count,
        artifact_ids=request.artifact_ids
    )


@router.post("/")
async def new_artifact(
    artifact: Artifact,
):
    """
    Legacy endpoint for creating artifacts directly (backwards compatibility).
    Consider using /ingest endpoint for new implementations.
    """
    return await factory.db.insert_artifact("artifacts", artifact)
