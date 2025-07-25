from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from app.models.metadata import Artifact
from app.models.pager import Pager
from bson import ObjectId


class Database:
    """
    Database service for the application.
    """

    def __init__(self, uri: str, db_name: str):
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client[db_name]

    def _convert_objectids_to_strings(self, items: list[dict]) -> list[dict]:
        """Convert ObjectId to string in a list of documents."""
        for item in items:
            item = self._convert_single_objectid_to_string(item)
        return items

    def _convert_single_objectid_to_string(self, item: dict | None) -> dict | None:
        """Convert ObjectId to string in a single document."""
        if item and "_id" in item:
            item["_id"] = str(item["_id"])
        return item

    async def get_collection(self, collection_name: str) -> AsyncIOMotorCollection:
        return self.db[collection_name]

    async def get_artifacts_paged(
        self, page: int = 1, page_size: int = 10, search: str = ""
    ) -> Pager[Artifact]:
        """Get artifacts from the database with pagination."""
        # Calculate skip value for pagination
        skip = (page - 1) * page_size

        # Get total count of documents
        total = await self.db.artifacts.count_documents(
            {
                "$or": [
                    {"title": {"$regex": search, "$options": "i"}},
                    {"description": {"$regex": search, "$options": "i"}},
                ]
            }
            if search
            else {}
        )

        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size

        # Get paginated results
        cursor = (
            self.db.artifacts.find(
                {
                    "$or": [
                        {"title": {"$regex": search, "$options": "i"}},
                        {"description": {"$regex": search, "$options": "i"}},
                    ]
                }
                if search
                else {}
            )
            .skip(skip)
            .limit(page_size)
        )
        items = await cursor.to_list(length=page_size)
        artifacts = [Artifact.model_validate(item) for item in items]

        # Calculate pagination metadata
        has_next = page < total_pages
        has_previous = page > 1

        paged = Pager(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous,
            items=artifacts,
        )
        return paged

    async def get_artifacts(self):
        """Get all artifacts from the database."""
        items = await self.db.artifacts.find().to_list(length=None)
        return self._convert_objectids_to_strings(items)

    async def get_artifact(self, artifact_id: str):
        """Get an artifact from the database."""

        item = await self.db.artifacts.find_one({"_id": ObjectId(artifact_id)})
        return Artifact.model_validate(item)

    async def insert_artifact(self, artifact: Artifact):
        """Insert an artifact into the database."""
        a = Artifact.create(artifact)
        ior = await self.db.artifacts.insert_one(a.model_dump())
        return {"id": str(ior.inserted_id)}

    async def update_artifact(self, artifact: Artifact):
        """Update an artifact in the database."""
        prev_artifact = await self.get_artifact(artifact.id)
        print(prev_artifact)
        print("XX", artifact)
        a = Artifact.update(prev_artifact, artifact)
        ior = await self.db.artifacts.update_one(
            {"_id": ObjectId(artifact.id)}, {"$set": a.model_dump()}
        )
        return {"updated": str(ior.modified_count)}

    async def close(self):
        """Close the database connection."""
        self.client.close()
