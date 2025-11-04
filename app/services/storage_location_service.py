from datetime import datetime
from app.models.metadata import StorageLocation, StorageType
from app.services.db import Database


class StorageLocationService:
    """
    Service for managing storage locations across multiple backends.
    Handles dual-tier storage: hot storage (MinIO) and archive (Globus).
    """

    def __init__(self, db: Database):
        self.db = db

    async def register_location(
        self,
        artifact_id: str,
        storage_type: StorageType,
        path: str,
        size_bytes: int,
        checksum_md5: str,
        checksum_sha256: str,
        bucket: str | None = None,
        endpoint: str | None = None,
    ) -> StorageLocation:
        """
        Register a new storage location for an artifact.

        Args:
            artifact_id: Artifact identifier
            storage_type: Type of storage (hot/archive)
            path: Path to the file in storage
            size_bytes: File size in bytes
            checksum_md5: MD5 checksum
            checksum_sha256: SHA-256 checksum
            bucket: Bucket name (for S3/MinIO)
            endpoint: Storage endpoint or Globus endpoint ID

        Returns:
            StorageLocation object

        Raises:
            StorageLocationServiceError: If registration fails
        """
        location = StorageLocation(
            storage_type=storage_type,
            path=path,
            bucket=bucket,
            endpoint=endpoint,
            size_bytes=size_bytes,
            checksum_md5=checksum_md5,
            checksum_sha256=checksum_sha256,
            created_at=datetime.utcnow(),
        )

        # Add location to artifact's storage_locations list
        try:
            await self.db.add_storage_location(artifact_id, location)
        except Exception as e:
            raise StorageLocationServiceError(
                f"Failed to register storage location: {str(e)}"
            )

        return location

    async def get_locations(self, artifact_id: str) -> list[StorageLocation]:
        """
        Get all storage locations for an artifact.

        Args:
            artifact_id: Artifact identifier

        Returns:
            List of StorageLocation objects

        Raises:
            StorageLocationServiceError: If retrieval fails
        """
        try:
            artifact = await self.db.get_artifact(artifact_id)
            if not artifact:
                raise StorageLocationServiceError(
                    f"Artifact not found: {artifact_id}"
                )
            return artifact.get("storage_locations", [])
        except Exception as e:
            raise StorageLocationServiceError(
                f"Failed to retrieve storage locations: {str(e)}"
            )

    async def get_primary_location(
        self, artifact_id: str, storage_type: StorageType = StorageType.HOT
    ) -> StorageLocation | None:
        """
        Get the primary storage location of a specific type.

        Args:
            artifact_id: Artifact identifier
            storage_type: Type of storage to retrieve (defaults to HOT)

        Returns:
            StorageLocation object or None if not found
        """
        locations = await self.get_locations(artifact_id)
        for location in locations:
            if location.get("storage_type") == storage_type.value:
                return StorageLocation(**location)
        return None

    async def update_verification_time(
        self, artifact_id: str, storage_type: StorageType
    ) -> None:
        """
        Update the verified_at timestamp for a storage location.

        Args:
            artifact_id: Artifact identifier
            storage_type: Type of storage that was verified

        Raises:
            StorageLocationServiceError: If update fails
        """
        try:
            await self.db.update_storage_location_verification(
                artifact_id, storage_type, datetime.utcnow()
            )
        except Exception as e:
            raise StorageLocationServiceError(
                f"Failed to update verification time: {str(e)}"
            )

    async def replicate_to_archive(self, artifact_id: str) -> dict:
        """
        Initiate replication from hot storage to archive (Globus).
        This is a stub for future Globus integration.

        Args:
            artifact_id: Artifact identifier

        Returns:
            Dictionary with replication status

        Raises:
            StorageLocationServiceError: If replication fails
        """
        # Get the hot storage location
        hot_location = await self.get_primary_location(
            artifact_id, StorageType.HOT
        )

        if not hot_location:
            raise StorageLocationServiceError(
                f"No hot storage location found for artifact {artifact_id}"
            )

        # TODO: Implement actual Globus transfer logic
        # For now, this is a placeholder that would trigger background replication
        return {
            "status": "pending",
            "message": "Replication to archive storage queued",
            "artifact_id": artifact_id,
            "source_type": "hot",
            "destination_type": "archive",
        }

    def build_storage_path(
        self,
        artifact_id: str,
        filename: str,
        storage_type: StorageType,
        date: datetime | None = None,
    ) -> str:
        """
        Build a consistent storage path for an artifact.
        Uses year/month partitioning for organization.

        Args:
            artifact_id: Artifact identifier
            storage_type: Type of storage
            filename: Original filename
            date: Date to use for partitioning (defaults to now)

        Returns:
            Storage path string
        """
        if date is None:
            date = datetime.utcnow()

        year = date.strftime("%Y")
        month = date.strftime("%m")

        # Format: artifacts/YYYY/MM/artifact_id/filename
        return f"artifacts/{year}/{month}/{artifact_id}/{filename}"


class StorageLocationServiceError(Exception):
    """Exception raised by StorageLocationService"""

    pass
