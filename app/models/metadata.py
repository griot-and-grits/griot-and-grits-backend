from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from enum import Enum


class Base(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)


# ============================================
# Preservation & Storage Models
# ============================================


class ArtifactStatus(str, Enum):
    """Processing status of an artifact"""

    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    ARCHIVED = "archived"


class StorageType(str, Enum):
    """Type of storage backend"""

    HOT = "hot"  # MinIO/S3 - frequently accessed
    ARCHIVE = "archive"  # Globus - long-term preservation


class FixityAlgorithm(str, Enum):
    """Checksum algorithms for fixity checking"""

    MD5 = "md5"
    SHA256 = "sha256"
    SHA512 = "sha512"


class FixityInfo(BaseModel):
    """Fixity information for integrity verification"""

    checksum_md5: str = Field(description="MD5 checksum of the file")
    checksum_sha256: str = Field(description="SHA-256 checksum of the file")
    algorithm: list[FixityAlgorithm] = Field(
        default=[FixityAlgorithm.MD5, FixityAlgorithm.SHA256],
        description="Algorithms used for checksum calculation",
    )
    calculated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when checksums were calculated",
    )
    verified_at: datetime | None = Field(
        default=None,
        description="Timestamp of last successful verification",
    )


class StorageLocation(BaseModel):
    """Storage location information for an artifact"""

    storage_type: StorageType = Field(description="Type of storage (hot/archive)")
    path: str = Field(description="Path to the file in storage")
    bucket: str | None = Field(default=None, description="Bucket name (for S3/MinIO)")
    endpoint: str | None = Field(
        default=None, description="Storage endpoint or Globus endpoint ID"
    )
    size_bytes: int = Field(description="File size in bytes")
    checksum_md5: str = Field(description="MD5 checksum at this location")
    checksum_sha256: str = Field(description="SHA-256 checksum at this location")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when file was stored at this location",
    )
    verified_at: datetime | None = Field(
        default=None,
        description="Timestamp of last successful fixity check",
    )


class PreservationEventType(str, Enum):
    """PREMIS-compliant preservation event types"""

    INGESTION = "ingestion"
    VALIDATION = "validation"
    METADATA_EXTRACTION = "metadata_extraction"
    REPLICATION = "replication"
    FIXITY_CHECK = "fixity_check"
    FORMAT_MIGRATION = "format_migration"
    DELETION = "deletion"
    TRANSCRIPTION = "transcription"
    ENHANCEMENT = "enhancement"


class PreservationEventOutcome(str, Enum):
    """Outcome of a preservation event"""

    SUCCESS = "success"
    FAILURE = "failure"
    WARNING = "warning"


class PreservationEvent(BaseModel):
    """PREMIS preservation event for audit trail"""

    event_type: PreservationEventType = Field(description="Type of preservation event")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the event occurred",
    )
    agent: str = Field(
        default="system",
        description="Agent that performed the event (user, system, service)",
    )
    outcome: PreservationEventOutcome = Field(
        description="Outcome of the event (success/failure/warning)"
    )
    detail: str | None = Field(
        default=None, description="Additional details about the event"
    )
    related_object: str | None = Field(
        default=None,
        description="Related object identifier (e.g., storage location, derivative)",
    )


# ============================================
# Content & Descriptive Metadata Models
# ============================================


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
    status: ArtifactStatus = Field(
        default=ArtifactStatus.UPLOADING,
        description="Current processing status of the artifact",
    )
    storage_locations: list[StorageLocation] = Field(
        default_factory=list,
        description="All storage locations for this artifact (hot + archive)",
    )
    preservation_events: list[PreservationEvent] = Field(
        default_factory=list,
        description="Audit trail of all preservation events",
    )
    fixity: FixityInfo | None = Field(
        default=None,
        description="Fixity information for integrity verification",
    )
    processing_metadata: dict = Field(
        default_factory=dict,
        description="Internal metadata for tracking processing pipeline state",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when artifact was created",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when artifact was last updated",
    )

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
                "updated_at": datetime.utcnow(),
            }
        )


class ArtifactGroup(BaseModel):
    ids: list[str] = Field(description="The unique identifiers for the artifact.")
