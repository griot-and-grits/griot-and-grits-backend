from pydantic import BaseModel, Field, ConfigDict


class Base(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)


class ContentInfo(BaseModel):
    genre: str
    language: str | None = None
    themes: list[str] = []
    keywords: list[str] = []


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
    duration: Duration
    production_info: ProductionInfo


# Inherit from TypeMetadata
class AudioMetadata(TypeMetadata):
    codec: str
    channels: str
    sample_rate: str


# Inherit from TypeMetadata
class VideoMetadata(TypeMetadata):
    format: str
    resolution_height: int
    resolution_width: int
    frame_rate: float
    codec: str
    file_size_mb: float


class Licensing(BaseModel):
    license_type: str
    license_url: str
    rights_holder: str | None = None
    expiration_date: str


class AIContribution(BaseModel):
    type: str
    ai_tool: str
    original_content_percentage: float | None = None
    ai_generated_percentage: float | None = None


class AISpecificMetadata(BaseModel):
    contributions: list[AIContribution]
    ethical_considerations: list[str]


class ArchivalInfo(BaseModel):
    creation_date: str = Field(description="An exact date or estimate")
    checksum: str
    storage_location: str


class Artifact(BaseModel):
    title: str
    description: str
    version: str
    content: ContentInfo
    meta: AudioMetadata | VideoMetadata
    recorded_date: str = Field(
        description="Date that this artifact was recorded into library"
    )
    archival_info: ArchivalInfo
    ai_specific_metadata: AISpecificMetadata | None = Field(
        description="If any AI was related to enhancing or processing this artifact."
    )
    licensing: Licensing | None = None
