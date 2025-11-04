from pydantic import BaseModel, Field
from datetime import datetime
from app.models.metadata import (
    ContentInfo,
    ProductionInfo,
    Licensing,
    AISpecificMetadata,
    ArtifactStatus,
)


class IngestionMetadata(BaseModel):
    """
    User-submitted metadata for artifact ingestion.
    This separates required fields from optional enrichment data.
    """

    # Required fields (must be provided by user)
    title: str = Field(
        description="Title of the artifact",
        min_length=1,
        max_length=255,
        examples=["Interview with John Doe", "Civil Rights March 1965"],
    )
    description: str = Field(
        description="Description of the artifact content",
        max_length=2000,
        examples=[
            "An oral history interview discussing experiences during the Civil Rights Movement"
        ],
    )
    creator: str = Field(
        description="Creator or contributor of the artifact",
        min_length=1,
        max_length=255,
        examples=["Jane Smith", "Community Archive Collective"],
    )
    creation_date: str = Field(
        description="Date the original content was created (can be exact or approximate)",
        examples=["1965-03-15", "circa 1960s", "Summer 1972"],
    )

    # Optional fields
    content: ContentInfo | None = Field(
        default=None,
        description="Content classification (genre, language, themes, keywords)",
    )
    production: ProductionInfo | None = Field(
        default=None,
        description="Production information (director, producer, speaker, etc.)",
    )
    licensing: Licensing | None = Field(
        default=None,
        description="Rights and licensing information",
    )
    ai_metadata: AISpecificMetadata | None = Field(
        default=None,
        description="AI contribution metadata if applicable",
    )
    notes: str | None = Field(
        default=None,
        max_length=1000,
        description="Additional notes about the artifact",
    )


class IngestionResponse(BaseModel):
    """Response returned after successful artifact ingestion"""

    artifact_id: str = Field(description="Unique identifier for the ingested artifact")
    status: ArtifactStatus = Field(
        description="Current processing status of the artifact"
    )
    message: str = Field(
        default="Artifact ingestion initiated successfully",
        description="Human-readable status message",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of ingestion",
    )
    storage_path: str | None = Field(
        default=None,
        description="Primary storage path (if available)",
    )


class ArtifactStatusResponse(BaseModel):
    """Response for artifact status queries"""

    artifact_id: str = Field(description="Artifact identifier")
    status: ArtifactStatus = Field(description="Current status")
    processing_progress: dict = Field(
        default_factory=dict,
        description="Detailed processing progress information",
    )
    last_updated: datetime = Field(description="When status was last updated")
    errors: list[str] = Field(
        default_factory=list,
        description="Any errors encountered during processing",
    )
