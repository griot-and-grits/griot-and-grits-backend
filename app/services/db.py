from motor.motor_asyncio import AsyncIOMotorClient



class Database:
    def __init__(self, uri: str, db_name: str):
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client[db_name]

    async def get_collection(self, collection_name: str):
        return self.db[collection_name]