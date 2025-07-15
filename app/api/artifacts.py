from fastapi import APIRouter, Query
from app.models.metadata import Artifact

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.post("/")
async def new_artifact(
    artifact: Artifact,
):
    return {"message": "Hello World"}
