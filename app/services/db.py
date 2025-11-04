from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from datetime import datetime
from bson import ObjectId
from app.models.metadata import (
    Artifact,
    ArtifactStatus,
    StorageLocation,
    PreservationEvent,
    StorageType,
)
from app.models.collection import Collection, CollectionStatus


class Database:
    """
    Database service for the application.
    Enhanced with preservation metadata support.
    """

    def __init__(self, uri: str, db_name: str):
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client[db_name]
        self._indexes_created = False

    async def _ensure_indexes(self):
        """Create database indexes for optimized queries"""
        if self._indexes_created:
            return

        # Indexes for artifact queries
        await self.db.artifacts.create_index("status")
        await self.db.artifacts.create_index("created_at")
        await self.db.artifacts.create_index([("title", "text"), ("description", "text")])
        await self.db.artifacts.create_index("storage_locations.checksum_sha256")

        # Indexes for collection queries
        await self.db.collections.create_index("collection_id", unique=True)
        await self.db.collections.create_index("status")
        await self.db.collections.create_index("slug", unique=True)
        await self.db.collections.create_index("created_at")

        self._indexes_created = True

    async def get_collection(self, collection_name: str) -> AsyncIOMotorCollection:
        return self.db[collection_name]

    async def get_artifacts(self, limit: int | None = None, skip: int = 0):
        """
        Get all artifacts from the database with pagination.

        Args:
            limit: Maximum number of artifacts to return
            skip: Number of artifacts to skip

        Returns:
            List of artifact documents
        """
        await self._ensure_indexes()
        query = self.db.artifacts.find().skip(skip)
        if limit:
            query = query.limit(limit)
        return await query.to_list(length=None)

    async def get_artifact(self, artifact_id: str):
        """
        Get an artifact from the database by ID.

        Args:
            artifact_id: Artifact identifier

        Returns:
            Artifact document or None if not found
        """
        try:
            return await self.db.artifacts.find_one({"_id": ObjectId(artifact_id)})
        except Exception:
            # If ID is not a valid ObjectId, try as string
            return await self.db.artifacts.find_one({"_id": artifact_id})

    async def get_artifacts_by_status(self, status: ArtifactStatus):
        """
        Get artifacts by processing status.

        Args:
            status: Artifact status to filter by

        Returns:
            List of artifact documents
        """
        await self._ensure_indexes()
        return await self.db.artifacts.find({"status": status.value}).to_list(length=None)

    async def insert_artifact(self, collection: str, artifact: Artifact):
        """
        Insert an artifact into the database.

        Args:
            collection: Collection name (kept for backwards compatibility)
            artifact: Artifact object to insert

        Returns:
            Dictionary with inserted artifact ID
        """
        await self._ensure_indexes()
        artifact_dict = artifact.model_dump(mode="json")
        ior = await self.db.artifacts.insert_one(artifact_dict)
        return {"id": str(ior.inserted_id)}

    async def update_artifact_status(
        self, artifact_id: str, status: ArtifactStatus
    ) -> bool:
        """
        Update the status of an artifact.

        Args:
            artifact_id: Artifact identifier
            status: New status

        Returns:
            True if updated successfully
        """
        try:
            oid = ObjectId(artifact_id)
        except Exception:
            oid = artifact_id

        result = await self.db.artifacts.update_one(
            {"_id": oid},
            {
                "$set": {
                    "status": status.value,
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        return result.modified_count > 0

    async def add_storage_location(
        self, artifact_id: str, location: StorageLocation
    ) -> bool:
        """
        Add a storage location to an artifact.

        Args:
            artifact_id: Artifact identifier
            location: StorageLocation object

        Returns:
            True if added successfully
        """
        try:
            oid = ObjectId(artifact_id)
        except Exception:
            oid = artifact_id

        result = await self.db.artifacts.update_one(
            {"_id": oid},
            {
                "$push": {"storage_locations": location.model_dump(mode="json")},
                "$set": {"updated_at": datetime.utcnow()},
            },
        )
        return result.modified_count > 0

    async def add_preservation_event(
        self, artifact_id: str, event: PreservationEvent
    ) -> bool:
        """
        Add a preservation event to an artifact.

        Args:
            artifact_id: Artifact identifier
            event: PreservationEvent object

        Returns:
            True if added successfully
        """
        try:
            oid = ObjectId(artifact_id)
        except Exception:
            oid = artifact_id

        result = await self.db.artifacts.update_one(
            {"_id": oid},
            {
                "$push": {"preservation_events": event.model_dump(mode="json")},
                "$set": {"updated_at": datetime.utcnow()},
            },
        )
        return result.modified_count > 0

    async def update_storage_location_verification(
        self, artifact_id: str, storage_type: StorageType, verified_at: datetime
    ) -> bool:
        """
        Update the verification timestamp for a storage location.

        Args:
            artifact_id: Artifact identifier
            storage_type: Type of storage to update
            verified_at: Verification timestamp

        Returns:
            True if updated successfully
        """
        try:
            oid = ObjectId(artifact_id)
        except Exception:
            oid = artifact_id

        result = await self.db.artifacts.update_one(
            {
                "_id": oid,
                "storage_locations.storage_type": storage_type.value,
            },
            {
                "$set": {
                    "storage_locations.$.verified_at": verified_at,
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        return result.modified_count > 0

    async def update_artifact(self, artifact_id: str, updates: dict) -> bool:
        """
        Update arbitrary fields on an artifact.

        Args:
            artifact_id: Artifact identifier
            updates: Dictionary of fields to update

        Returns:
            True if updated successfully
        """
        try:
            oid = ObjectId(artifact_id)
        except Exception:
            oid = artifact_id

        updates["updated_at"] = datetime.utcnow()
        result = await self.db.artifacts.update_one(
            {"_id": oid},
            {"$set": updates},
        )
        return result.modified_count > 0

    # ===== Collection Management Methods =====

    async def insert_collection(self, package: Collection):
        """
        Insert a preservation package.

        Args:
            package: Collection object

        Returns:
            Dictionary with inserted collection ID
        """
        await self._ensure_indexes()
        package_dict = package.model_dump(mode="json")
        result = await self.db.collections.insert_one(package_dict)
        return {"id": str(result.inserted_id)}

    async def get_collection(self, collection_id: str) -> dict | None:
        """
        Get collection by collection_id.

        Args:
            collection_id: Collection identifier

        Returns:
            Collection document or None
        """
        return await self.db.collections.find_one({"collection_id": collection_id})

    async def get_collection_by_slug(self, slug: str) -> dict | None:
        """
        Get collection by slug.

        Args:
            slug: Collection slug

        Returns:
            Collection document or None
        """
        return await self.db.collections.find_one({"slug": slug})

    async def update_collection(self, collection_id: str, updates: dict) -> bool:
        """
        Update collection fields.

        Args:
            collection_id: Collection identifier
            updates: Dictionary of fields to update

        Returns:
            True if updated successfully
        """
        updates["updated_at"] = datetime.utcnow()
        result = await self.db.collections.update_one(
            {"collection_id": collection_id},
            {"$set": updates}
        )
        return result.modified_count > 0

    async def list_collections(
        self,
        status: CollectionStatus | None = None,
        limit: int = 50,
        skip: int = 0
    ) -> list[dict]:
        """
        List packages with optional status filter.

        Args:
            status: Optional status filter
            limit: Maximum number of packages
            skip: Number to skip for pagination

        Returns:
            List of collection documents
        """
        await self._ensure_indexes()
        query = {"status": status.value} if status else {}
        cursor = self.db.collections.find(query).skip(skip).limit(limit).sort("created_at", -1)
        return await cursor.to_list(length=None)

    async def count_collections(self, status: CollectionStatus | None = None) -> int:
        """
        Count packages with optional status filter.

        Args:
            status: Optional status filter

        Returns:
            Number of packages
        """
        query = {"status": status.value} if status else {}
        return await self.db.collections.count_documents(query)

    async def close(self):
        """Close the database connection."""
        self.client.close()
