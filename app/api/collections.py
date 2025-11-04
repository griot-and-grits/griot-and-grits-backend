"""
API endpoints for preservation collections.
"""

from fastapi import APIRouter, HTTPException, Query
from app.models.collection import (
    CollectionDraftRequest,
    CollectionDraftResponse,
    CollectionStatus,
    CollectionVerificationResult,
    Collection,
)
from app.factory import factory
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collections", tags=["collections"])


@router.post("/draft", response_model=CollectionDraftResponse)
async def create_collection_draft(request: CollectionDraftRequest):
    """
    Create a new preservation collection draft.

    Returns upload instructions and Globus path for user to upload files.
    **The directory structure (raw/ and processed/) will be automatically created in Globus.**

    **User workflow:**
    1. Call this endpoint to create a draft (directory structure auto-created)
    2. Upload files to Globus at {upload_path}/raw/ (REQUIRED)
    3. Optionally add manifest.json at {upload_path}/ root
    4. Call POST /collections/{id}/finalize when upload is complete

    **Directory structure:**
    - {upload_path}/raw/          - Upload original/unedited files here (REQUIRED)
    - {upload_path}/processed/    - Created by processing jobs (DO NOT USE)
    - {upload_path}/manifest.json - Optional metadata file
    """
    if not factory.collection_service:
        raise HTTPException(
            status_code=503,
            detail="Collection service not available. Globus may not be enabled."
        )

    try:
        collection = await factory.collection_service.create_draft(request)

        # Generate direct Globus web link with URL-encoded path
        from urllib.parse import quote
        raw_path = f"{collection.globus_path}raw/"
        globus_url = (
            f"https://app.globus.org/file-manager"
            f"?origin_id={collection.globus_endpoint_id}"
            f"&origin_path={quote(raw_path)}"
            f"&two_pane=false"
        )

        return CollectionDraftResponse(
            collection_id=collection.collection_id,
            upload_path=collection.globus_path,
            raw_upload_path=raw_path,
            globus_endpoint_id=collection.globus_endpoint_id,
            globus_link=globus_url,
            status=collection.status,
            created_at=collection.created_at,
        )
    except Exception as e:
        logger.error(f"Failed to create collection draft: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{collection_id}/finalize", response_model=CollectionVerificationResult)
async def finalize_collection(collection_id: str):
    """
    Verify and seal a collection after user upload.

    Queries Globus to verify files exist in raw/ folder, then marks collection as sealed.

    **Verification checks:**
    - raw/ folder contains at least one file (REQUIRED - fails if empty)
    - manifest.json exists at root (OPTIONAL - warning if missing)
    - Calculate total size of files in raw/
    - Count files in raw/

    **Status transitions:**
    - DRAFT → VERIFYING → SEALED (success, files found in raw/)
    - DRAFT → VERIFYING → SEALED with warning (success, but manifest.json missing)
    - DRAFT → VERIFYING → FAILED (raw/ folder is empty or errors)
    """
    if not factory.collection_service:
        raise HTTPException(
            status_code=503,
            detail="Collection service not available. Globus may not be enabled."
        )

    try:
        collection = await factory.collection_service.finalize_collection(collection_id)

        return CollectionVerificationResult(
            collection_id=collection.collection_id,
            status=collection.status,
            verified_at=collection.verified_at,
            total_size_bytes=collection.total_size_bytes,
            actual_artifact_count=collection.actual_artifact_count,
            verification_errors=collection.verification_errors,
            has_manifest=collection.has_manifest,
            has_package_zip=collection.has_package_zip,
        )
    except Exception as e:
        logger.error(f"Failed to finalize collection {collection_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{collection_id}", response_model=Collection)
async def get_collection(collection_id: str):
    """
    Get collection details by ID.

    Returns full collection metadata including verification status.
    """
    if not factory.collection_service:
        raise HTTPException(
            status_code=503,
            detail="Collection service not available. Globus may not be enabled."
        )

    collection = await factory.collection_service.get_collection(collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    return collection


@router.get("/")
async def list_collections(
    status: CollectionStatus | None = Query(default=None, description="Filter by status"),
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of results"),
    skip: int = Query(default=0, ge=0, description="Number of results to skip"),
):
    """
    List collections with optional filtering.

    **Query parameters:**
    - status: Filter by collection status (draft, sealed, failed, etc.)
    - limit: Maximum number of results (1-100, default 50)
    - skip: Number to skip for pagination (default 0)

    **Returns:**
    - collections: List of Collection objects
    - count: Number of collections returned
    - total: Total number of collections matching filter
    """
    if not factory.collection_service:
        raise HTTPException(
            status_code=503,
            detail="Collection service not available. Globus may not be enabled."
        )

    try:
        collections, total = await factory.collection_service.list_collections(status, limit, skip)
        return {
            "collections": collections,
            "count": len(collections),
            "total": total,
        }
    except Exception as e:
        logger.error(f"Failed to list collections: {e}")
        raise HTTPException(status_code=500, detail=str(e))
