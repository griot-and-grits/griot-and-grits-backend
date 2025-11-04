from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Literal


class DatabaseSettings(BaseSettings):
    """MongoDB database configuration"""

    model_config = SettingsConfigDict(env_prefix="DB_", extra="ignore")

    uri: str = Field(
        description="MongoDB connection URI",
        examples=["mongodb://user:pass@localhost:27017/"],
    )
    name: str = Field(
        default="gngdb",
        description="Database name",
    )
    max_pool_size: int = Field(
        default=10,
        description="Maximum connection pool size",
    )
    min_pool_size: int = Field(
        default=1,
        description="Minimum connection pool size",
    )


class StorageSettings(BaseSettings):
    """MinIO/S3-compatible storage configuration for hot storage"""

    model_config = SettingsConfigDict(env_prefix="STORAGE_", extra="ignore")

    endpoint: str = Field(
        description="MinIO endpoint (e.g., localhost:9000)",
        examples=["localhost:9000", "minio.example.com"],
    )
    access_key: str = Field(
        description="MinIO access key",
    )
    secret_key: str = Field(
        description="MinIO secret key",
    )
    bucket: str = Field(
        default="artifacts",
        description="Default bucket name for artifacts",
    )
    region: str = Field(
        default="us-east-1",
        description="Storage region",
    )
    secure: bool = Field(
        default=True,
        description="Use HTTPS for connections",
    )


class GlobusSettings(BaseSettings):
    """Globus archive storage configuration"""

    model_config = SettingsConfigDict(env_prefix="GLOBUS_", extra="ignore")

    enabled: bool = Field(
        default=False,
        description="Enable Globus archive storage",
    )
    endpoint_id: str | None = Field(
        default=None,
        description="Globus endpoint ID for BU archive",
    )
    base_path: str | None = Field(
        default=None,
        description="Base path on Globus filesystem",
        examples=["/archive/griot-and-grits/"],
    )
    client_id: str | None = Field(
        default=None,
        description="Globus application client ID",
    )
    client_secret: str | None = Field(
        default=None,
        description="Globus application client secret",
    )


class ProcessingSettings(BaseSettings):
    """Background processing and pipeline configuration"""

    model_config = SettingsConfigDict(env_prefix="PROCESSING_", extra="ignore")

    mode: Literal["sync", "async"] = Field(
        default="sync",
        description="Processing mode: sync (immediate) or async (background)",
    )
    celery_broker_url: str | None = Field(
        default=None,
        description="Celery broker URL (Redis/RabbitMQ)",
        examples=["redis://localhost:6379/0"],
    )
    celery_result_backend: str | None = Field(
        default=None,
        description="Celery result backend URL",
        examples=["redis://localhost:6379/0"],
    )
    transcription_api_url: str | None = Field(
        default=None,
        description="Whisper/ASR transcription API endpoint",
    )
    enable_metadata_extraction: bool = Field(
        default=True,
        description="Enable automatic technical metadata extraction",
    )
    enable_transcription: bool = Field(
        default=False,
        description="Enable automatic transcription of audio/video",
    )
    enable_llm_enrichment: bool = Field(
        default=False,
        description="Enable LLM-based metadata enrichment",
    )


class Settings(BaseSettings):
    """Main application settings"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_nested_delimiter="__",
    )

    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Application environment",
    )
    app_name: str = Field(
        default="Griot and Grits API",
        description="Application name",
    )
    app_version: str = Field(
        default="0.1.0",
        description="Application version",
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )

    # Nested settings - will read from .env using their env_prefix
    database: DatabaseSettings = Field(
        default_factory=lambda: DatabaseSettings(_env_file=".env")
    )
    storage: StorageSettings = Field(
        default_factory=lambda: StorageSettings(_env_file=".env")
    )
    globus: GlobusSettings = Field(
        default_factory=lambda: GlobusSettings(_env_file=".env")
    )
    processing: ProcessingSettings = Field(
        default_factory=lambda: ProcessingSettings(_env_file=".env")
    )


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings.
    Settings are loaded from environment variables with proper prefixes.
    """
    return Settings()
