from fastapi import APIRouter, Query
from app.models.metadata import Artifact
from app.factory import factory

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.post("/")
async def new_artifact(
    artifact: Artifact,
):
    return await factory.db.insert_artifact("artifacts", artifact)
