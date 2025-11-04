import os
import io
from datetime import datetime
from typing import BinaryIO
from fastapi import UploadFile

from app.models.ingestion import IngestionMetadata, IngestionResponse
from app.models.metadata import (
    Artifact,
    ArtifactCreate,
    ArtifactStatus,
    ArchivalInfo,
    StorageType,
    PreservationEventType,
    PreservationEventOutcome,
)
from app.services.db import Database
from app.services.fixity_service import FixityService
from app.services.storage_location_service import StorageLocationService
from app.services.preservation_event_service import PreservationEventService
from app.services.object_storage import ObjectStorage
from app.config.settings import Settings


class IngestionService:
    """
    Core orchestrator for artifact ingestion.
    Handles the complete pipeline: upload → checksum → storage → metadata → events
    """

    def __init__(
        self,
        db: Database,
        storage: ObjectStorage,
        settings: Settings,
    ):
        self.db = db
        self.storage = storage
        self.settings = settings

        # Initialize supporting services
        self.fixity_service = FixityService()
        self.storage_location_service = StorageLocationService(db)
        self.preservation_event_service = PreservationEventService(db)

    async def ingest_artifact(
        self,
        file: UploadFile,
        metadata: IngestionMetadata,
        agent: str = "api",
    ) -> IngestionResponse:
        """
        Ingest an artifact with metadata and file upload.
        This is the main entry point for artifact ingestion.

        Process:
        1. Validate metadata
        2. Calculate checksums while streaming to storage
        3. Create artifact record with PROCESSING status
        4. Store file to hot storage (MinIO)
        5. Register storage location
        6. Log ingestion event
        7. Return artifact ID and status

        Args:
            file: Uploaded file
            metadata: User-submitted metadata
            agent: Agent performing the ingestion (e.g., "api", "user:email")

        Returns:
            IngestionResponse with artifact ID and status

        Raises:
            IngestionServiceError: If ingestion fails at any step
        """
        try:
            # Step 1: Read file content and calculate checksums
            file_content = await file.read()
            file_stream = io.BytesIO(file_content)
            file_size = len(file_content)

            checksums = self.fixity_service.calculate_checksums_sync(file_stream)
            fixity_info = self.fixity_service.generate_fixity_info(checksums)

            # Step 2: Create initial artifact record with PROCESSING status
            artifact = await self._create_artifact_record(metadata, fixity_info)
            result = await self.db.insert_artifact("artifacts", artifact)
            artifact_id = result["id"]

            # Step 3: Upload to hot storage (MinIO)
            storage_path = self.storage_location_service.build_storage_path(
                artifact_id=artifact_id,
                filename=file.filename or "artifact",
                storage_type=StorageType.HOT,
            )

            # Reset stream for upload
            file_stream.seek(0)

            # Upload to MinIO
            await self._upload_to_storage(
                file_stream=file_stream,
                storage_path=storage_path,
                metadata=metadata,
            )

            # Step 4: Register storage location
            await self.storage_location_service.register_location(
                artifact_id=artifact_id,
                storage_type=StorageType.HOT,
                path=storage_path,
                size_bytes=file_size,
                checksum_md5=checksums["md5"],
                checksum_sha256=checksums["sha256"],
                bucket=self.settings.storage.bucket,
                endpoint=self.settings.storage.endpoint,
            )

            # Step 5: Log ingestion event
            await self.preservation_event_service.log_ingestion(
                artifact_id=artifact_id,
                outcome=PreservationEventOutcome.SUCCESS,
                storage_path=storage_path,
                agent=agent,
            )

            # Step 6: Update status to READY (or PROCESSING if background tasks are needed)
            final_status = ArtifactStatus.READY
            if self.settings.processing.enable_metadata_extraction:
                final_status = ArtifactStatus.PROCESSING

            await self.db.update_artifact_status(artifact_id, final_status)

            return IngestionResponse(
                artifact_id=artifact_id,
                status=final_status,
                message=f"Artifact ingested successfully to {storage_path}",
                storage_path=storage_path,
            )

        except Exception as e:
            # Log failure event if artifact was created
            if "artifact_id" in locals():
                await self.preservation_event_service.log_event(
                    artifact_id=artifact_id,
                    event_type=PreservationEventType.INGESTION,
                    outcome=PreservationEventOutcome.FAILURE,
                    agent=agent,
                    detail=f"Ingestion failed: {str(e)}",
                )
                await self.db.update_artifact_status(artifact_id, ArtifactStatus.FAILED)

            raise IngestionServiceError(f"Ingestion failed: {str(e)}")

    async def _create_artifact_record(
        self, metadata: IngestionMetadata, fixity_info
    ) -> Artifact:
        """
        Create an Artifact record from user-submitted metadata.

        Args:
            metadata: User-submitted ingestion metadata
            fixity_info: Calculated fixity information

        Returns:
            Artifact object
        """
        # Build archival info
        archival_info = ArchivalInfo(
            creation_date=metadata.creation_date,
            checksum=fixity_info.checksum_sha256,
            storage_location="pending",  # Will be updated after upload
        )

        # Create ArtifactCreate model
        artifact_create = ArtifactCreate(
            title=metadata.title,
            description=metadata.description,
            recorded_date=datetime.utcnow().isoformat(),
            archival_info=archival_info,
            content=metadata.content,
            licensing=metadata.licensing,
            ai_specific_metadata=metadata.ai_metadata,
        )

        # Create Artifact with preservation metadata
        artifact = Artifact.create(artifact_create)
        artifact.status = ArtifactStatus.PROCESSING
        artifact.fixity = fixity_info
        artifact.processing_metadata = {
            "creator": metadata.creator,
            "notes": metadata.notes,
            "ingestion_start": datetime.utcnow().isoformat(),
        }

        return artifact

    async def _upload_to_storage(
        self,
        file_stream: BinaryIO,
        storage_path: str,
        metadata: IngestionMetadata,
    ) -> None:
        """
        Upload file to object storage.

        Args:
            file_stream: File content as stream
            storage_path: Path in storage
            metadata: User metadata for S3 metadata tags

        Raises:
            IngestionServiceError: If upload fails
        """
        try:
            # Save stream to temporary file for minio upload
            temp_path = f"/tmp/{os.path.basename(storage_path)}"
            with open(temp_path, "wb") as f:
                f.write(file_stream.read())

            # Upload to MinIO
            storage_metadata = {
                "title": metadata.title,
                "creator": metadata.creator,
                "creation-date": metadata.creation_date,
            }

            self.storage.upload_file(
                bucket=self.settings.storage.bucket,
                file_path=temp_path,
                s3_path=storage_path,
                meta=storage_metadata,
            )

            # Clean up temp file
            os.remove(temp_path)

        except Exception as e:
            raise IngestionServiceError(f"Storage upload failed: {str(e)}")

    async def finalize_ingestion(self, artifact_id: str) -> bool:
        """
        Mark an artifact as READY after background processing completes.

        Args:
            artifact_id: Artifact identifier

        Returns:
            True if finalized successfully
        """
        return await self.db.update_artifact_status(artifact_id, ArtifactStatus.READY)

    async def get_artifact_status(self, artifact_id: str) -> dict:
        """
        Get the current status and processing progress of an artifact.

        Args:
            artifact_id: Artifact identifier

        Returns:
            Dictionary with status information
        """
        artifact = await self.db.get_artifact(artifact_id)
        if not artifact:
            raise IngestionServiceError(f"Artifact not found: {artifact_id}")

        return {
            "artifact_id": artifact_id,
            "status": artifact.get("status"),
            "processing_metadata": artifact.get("processing_metadata", {}),
            "created_at": artifact.get("created_at"),
            "updated_at": artifact.get("updated_at"),
        }


class IngestionServiceError(Exception):
    """Exception raised by IngestionService"""

    pass
