from pydantic import BaseModel, Field, ConfigDict


class Base(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)


class ContentInfo(BaseModel):
    genre: str | None = None
    language: str | None = None
    themes: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class ProductionInfo(BaseModel):
    director: str | None = None
    producer: str | None = None
    editor: str | None = None
    speaker: str | None = None
    cinematographer: str | None = None


class Duration(BaseModel):
    minutes: int | None = None
    seconds: int | None = None
    hours: int | None = None


class TypeMetadata(BaseModel):
    duration: Duration | None = None
    file_size_mb: float | None = None


# Inherit from TypeMetadata
class AudioMetadata(TypeMetadata):
    codec: str | None = None
    channels: int | None = None
    sample_rate: str | None = None


# Inherit from TypeMetadata
class VideoMetadata(TypeMetadata):
    format: str | None = None
    resolution_height: int | None = None
    resolution_width: int | None = None
    frame_rate: float | None = None
    codec: str | None = None


class Licensing(BaseModel):
    license_type: str | None = None
    license_url: str | None = None
    rights_holder: str | None = None
    expiration_date: str | None = None


class AIContribution(BaseModel):
    type: str | None = None
    ai_tool: str | None = None
    original_content_percentage: float | None = None
    ai_generated_percentage: float | None = None


class AISpecificMetadata(BaseModel):
    contributions: list[AIContribution] = Field(default_factory=list)
    ethical_considerations: list[str] = Field(default_factory=list)


class ArchivalInfo(BaseModel):
    creation_date: str = Field(description="An exact date or estimate")
    checksum: str | None = None
    storage_location: str | None = None


class ArtifactBase(BaseModel):
    title: str = Field(
        description="The title of the artifact.",
        min_length=1,
        max_length=255,
    )
    description: str = Field(
        description="A description of the artifact.", max_length=1000
    )
    meta: AudioMetadata | VideoMetadata | None = None
    content: ContentInfo | None = None
    recorded_date: str = Field(
        description="Date that this artifact was recorded into library"
    )
    archival_info: ArchivalInfo
    ai_specific_metadata: AISpecificMetadata | None = Field(
        description="If any AI was related to enhancing or processing this artifact."
    )
    licensing: Licensing | None = None


class ArtifactCreate(ArtifactBase):
    """
    ArtifactCreate is the model for creating an artifact.
    """

    ...


class Artifact(ArtifactBase):
    version: int = 0

    @classmethod
    def create(cls, artifact: ArtifactCreate):
        return cls(**{**artifact.model_dump(), "version": 1})

    @classmethod
    def update(cls, artifact: ArtifactBase, update: ArtifactCreate):
        return cls(
            **{
                **artifact.model_dump(),
                **update.model_dump(),
                "version": artifact.version + 1,
            }
        )


class ArtifactGroup(BaseModel):
    ids: list[str] = Field(description="The unique identifiers for the artifact.")
