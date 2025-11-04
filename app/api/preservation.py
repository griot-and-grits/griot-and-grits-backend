from fastapi import APIRouter, HTTPException
from app.factory import factory

router = APIRouter(prefix="/preservation", tags=["preservation"])


@router.get("/artifacts/{artifact_id}/events")
async def get_preservation_events(artifact_id: str):
    """
    Get all preservation events for an artifact.

    Preservation events provide an audit trail of all activities
    performed on the artifact (ingestion, validation, replication, etc.)

    Args:
        artifact_id: Artifact identifier

    Returns:
        List of preservation events
    """
    try:
        events = await factory.preservation_event_service.get_events(artifact_id)
        return {"artifact_id": artifact_id, "events": events}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {str(e)}")


@router.get("/artifacts/{artifact_id}/storage-locations")
async def get_storage_locations(artifact_id: str):
    """
    Get all storage locations for an artifact.

    Returns information about where the artifact is stored
    (hot storage/MinIO, archive/Globus, etc.)

    Args:
        artifact_id: Artifact identifier

    Returns:
        List of storage locations with checksums and verification timestamps
    """
    try:
        locations = await factory.storage_location_service.get_locations(artifact_id)
        return {
            "artifact_id": artifact_id,
            "locations": locations,
            "total_copies": len(locations),
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {str(e)}")


@router.post("/artifacts/{artifact_id}/replicate")
async def replicate_to_archive(artifact_id: str):
    """
    Trigger replication of artifact from hot storage to archive.

    This initiates a background process to copy the artifact
    from MinIO to BU Globus for long-term preservation.

    Args:
        artifact_id: Artifact identifier

    Returns:
        Replication status
    """
    try:
        result = await factory.storage_location_service.replicate_to_archive(artifact_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Replication failed: {str(e)}")


@router.post("/artifacts/{artifact_id}/validate-fixity")
async def validate_fixity(artifact_id: str):
    """
    Validate the integrity of an artifact by recalculating checksums.

    This performs a fixity check to ensure the artifact hasn't been corrupted.
    NOTE: For large files, this downloads the file from storage and may take time.

    Args:
        artifact_id: Artifact identifier

    Returns:
        Fixity validation result
    """
    # TODO: Implement full fixity validation
    # This would require downloading from storage and recalculating checksums
    raise HTTPException(
        status_code=501,
        detail="Fixity validation not yet implemented. Use storage-level integrity checks.",
    )


@router.get("/artifacts/{artifact_id}/fixity")
async def get_fixity_info(artifact_id: str):
    """
    Get fixity information (checksums) for an artifact.

    Args:
        artifact_id: Artifact identifier

    Returns:
        Fixity information including checksums and calculation timestamps
    """
    try:
        artifact = await factory.db.get_artifact(artifact_id)
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found")

        fixity = artifact.get("fixity")
        if not fixity:
            raise HTTPException(
                status_code=404, detail="No fixity information available"
            )

        return {"artifact_id": artifact_id, "fixity": fixity}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving fixity: {str(e)}")
