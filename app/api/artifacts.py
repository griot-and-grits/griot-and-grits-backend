from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from typing import Optional
import json
from app.models.metadata import Artifact, ArtifactStatus
from app.models.ingestion import IngestionMetadata, IngestionResponse, ArtifactStatusResponse
from app.factory import factory

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.post("/ingest", response_model=IngestionResponse)
async def ingest_artifact(
    file: UploadFile = File(..., description="Artifact file to upload"),
    metadata: str = Form(..., description="JSON-encoded ingestion metadata"),
):
    """
    Ingest a new artifact with file upload and metadata.

    This endpoint handles:
    - File upload to hot storage (MinIO)
    - Checksum calculation for integrity verification
    - Metadata extraction and preservation event logging
    - Storage location tracking

    Args:
        file: The artifact file (video, audio, document, etc.)
        metadata: JSON string containing IngestionMetadata fields

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


@router.post("/")
async def new_artifact(
    artifact: Artifact,
):
    """
    Legacy endpoint for creating artifacts directly (backwards compatibility).
    Consider using /ingest endpoint for new implementations.
    """
    return await factory.db.insert_artifact("artifacts", artifact)
