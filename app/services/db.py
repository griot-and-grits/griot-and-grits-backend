from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from app.models.metadata import Artifact

class Database:
    """
    Database service for the application.
    """

    def __init__(self, uri: str, db_name: str):
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client[db_name]

    async def get_collection(self, collection_name: str) -> AsyncIOMotorCollection:
        return self.db[collection_name]

    async def get_artifacts(self):
        """Get all artifacts from the database."""
        return await self.db.artifacts.find().to_list(length=None)

    async def get_artifact(self, artifact_id: str):
        """Get an artifact from the database."""
        return await self.db.artifacts.find_one({"_id": artifact_id})

    async def insert_artifact(self, collection: str, artifact: Artifact):
        """Insert an artifact into the database."""
        ior = await self.db.artifacts.insert_one(artifact.model_dump())
        return {"id": str(ior.inserted_id)}

    async def close(self):
        """Close the database connection."""
        self.client.close()
