from fastapi import APIRouter, Query
from app.models.metadata import Artifact
from app.factory import factory

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.post("/")
async def new_artifact(
    artifact: Artifact,
):
    return await factory.db.insert_artifact(artifact)


@router.get("/")
async def get_artifacts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1),
):
    return await factory.db.get_artifacts_paged(page, page_size)
