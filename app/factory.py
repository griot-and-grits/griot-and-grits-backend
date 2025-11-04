from functools import lru_cache
from app.config.settings import get_settings, Settings
from app.services.db import Database
from app.services.object_storage import ObjectStorage
from app.services.fixity_service import FixityService
from app.services.storage_location_service import StorageLocationService
from app.services.preservation_event_service import PreservationEventService
from app.services.ingestion_service import IngestionService
from app.services.globus_service import GlobusService
from app.services.collection_service import CollectionService
import logging

logger = logging.getLogger(__name__)


class Factory:
    """
    Application factory for dependency injection.
    Provides centralized access to all services.
    """

    def __init__(self):
        self.settings: Settings = get_settings()

        # Core database service
        self.db = Database(
            uri=self.settings.database.uri,
            db_name=self.settings.database.name,
        )

        # Storage service (MinIO/S3)
        self.storage = ObjectStorage(
            endpoint=self.settings.storage.endpoint,
            access_key=self.settings.storage.access_key,
            secret_key=self.settings.storage.secret_key,
            bucket=self.settings.storage.bucket,
            region=self.settings.storage.region,
            secure=self.settings.storage.secure,
        )

        # Preservation services
        self.fixity_service = FixityService()
        self.storage_location_service = StorageLocationService(self.db)
        self.preservation_event_service = PreservationEventService(self.db)

        # Ingestion orchestrator
        self.ingestion_service = IngestionService(
            db=self.db,
            storage=self.storage,
            settings=self.settings,
        )

        # Globus and Collection services (conditional on GLOBUS_ENABLED)
        if self.settings.globus.enabled:
            try:
                self.globus_service = GlobusService(self.settings)
                self.collection_service = CollectionService(
                    db=self.db,
                    globus=self.globus_service,
                    settings=self.settings,
                )
                logger.info("Globus and Collection services initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Globus services: {e}")
                self.globus_service = None
                self.collection_service = None
        else:
            logger.info("Globus services disabled (GLOBUS_ENABLED=false)")
            self.globus_service = None
            self.collection_service = None


@lru_cache
def get_factory():
    """Singleton factory for the application."""
    return Factory()


# Create the singleton factory instance
factory = get_factory()

__all__ = ["factory", "get_factory", "get_settings"]
