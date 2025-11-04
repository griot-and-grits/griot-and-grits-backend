"""
Collection models for Globus archival storage.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class CollectionStatus(str, Enum):
    """Status of preservation collection"""
    DRAFT = "draft"              # Path assigned, awaiting upload
    UPLOADED = "uploaded"        # User claims upload complete
    VERIFYING = "verifying"      # Server checking files
    SEALED = "sealed"            # Verified and immutable
    FAILED = "failed"            # Verification failed


class Collection(BaseModel):
    """Preservation collection in Globus archive"""

    collection_id: str = Field(description="Unique collection identifier")
    title: str = Field(description="Human-readable collection title")
    slug: str = Field(description="URL-safe slug for path")
    status: CollectionStatus = Field(default=CollectionStatus.DRAFT)

    # Globus location
    globus_path: str = Field(description="Full path in Globus (e.g., /archive/2025-01/slug/)")
    globus_endpoint_id: str = Field(description="Globus endpoint ID")

    # Contents
    expected_artifact_count: int | None = Field(default=None)
    actual_artifact_count: int | None = Field(default=None)
    total_size_bytes: int | None = Field(default=None)

    # Verification
    verification_errors: list[str] = Field(default_factory=list)
    has_manifest: bool = Field(default=False)
    has_package_zip: bool = Field(default=False)

    # Checksums
    collection_checksum_md5: str | None = None
    collection_checksum_sha256: str | None = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    uploaded_at: datetime | None = None
    verified_at: datetime | None = None
    sealed_at: datetime | None = None

    # Metadata
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    creator: str | None = None


class CollectionDraftRequest(BaseModel):
    """Request to create a collection draft"""
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    slug: str | None = Field(default=None, max_length=100, description="Optional custom slug")
    expected_artifact_count: int | None = None
    tags: list[str] = Field(default_factory=list)
    creator: str | None = None


class CollectionDraftResponse(BaseModel):
    """Response when draft is created"""
    collection_id: str
    upload_path: str
    raw_upload_path: str
    globus_endpoint_id: str
    globus_link: str
    status: CollectionStatus
    created_at: datetime


class CollectionVerificationResult(BaseModel):
    """Result of collection verification"""
    collection_id: str
    status: CollectionStatus
    verified_at: datetime | None
    total_size_bytes: int | None
    actual_artifact_count: int | None
    verification_errors: list[str]
    has_manifest: bool
    has_package_zip: bool
