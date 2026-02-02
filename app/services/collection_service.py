"""
Service for managing preservation collections.
"""

from datetime import datetime
import re
import uuid
from pathlib import Path
from app.models.collection import (
    Collection,
    CollectionDraftRequest,
    CollectionStatus,
)
from app.models.metadata import (
    Artifact,
    ArtifactStatus,
    ArchivalInfo,
)
from app.services.globus_service import GlobusService, GlobusServiceError
from app.services.db import Database
from app.config.settings import Settings
import logging

logger = logging.getLogger(__name__)


class CollectionService:
    """Service for preservation collection lifecycle"""

    def __init__(self, db: Database, globus: GlobusService, settings: Settings):
        self.db = db
        self.globus = globus
        self.settings = settings

    async def create_draft(self, request: CollectionDraftRequest) -> Collection:
        """
        Create a new collection draft.

        1. Generate slug from title (if not provided)
        2. Generate Globus path: /archive/2025-01/{slug}/
        3. Create collection record in database
        4. Return collection with upload instructions

        Args:
            request: PackageDraftRequest with collection metadata

        Returns:
            Collection with DRAFT status
        """
        # Generate or validate slug
        slug = request.slug or self._generate_slug(request.title)

        # Ensure slug is unique
        existing = await self.db.get_collection_by_slug(slug)
        if existing:
            # Append random suffix to make unique
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"

        # Build path: /archive/2025-01/{slug}/
        globus_path = self._build_archive_path(slug)

        # Create collection
        collection = Collection(
            collection_id=self._generate_collection_id(),
            title=request.title,
            slug=slug,
            globus_path=globus_path,
            globus_endpoint_id=self.settings.globus.endpoint_id,
            description=request.description,
            expected_artifact_count=request.expected_artifact_count,
            tags=request.tags or [],
            creator=request.creator,
        )

        # Save to database
        await self.db.insert_collection(collection)

        # Create directory structure in Globus
        # /archive/2025-01/{slug}/
        # ├── raw/       (required - users upload here)
        # └── processed/ (created by jobs)
        try:
            await self.globus.create_directory(globus_path)
            await self.globus.create_directory(f"{globus_path}raw/")
            await self.globus.create_directory(f"{globus_path}processed/")
            logger.info(f"Created Globus directory structure: {globus_path}{{raw/,processed/}}")
        except GlobusServiceError as e:
            logger.warning(f"Failed to create Globus directory structure (non-fatal): {e}")
            # Don't fail the draft creation if directory creation fails
            # User can still create it manually

        logger.info(f"Created collection draft: {collection.collection_id} at {globus_path}")
        return collection

    async def finalize_collection(self, collection_id: str) -> Collection:
        """
        Verify and seal a collection after user upload.

        1. Query Globus for files in raw/ folder
        2. Verify raw/ folder contains files
        3. Calculate total size
        4. Update collection status
        5. Log preservation events

        Args:
            collection_id: Collection identifier

        Returns:
            Updated Collection with verification results
        """
        collection_dict = await self.db.get_collection(collection_id)
        if not collection_dict:
            raise CollectionServiceError(f"Collection not found: {collection_id}")

        collection = Collection(**collection_dict)

        # Update status to verifying
        collection.status = CollectionStatus.VERIFYING
        await self.db.update_collection(collection_id, {"status": collection.status.value})

        try:
            # Verify files exist in Globus raw/ folder
            raw_path = f"{collection.globus_path}raw/"
            logger.info(f"Verifying collection {collection_id} at {raw_path}")

            raw_files = await self.globus.list_directory(raw_path)

            # Check for files at root level (optional manifest.json)
            root_files = await self.globus.list_directory(collection.globus_path)
            root_file_names = {f["name"] for f in root_files if f["type"] == "file"}
            has_manifest = "manifest.json" in root_file_names

            # Count files in raw/
            raw_file_list = [f for f in raw_files if f["type"] == "file"]
            raw_file_count = len(raw_file_list)
            total_size = sum(f.get("size", 0) for f in raw_file_list)

            # Determine status and errors
            verification_errors = []
            warnings = []

            # manifest.json is optional but recommended
            if not has_manifest:
                warnings.append("Warning: manifest.json not found in root (recommended for preservation)")

            # raw/ folder must contain at least one file
            if raw_file_count == 0:
                verification_errors.append("Error: raw/ folder is empty. Upload files to raw/ before finalizing.")

            # Only fail if critical requirements not met
            status = CollectionStatus.SEALED if not verification_errors else CollectionStatus.FAILED

            # Combine errors and warnings for reporting
            all_messages = verification_errors + warnings

            # NEW: Create draft artifacts from files in raw/ folder
            # Only create artifacts for NEW files (not already in artifact_ids)
            created_artifact_count = 0
            if status == CollectionStatus.SEALED and raw_file_count > 0:
                existing_artifact_ids = set(collection.artifact_ids)

                for file_info in raw_file_list:
                    filename = file_info["name"]
                    relative_path = f"raw/{filename}"

                    # Extract metadata from filename
                    metadata = self._extract_metadata_from_filename(filename, file_info)

                    try:
                        # Create draft artifact
                        artifact = Artifact(
                            title=metadata['title'],
                            description=metadata['description'],
                            recorded_date=metadata['recorded_date'],
                            archival_info=ArchivalInfo(**metadata['archival_info']),
                            status=ArtifactStatus.DRAFT,
                            collection_id=collection_id,
                            package_path=relative_path,
                            ingestion_source="globus",
                        )

                        # Insert artifact into database
                        result = await self.db.insert_artifact("artifacts", artifact)
                        artifact_id = result["id"]

                        # Link to collection (adds to artifact_ids)
                        await self.db.link_artifact_to_collection(artifact_id, collection_id)

                        created_artifact_count += 1
                        logger.info(f"Created draft artifact {artifact_id} for file {filename}")

                    except Exception as e:
                        logger.error(f"Failed to create artifact for {filename}: {e}")
                        warnings.append(f"Warning: Could not create artifact for {filename}")

                # Update collection artifact counts
                await self.db.update_collection_artifact_counts(collection_id)

            # Update collection
            now = datetime.utcnow()
            updates = {
                "status": status.value,
                "has_manifest": has_manifest,
                "has_package_zip": False,  # Not used in folder-based approach
                "total_size_bytes": total_size,
                "actual_artifact_count": raw_file_count,
                "verified_at": now,
                "verification_errors": all_messages,
            }

            if status == CollectionStatus.SEALED:
                updates["sealed_at"] = now
                updates["last_sealed_at"] = now
                # Increment seal_count
                updates["seal_count"] = collection.seal_count + 1

            await self.db.update_collection(collection_id, updates)

            # Fetch updated collection
            updated_dict = await self.db.get_collection(collection_id)
            updated_collection = Collection(**updated_dict)

            logger.info(
                f"Collection {collection_id} verification complete. "
                f"Status: {updated_collection.status}, Files in raw/: {raw_file_count}, Messages: {all_messages}"
            )
            return updated_collection

        except GlobusServiceError as e:
            # Mark as failed
            error_msg = f"Globus verification failed: {str(e)}"
            await self.db.update_collection(collection_id, {
                "status": CollectionStatus.FAILED.value,
                "verification_errors": [error_msg]
            })
            logger.error(f"Collection {collection_id} verification failed: {e}")
            raise CollectionServiceError(error_msg)

        except Exception as e:
            # Mark as failed
            error_msg = f"Verification failed: {str(e)}"
            await self.db.update_collection(collection_id, {
                "status": CollectionStatus.FAILED.value,
                "verification_errors": [error_msg]
            })
            logger.error(f"Collection {collection_id} verification failed: {e}")
            raise CollectionServiceError(error_msg)

    async def reseal_collection(self, collection_id: str) -> Collection:
        """
        Re-scan Globus folder and create draft artifacts for NEW files only.
        Compare against existing artifact_ids to avoid duplicates.
        Increment seal_count and update last_sealed_at.

        Args:
            collection_id: Collection identifier

        Returns:
            Updated Collection
        """
        collection_dict = await self.db.get_collection(collection_id)
        if not collection_dict:
            raise CollectionServiceError(f"Collection not found: {collection_id}")

        collection = Collection(**collection_dict)

        try:
            # Get files currently in Globus raw/ folder
            raw_path = f"{collection.globus_path}raw/"
            logger.info(f"Re-sealing collection {collection_id} at {raw_path}")

            raw_files = await self.globus.list_directory(raw_path)
            raw_file_list = [f for f in raw_files if f["type"] == "file"]

            # Get existing artifacts for this collection to avoid duplicates
            existing_artifacts = await self.db.get_artifacts_by_collection(collection_id, limit=1000)
            existing_filenames = {
                art.get("package_path", "").split("/")[-1]
                for art in existing_artifacts
                if art.get("package_path")
            }

            # Create draft artifacts for NEW files only
            created_artifact_count = 0
            for file_info in raw_file_list:
                filename = file_info["name"]

                # Skip if we already have an artifact for this file
                if filename in existing_filenames:
                    continue

                relative_path = f"raw/{filename}"
                metadata = self._extract_metadata_from_filename(filename, file_info)

                try:
                    # Create draft artifact
                    artifact = Artifact(
                        title=metadata['title'],
                        description=metadata['description'],
                        recorded_date=metadata['recorded_date'],
                        archival_info=ArchivalInfo(**metadata['archival_info']),
                        status=ArtifactStatus.DRAFT,
                        collection_id=collection_id,
                        package_path=relative_path,
                        ingestion_source="globus",
                    )

                    # Insert artifact into database
                    result = await self.db.insert_artifact("artifacts", artifact)
                    artifact_id = result["id"]

                    # Link to collection
                    await self.db.link_artifact_to_collection(artifact_id, collection_id)

                    created_artifact_count += 1
                    logger.info(f"Created draft artifact {artifact_id} for new file {filename}")

                except Exception as e:
                    logger.error(f"Failed to create artifact for {filename}: {e}")

            # Update collection artifact counts and seal tracking
            await self.db.update_collection_artifact_counts(collection_id)

            now = datetime.utcnow()
            updates = {
                "last_sealed_at": now,
                "seal_count": collection.seal_count + 1,
                "actual_artifact_count": len(raw_file_list),
                "total_size_bytes": sum(f.get("size", 0) for f in raw_file_list),
            }

            await self.db.update_collection(collection_id, updates)

            # Fetch updated collection
            updated_dict = await self.db.get_collection(collection_id)
            updated_collection = Collection(**updated_dict)

            logger.info(
                f"Collection {collection_id} re-sealed. "
                f"Created {created_artifact_count} new draft artifacts. "
                f"Seal count: {updated_collection.seal_count}"
            )
            return updated_collection

        except GlobusServiceError as e:
            error_msg = f"Globus re-seal failed: {str(e)}"
            logger.error(f"Collection {collection_id} re-seal failed: {e}")
            raise CollectionServiceError(error_msg)

        except Exception as e:
            error_msg = f"Re-seal failed: {str(e)}"
            logger.error(f"Collection {collection_id} re-seal failed: {e}")
            raise CollectionServiceError(error_msg)

    async def get_collection(self, collection_id: str) -> Collection | None:
        """
        Get a collection by ID.

        Args:
            collection_id: Collection identifier

        Returns:
            Collection or None
        """
        collection_dict = await self.db.get_collection(collection_id)
        if not collection_dict:
            return None
        return Collection(**collection_dict)

    async def list_collections(
        self,
        status: CollectionStatus | None = None,
        limit: int = 50,
        skip: int = 0,
    ) -> tuple[list[Collection], int]:
        """
        List collections with optional filtering.

        Args:
            status: Optional status filter
            limit: Maximum number of collections
            skip: Number to skip for pagination

        Returns:
            Tuple of (packages list, total count)
        """
        collections_dicts = await self.db.list_collections(status, limit, skip)
        collections = [Collection(**p) for p in collections_dicts]
        total = await self.db.count_collections(status)
        return collections, total

    def _generate_slug(self, title: str) -> str:
        """Generate URL-safe slug from title"""
        slug = title.lower()
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        slug = slug.strip('-')
        return slug[:50]

    def _build_archive_path(self, slug: str) -> str:
        """Build archive path: /archive/2025-01/{slug}/"""
        month = datetime.utcnow().strftime("%Y-%m")
        base = self.settings.globus.base_path.rstrip('/')
        return f"{base}/{month}/{slug}/"

    def _generate_collection_id(self) -> str:
        """Generate unique collection ID"""
        return f"coll_{uuid.uuid4().hex[:12]}"

    def _extract_metadata_from_filename(self, filepath: str, file_info: dict) -> dict:
        """
        Extract minimal metadata from filename for draft artifacts.

        Args:
            filepath: Relative path within collection (e.g., "interview_1975.mp4")
            file_info: File info dict from Globus with 'name', 'size', etc.

        Returns:
            Dictionary with extracted metadata
        """
        path = Path(filepath)
        filename = path.stem  # without extension
        extension = path.suffix.lstrip('.')

        # Generate title: replace underscores/dashes with spaces, capitalize
        title = filename.replace('_', ' ').replace('-', ' ').title()

        # Infer type from extension
        type_mapping = {
            'mp4': 'video', 'mov': 'video', 'avi': 'video', 'mkv': 'video', 'webm': 'video',
            'mp3': 'audio', 'wav': 'audio', 'flac': 'audio', 'm4a': 'audio', 'aac': 'audio',
            'jpg': 'image', 'jpeg': 'image', 'png': 'image', 'gif': 'image', 'tiff': 'image',
            'pdf': 'document', 'doc': 'document', 'docx': 'document', 'txt': 'document',
        }
        inferred_type = type_mapping.get(extension.lower(), 'other')

        # Get current date as string
        today = datetime.utcnow().strftime("%Y-%m-%d")

        return {
            'title': title,
            'description': f"Uploaded via Globus (auto-generated from filename)",
            'recorded_date': today,
            'archival_info': {
                'creation_date': today,
                'checksum': None,
                'storage_location': filepath,
            },
            'original_filename': file_info['name'],
            'file_extension': extension,
            'format': extension,
            'type': inferred_type,
            'size_bytes': file_info.get('size', 0),
        }


class CollectionServiceError(Exception):
    """Collection service exceptions"""
    pass
